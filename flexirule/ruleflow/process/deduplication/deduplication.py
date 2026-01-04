# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Deduplication Process

File-backed execution for deduplication operations.
Migrated from flexirule.ruleflow.methods.deduplication.
"""

import frappe
import json
from frappe import _
from typing import Dict, List, Any, Optional
from rapidfuzz import process, fuzz

# ============================================================
# HELPERS
# ============================================================

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


def parse_field_list(fields) -> List[str]:
    """
    Parse fields from multiple formats:
    - Array: ["field1", "field2"]
    - Newline text: "field1\nfield2"
    - Comma text: "field1, field2"
    - JSON string: '["field1", "field2"]'
    """
    if not fields:
        return []
    
    # Already a list
    if isinstance(fields, list):
        return [f.strip() if isinstance(f, str) else f for f in fields]
    
    # String - try to parse
    if isinstance(fields, str):
        fields = fields.strip()
        
        # Try JSON first
        if fields.startswith('['):
            try:
                return json.loads(fields)
            except json.JSONDecodeError:
                pass
        
        # Newline separated
        if '\n' in fields:
            return [f.strip() for f in fields.split('\n') if f.strip()]
        
        # Comma separated
        if ',' in fields:
            return [f.strip() for f in fields.split(',') if f.strip()]
        
        # Single field
        return [fields] if fields else []
    
    return []


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


def _find_similar_records_bulk(context, fields, similarity_threshold):
    """
    Bulk fuzzy matching using rapidfuzz.process.extract
    Backwards compatible with legacy simple signature
    """
    doc = context.get('doc')
    field_list = parse_field_list(fields)
    
    threshold = similarity_threshold if similarity_threshold <= 1 else similarity_threshold / 100
    
   
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


# ============================================================
# OPERATIONS
# ============================================================

def find_similar_records(context, config):
    """Find similar records using configurable algorithms."""
    # Unpack config
    overall_threshold = config.get('overall_threshold', 0.8)
    minimum_fields_matched = config.get('minimum_fields_matched', 1)
    stop_after_first_match = config.get('stop_after_first_match', False)
    fields_config = config.get('fields_config')
    fields = config.get('fields')
    similarity_threshold = config.get('similarity_threshold', 80)
    
    doc = context.get('doc')
    if not doc:
        return []
    
    # Handle legacy simple call signature
    if fields and not fields_config:
        return _find_similar_records_bulk(context, fields, similarity_threshold)
    
    if not fields_config:
        return []
 
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
                'doctype': doc.doctype,
                'score': round(final_score * 100, 1),
                'fields': {k: round(v * 100, 1) for k, v in field_scores.items()}
            })
            
            if stop_after_first_match:
                break
    
    return sorted(matches, key=lambda x: x['score'], reverse=True)


def find_duplicates_by_fields(context, config):
    """Find exact duplicate records based on field values."""
    fields = config.get('fields')
    ignore_cancelled = config.get('ignore_cancelled', True)
    
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


def check_duplicate_and_prevent_save(context, config):
    """Block save if exact duplicate exists."""
    fields = config.get('fields')
    
    doc = context.get('doc')
    duplicates = find_duplicates_by_fields(context, config)
    
    if duplicates:
        field_list = parse_field_list(fields)
        frappe.throw(
            _("Duplicate found: {0} has the same values for {1}").format(
                duplicates[0], ", ".join(field_list)
            ),
            exc=frappe.DuplicateEntryError
        )
    
    return True


def check_similar_and_prevent_save(context, config):
    """Block save if similar records exist (fuzzy match)."""
    matches = find_similar_records(context, config)
    
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


def mark_as_duplicate(context, config):
    """Mark document as duplicate of another."""
    master_document = config.get('master_document')
    
    doc = context.get('doc')
    
    if not master_document:
        return False
    
    if hasattr(doc, 'is_duplicate'):
        doc.is_duplicate = 1
    if hasattr(doc, 'master_record'):
        doc.master_record = master_document
    
    return master_document


def find_duplicates_in_child_table(context, config):
    """Find duplicates based on values in a child table."""
    child_table_field = config.get('child_table_field')
    child_search_field = config.get('child_search_field')
    
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


# ============================================================
# DISPATCHER — single entry point
# ============================================================

_OPERATIONS = {
    "find_similar_records": find_similar_records,
    "find_duplicates_by_fields": find_duplicates_by_fields,
    "check_duplicate_and_prevent_save": check_duplicate_and_prevent_save,
    "check_similar_and_prevent_save": check_similar_and_prevent_save,
    "mark_as_duplicate": mark_as_duplicate,
    "find_duplicates_in_child_table": find_duplicates_in_child_table,
}


def execute(context, func=None, config=None):
    """
    Execute a deduplication operation.
    
    Args:
        context: Execution context with 'doc', 'dry_run', etc.
        func: Operation function name
        config: Configuration dict
    
    Returns:
        Operation result
    """
    if not func:
        frappe.throw(_("Operation function name is required"))
    
    if func not in _OPERATIONS:
        frappe.throw(_("Unknown operation: {0}. Available: {1}").format(
            func, ", ".join(_OPERATIONS.keys())
        ))
    
    return _OPERATIONS[func](context, config or {})
