# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Enhanced Deduplication process methods for the Bolton Rule Engine
Features: Blocking strategy, weighted scoring, rapidfuzz.process for bulk matching
"""

import frappe
from frappe import _
from .utils import parse_field_list
from typing import Dict, List, Any, Optional


# ============================================================================
# RAPIDFUZZ BULK MATCHING
# ============================================================================

def get_rapidfuzz_process():
    """Get rapidfuzz.process module for bulk matching"""
    try:
        from rapidfuzz import process, fuzz
        return process, fuzz
    except ImportError:
        return None, None


def get_phonetic_scorer():
    """Lazy-load phonetic matcher"""
    try:
        import jellyfish
        def phonetic_score(a, b):
            code_a = jellyfish.metaphone(str(a))
            code_b = jellyfish.metaphone(str(b))
            return 1.0 if code_a == code_b else 0.0
        return phonetic_score
    except ImportError:
        return lambda a, b: 1.0 if str(a).lower() == str(b).lower() else 0.0


def _normalize(value):
    """Basic text normalization"""
    if not isinstance(value, str):
        return str(value) if value is not None else ''
    
    import re
    value = value.lower().strip()
    value = re.sub(r'\s+', ' ', value)
    return value


def _build_blocking_filters(doc, blocking_fields):
    """Build filters for blocking strategy (candidate pre-filtering)"""
    filters = {}
    
    for field_cfg in blocking_fields:
        if not field_cfg.get('included_in_filters', True):
            continue
            
        fieldname = field_cfg['fieldname']
        value = doc.get(fieldname)
        
        if not value:
            continue
        
        algorithm = field_cfg.get('algorithm', 'Exact')
        
        if algorithm == 'Exact':
            filters[fieldname] = value
        elif algorithm in ('Fuzzy', 'Contains', 'Phonetic'):
            # Use LIKE for initial blocking (first 3 chars)
            if isinstance(value, str) and len(value) >= 3:
                filters[fieldname] = ['like', f'%{value[:3]}%']
    
    return filters


# ============================================================================
# MAIN DEDUPLICATION METHODS
# ============================================================================

def find_similar_records(context, overall_threshold=0.8, minimum_fields_matched=1,
                         stop_after_first_match=False, fields_config=None, 
                         fields=None, similarity_threshold=80, **kwargs):
    """
    Find similar records using rapidfuzz.process for efficient bulk matching.
    
    Uses rapidfuzz.process.extract for vectorized fuzzy matching which is
    significantly faster than per-candidate comparison for large datasets.
    
    Args:
        context: Execution context containing 'doc'
        overall_threshold: Minimum weighted score (0-1) for a match
        minimum_fields_matched: Minimum fields exceeding their thresholds
        stop_after_first_match: Stop after first match
        fields_config: List of field comparison configs:
            [{"fieldname": "...", "algorithm": "Fuzzy", "weight": 0.3, 
              "threshold": 0.8, "normalize": True, "included_in_filters": True}]
        
        # Legacy parameters (backwards compatibility)
        fields: List/text of fields to compare (simple mode)
        similarity_threshold: Minimum similarity score 0-100 (simple mode)
        
    Returns:
        List of similar documents: [{"name": "...", "score": 85.5, "fields": {...}}]
    """
    doc = context.get('doc')
    if not doc:
        return []
    
    # Handle legacy simple call signature
    if fields and not fields_config:
        return _find_similar_records_bulk(context, fields, similarity_threshold)
    
    if not fields_config:
        return []
    
    # Get rapidfuzz
    process, fuzz = get_rapidfuzz_process()
    if not process:
        frappe.logger().warning("rapidfuzz not installed, using fallback matching")
        return _find_similar_records_fallback(context, overall_threshold, 
                                               minimum_fields_matched, 
                                               stop_after_first_match, 
                                               fields_config)
    
    # Build blocking query
    blocking_filters = _build_blocking_filters(doc, fields_config)
    
    if doc.name:
        blocking_filters['name'] = ['!=', doc.name]
    blocking_filters['docstatus'] = ['!=', 2]
    
    # Fetch candidates
    all_fieldnames = list(set(['name'] + [f['fieldname'] for f in fields_config]))
    
    try:
        candidates = frappe.get_all(
            doc.doctype,
            filters=blocking_filters,
            fields=all_fieldnames,
            limit=1000
        )
    except Exception as e:
        frappe.log_error(f"Deduplication candidate fetch failed: {e}")
        return []
    
    if not candidates:
        return []
    
    # Prepare candidate lookup by name
    candidate_map = {c.name: c for c in candidates}
    
    # Process each field with rapidfuzz.process.extract for bulk matching
    field_scores_map = {}  # {candidate_name: {fieldname: score}}
    
    for field_cfg in fields_config:
        fieldname = field_cfg['fieldname']
        algorithm = field_cfg.get('algorithm', 'Fuzzy')
        normalize = field_cfg.get('normalize', True)
        
        doc_value = doc.get(fieldname)
        if not doc_value:
            continue
        
        if normalize:
            doc_value = _normalize(doc_value)
        
        if algorithm == 'Fuzzy':
            # Use rapidfuzz.process.extract for bulk fuzzy matching
            choices = {}
            for c in candidates:
                val = c.get(fieldname)
                if val:
                    choices[c.name] = _normalize(val) if normalize else str(val)
            
            if choices:
                # extract returns list of (match, score, key)
                results = process.extract(
                    doc_value, 
                    choices, 
                    scorer=fuzz.ratio,
                    limit=None,  # Get all
                    score_cutoff=0  # Get all scores
                )
                
                for match_value, score, candidate_name in results:
                    if candidate_name not in field_scores_map:
                        field_scores_map[candidate_name] = {}
                    field_scores_map[candidate_name][fieldname] = score / 100.0
        
        elif algorithm == 'Exact':
            for c in candidates:
                val = c.get(fieldname)
                if val:
                    cmp_val = _normalize(val) if normalize else str(val).lower()
                    score = 1.0 if doc_value.lower() == cmp_val else 0.0
                    if c.name not in field_scores_map:
                        field_scores_map[c.name] = {}
                    field_scores_map[c.name][fieldname] = score
        
        elif algorithm == 'Contains':
            for c in candidates:
                val = c.get(fieldname)
                if val:
                    cmp_val = _normalize(val) if normalize else str(val).lower()
                    score = 1.0 if doc_value.lower() in cmp_val else 0.0
                    if c.name not in field_scores_map:
                        field_scores_map[c.name] = {}
                    field_scores_map[c.name][fieldname] = score
        
        elif algorithm == 'Phonetic':
            phonetic_scorer = get_phonetic_scorer()
            for c in candidates:
                val = c.get(fieldname)
                if val:
                    score = phonetic_scorer(doc_value, str(val))
                    if c.name not in field_scores_map:
                        field_scores_map[c.name] = {}
                    field_scores_map[c.name][fieldname] = score
        
        elif algorithm == 'Numeric Range':
            try:
                doc_num = float(doc_value)
                for c in candidates:
                    val = c.get(fieldname)
                    if val is not None:
                        try:
                            cmp_num = float(val)
                            max_val = max(abs(doc_num), abs(cmp_num))
                            if max_val == 0:
                                score = 1.0
                            else:
                                diff = abs(doc_num - cmp_num) / max_val
                                score = max(0, 1 - diff)
                            if c.name not in field_scores_map:
                                field_scores_map[c.name] = {}
                            field_scores_map[c.name][fieldname] = score
                        except (ValueError, TypeError):
                            pass
            except (ValueError, TypeError):
                pass
        
        elif algorithm == 'Date Distance':
            from frappe.utils import getdate, date_diff
            try:
                doc_date = getdate(doc_value)
                # Use tolerance from field config, default 30 days
                max_days = field_cfg.get('tolerance', 30)
                if max_days <= 0:
                    max_days = 1  # Avoid division by zero
                for c in candidates:
                    val = c.get(fieldname)
                    if val:
                        try:
                            cmp_date = getdate(val)
                            diff = abs(date_diff(doc_date, cmp_date))
                            # Score is 1.0 if within tolerance, decreasing linearly
                            if diff <= max_days:
                                score = 1.0 - (diff / max_days)
                            else:
                                score = 0.0
                            if c.name not in field_scores_map:
                                field_scores_map[c.name] = {}
                            field_scores_map[c.name][fieldname] = score
                        except Exception:
                            pass
            except Exception:
                pass
    
    # Calculate weighted scores
    matches = []
    total_weight = sum(f.get('weight', 1.0) for f in fields_config)
    
    for candidate_name, field_scores in field_scores_map.items():
        weighted_score = 0.0
        fields_matched = 0
        
        for field_cfg in fields_config:
            fieldname = field_cfg['fieldname']
            weight = field_cfg.get('weight', 1.0)
            threshold = field_cfg.get('threshold', 0.8)
            
            score = field_scores.get(fieldname, 0.0)
            weighted_score += score * weight
            
            if score >= threshold:
                fields_matched += 1
        
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0
        
        if final_score >= overall_threshold and fields_matched >= minimum_fields_matched:
            matches.append({
                'name': candidate_name,
                'score': round(final_score * 100, 1),
                'fields': {k: round(v * 100, 1) for k, v in field_scores.items()}
            })
            
            if stop_after_first_match:
                break
    
    return sorted(matches, key=lambda x: x['score'], reverse=True)


def _find_similar_records_bulk(context, fields, similarity_threshold):
    """
    Bulk fuzzy matching using rapidfuzz.process.extract
    Backwards compatible with legacy simple signature
    """
    doc = context.get('doc')
    field_list = parse_field_list(fields)
    
    threshold = similarity_threshold if similarity_threshold <= 1 else similarity_threshold / 100
    
    process, fuzz = get_rapidfuzz_process()
    if not process:
        return find_duplicates_by_fields(context, fields=fields)
    
    # Fetch candidates
    try:
        candidates = frappe.get_all(
            doc.doctype,
            filters={'name': ['!=', doc.name], 'docstatus': ['!=', 2]},
            fields=['name'] + field_list,
            limit=1000
        )
    except Exception:
        return []
    
    if not candidates:
        return []
    
    # Build combined search string for each candidate
    candidate_strings = {}
    for c in candidates:
        parts = [_normalize(c.get(f) or '') for f in field_list]
        combined = ' '.join(filter(None, parts))
        if combined:
            candidate_strings[c.name] = combined
    
    if not candidate_strings:
        return []
    
    # Build search string for doc
    doc_parts = [_normalize(doc.get(f) or '') for f in field_list]
    doc_string = ' '.join(filter(None, doc_parts))
    
    if not doc_string:
        return []
    
    # Bulk extract
    results = process.extract(
        doc_string,
        candidate_strings,
        scorer=fuzz.token_set_ratio,  # Better for multi-field comparison
        limit=None,
        score_cutoff=threshold * 100
    )
    
    matches = []
    for match_value, score, candidate_name in results:
        matches.append({
            'name': candidate_name,
            'score': round(score, 1)
        })
    
    return sorted(matches, key=lambda x: x['score'], reverse=True)


def _find_similar_records_fallback(context, overall_threshold, minimum_fields_matched,
                                    stop_after_first_match, fields_config):
    """Fallback when rapidfuzz is not available"""
    doc = context.get('doc')
    
    blocking_filters = _build_blocking_filters(doc, fields_config)
    if doc.name:
        blocking_filters['name'] = ['!=', doc.name]
    blocking_filters['docstatus'] = ['!=', 2]
    
    all_fieldnames = list(set(['name'] + [f['fieldname'] for f in fields_config]))
    
    try:
        candidates = frappe.get_all(
            doc.doctype,
            filters=blocking_filters,
            fields=all_fieldnames,
            limit=500
        )
    except Exception:
        return []
    
    matches = []
    total_weight = sum(f.get('weight', 1.0) for f in fields_config)
    
    for candidate in candidates:
        weighted_score = 0.0
        fields_matched = 0
        field_scores = {}
        
        for field_cfg in fields_config:
            fieldname = field_cfg['fieldname']
            algorithm = field_cfg.get('algorithm', 'Exact')
            weight = field_cfg.get('weight', 1.0)
            threshold = field_cfg.get('threshold', 0.8)
            normalize = field_cfg.get('normalize', True)
            
            val1 = doc.get(fieldname)
            val2 = candidate.get(fieldname)
            
            if not val1 or not val2:
                continue
            
            if normalize:
                val1, val2 = _normalize(val1), _normalize(val2)
            
            # Simple exact match fallback
            score = 1.0 if str(val1).lower() == str(val2).lower() else 0.0
            
            field_scores[fieldname] = round(score * 100, 1)
            weighted_score += score * weight
            
            if score >= threshold:
                fields_matched += 1
        
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0
        
        if final_score >= overall_threshold and fields_matched >= minimum_fields_matched:
            matches.append({
                'name': candidate.name,
                'score': round(final_score * 100, 1),
                'fields': field_scores
            })
            
            if stop_after_first_match:
                break
    
    return sorted(matches, key=lambda x: x['score'], reverse=True)


def find_duplicates_by_fields(context, fields=None, ignore_cancelled=True, **kwargs):
    """Find exact duplicate records based on field values"""
    doc = context.get('doc')
    field_list = parse_field_list(fields)
    
    if not field_list:
        return []
    
    filters = {}
    for field in field_list:
        value = doc.get(field)
        if value:
            filters[field] = value
    
    if doc.name:
        filters['name'] = ['!=', doc.name]
    if ignore_cancelled:
        filters['docstatus'] = ['!=', 2]
    
    duplicates = frappe.get_all(doc.doctype, filters=filters, pluck='name')
    return duplicates


def check_duplicate_and_prevent_save(context, fields=None, **kwargs):
    """Block save if duplicate exists"""
    doc = context.get('doc')
    duplicates = find_duplicates_by_fields(context, fields=fields)
    
    if duplicates:
        field_list = parse_field_list(fields)
        frappe.throw(
            _("Duplicate found: {0} has the same values for {1}").format(
                duplicates[0], ", ".join(field_list)
            ),
            exc=frappe.DuplicateEntryError
        )
    
    return True


def mark_as_duplicate(context, master_document=None, **kwargs):
    """Mark document as duplicate of another"""
    doc = context.get('doc')
    
    if not master_document:
        return False
    
    if hasattr(doc, 'is_duplicate'):
        doc.is_duplicate = 1
    if hasattr(doc, 'master_record'):
        doc.master_record = master_document
    
    return master_document


def find_duplicates_in_child_table(context, child_table_field, child_search_field, **kwargs):
    """
    Find duplicates based on values in a child table.
    """
    doc = context.get('doc')
    if not doc:
        return []
        
    current_rows = doc.get(child_table_field) or []
    values_to_check = [
        r.get(child_search_field) 
        for r in current_rows 
        if r.get(child_search_field)
    ]
    
    if not values_to_check:
        return []

    meta = frappe.get_meta(doc.doctype)
    child_doctype = None
    for df in meta.fields:
        if df.fieldname == child_table_field and df.fieldtype == 'Table':
            child_doctype = df.options
            break
            
    if not child_doctype:
        return []

    filters = {
        child_search_field: ["in", values_to_check],
        "parenttype": doc.doctype,
        "docstatus": ["!=", 2]
    }
    
    if doc.name and not doc.is_new():
        filters["parent"] = ["!=", doc.name]

    duplicates = frappe.get_all(
        child_doctype, 
        filters=filters, 
        pluck="parent", 
        distinct=True
    )
    
    return duplicates


def check_similar_and_prevent_save(context, **kwargs):
    """
    Find similar records (fuzzy match) and prevent save if any are found.
    Wrapper around find_similar_records that throws DuplicateEntryError.
    
    Args:
        context: Execution context
        **kwargs: Arguments passed to find_similar_records
    """
    matches = find_similar_records(context, **kwargs)
    
    if matches:
        match_names = ", ".join([m['name'] for m in matches[:3]])
        count = len(matches)
        
        if count > 3:
            match_names += _(" and {0} others").format(count - 3)
            
        frappe.throw(
            _("Potential duplicates found: {0}").format(match_names),
            exc=frappe.DuplicateEntryError
        )
    
    return matches
