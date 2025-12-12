# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Master Data Management (MDM) process methods for the Bolton Rule Engine

Includes:
- Data Review Task creation
- Batch normalization
- Duplicate detection with task creation
"""

import frappe
from frappe import _
from .utils import parse_field_list
from typing import Dict, List, Any, Optional


# ============================================================================
# DATA REVIEW TASK CREATION
# ============================================================================

def create_data_review_task(context, task_type='Duplicate Review', description=None,
                    priority='Medium', similarity_score=None, 
                    related_document=None, **kwargs):
    """
    Create a Data Review Task for data steward review.
    
    Args:
        context: Execution context containing 'doc'
        task_type: Type of task (Duplicate Review, Data Quality, Merge Request)
        description: Task description (supports {doc.field_name} placeholders)
        priority: Low, Medium, High, Critical
        similarity_score: Similarity percentage (for duplicate detection)
        related_document: Name of related document (for duplicate pairs)
    
    Returns:
        Name of created task or None
    """
    doc = context.get('doc')
    if not doc:
        return None
    
    # Check if Data Review Task doctype exists
    if not frappe.db.exists('DocType', 'Data Review Task'):
        frappe.log_error("Data Review Task DocType not found. Please create it first.")
        return None
    
    # Parse description with placeholders
    if description:
        try:
            description = description.format(doc=doc, **context.get('vars', {}))
        except Exception:
            pass
    else:
        description = f"Review required for {doc.doctype}: {doc.name}"
    
    # Create task
    task = frappe.new_doc('Data Review Task')
    task.task_type = task_type
    task.status = 'Open'
    task.priority = priority
    task.description = description
    task.source_doctype = doc.doctype
    task.source_document = doc.name
    
    if similarity_score:
        task.similarity_score = similarity_score
    
    # Add related document if provided
    if related_document and hasattr(task, 'related_documents'):
        task.append('related_documents', {
            'doctype_name': doc.doctype,
            'document_name': related_document
        })
    
    try:
        task.insert(ignore_permissions=True)
        frappe.db.commit()
        return task.name
    except Exception as e:
        frappe.log_error(f"Failed to create Data Review task: {e}")
        return None


def find_duplicates_and_create_task(context, fields_config=None, 
                                     overall_threshold=0.8,
                                     task_type='Duplicate Review',
                                     priority='Medium',
                                     max_tasks=5, **kwargs):
    """
    Find similar records and create Data Review Tasks for review.
    
    Args:
        context: Execution context containing 'doc'
        fields_config: Field comparison config
        overall_threshold: Similarity threshold (0-1)
        task_type: Type of task to create
        priority: Task priority
        max_tasks: Maximum number of tasks to create per document
    
    Returns:
        List of created task names
    """
    doc = context.get('doc')
    if not doc or not fields_config:
        return []
    
    # Import deduplication method
    from .deduplication import find_similar_records
    
    # Find similar records
    matches = find_similar_records(
        context,
        overall_threshold=overall_threshold,
        fields_config=fields_config,
        stop_after_first_match=False
    )
    
    if not matches:
        return []
    
    created_tasks = []
    
    for match in matches[:max_tasks]:
        match_name = match.get('name')
        match_score = match.get('score', 0)
        
        # Check if task already exists for this pair
        existing = frappe.db.exists('Data Review Task', {
            'source_doctype': doc.doctype,
            'source_document': doc.name,
            'status': ['in', ['Open', 'In Progress']]
        })
        
        if existing:
            continue
        
        description = f"Potential duplicate found:\n" \
                      f"• {doc.name} (current)\n" \
                      f"• {match_name} (match)\n" \
                      f"Similarity: {match_score}%"
        
        task_name = create_data_review_task(
            context,
            task_type=task_type,
            description=description,
            priority=priority,
            similarity_score=match_score,
            related_document=match_name
        )
        
        if task_name:
            created_tasks.append(task_name)
    
    return created_tasks


# ============================================================================
# BATCH NORMALIZATION (Background Job)
# ============================================================================

def normalize_all_documents(context, doctype=None, field=None, target_field=None,
                             transformations=None, batch_size=100, 
                             filters=None, **kwargs):
    """
    Normalize a field for all documents of a type (runs as background job).
    """
    if not doctype or not field:
        return 0
    
    target_field = target_field or f"{field}_normalized"
    
    # Build filters
    doc_filters = filters or {}
    doc_filters['docstatus'] = ['!=', 2]
    
    # Get total count
    total = frappe.db.count(doctype, doc_filters)
    if total == 0:
        return 0
    
    # Import normalization
    from .normalization import apply_transformations
    
    processed = 0
    offset = 0
    
    while offset < total:
        docs = frappe.get_all(
            doctype,
            filters=doc_filters,
            fields=['name', field],
            limit_start=offset,
            limit_page_length=batch_size
        )
        
        for doc_data in docs:
            value = doc_data.get(field)
            if value:
                normalized = apply_transformations(value, transformations or ['lowercase', 'strip'])
                
                try:
                    frappe.db.set_value(
                        doctype, doc_data.name, 
                        target_field, normalized,
                        update_modified=False
                    )
                    processed += 1
                except Exception as e:
                    frappe.log_error(f"Normalization failed for {doctype} {doc_data.name}: {e}")
        
        frappe.db.commit()
        offset += batch_size
    
    return processed


def enqueue_normalize_all_documents(context, doctype=None, field=None, 
                                     target_field=None, transformations=None,
                                     batch_size=100, filters=None, **kwargs):
    """
    Enqueue normalize_all_documents as a background job.
    """
    if not doctype or not field:
        return None
    
    job = frappe.enqueue(
        'flexirule.ruleflow.methods.mdm.normalize_all_documents',
        context=context,
        doctype=doctype,
        field=field,
        target_field=target_field,
        transformations=transformations,
        batch_size=batch_size,
        filters=filters,
        queue='long',
        timeout=3600
    )
    
    return job


def run_batch_duplicate_detection(context, doctype=None, fields_config=None,
                                   overall_threshold=0.8, batch_size=50,
                                   create_tasks=True, **kwargs):
    """
    Run duplicate detection across all documents of a type (background job).
    """
    if not doctype or not fields_config:
        return 0
    
    from .deduplication import find_similar_records
    
    total = frappe.db.count(doctype, {'docstatus': ['!=', 2]})
    duplicates_found = 0
    
    offset = 0
    while offset < total:
        docs = frappe.get_all(
            doctype,
            filters={'docstatus': ['!=', 2]},
            fields=['name'],
            limit_start=offset,
            limit_page_length=batch_size
        )
        
        for doc_data in docs:
            doc = frappe.get_doc(doctype, doc_data.name)
            ctx = {'doc': doc}
            
            matches = find_similar_records(
                ctx,
                overall_threshold=overall_threshold,
                fields_config=fields_config,
                stop_after_first_match=True
            )
            
            if matches:
                duplicates_found += 1
                
                if create_tasks:
                    find_duplicates_and_create_task(
                        ctx,
                        fields_config=fields_config,
                        overall_threshold=overall_threshold,
                        max_tasks=1
                    )
        
        frappe.db.commit()
        offset += batch_size
    
    return duplicates_found
