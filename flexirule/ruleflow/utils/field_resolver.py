# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
FieldResolver - Smart field value resolution
Handles dot notation, child tables, and aggregate functions
"""

import frappe
from typing import Any, List, Dict


class FieldResolver:
	"""
	Resolves field values from documents with support for:
	- Simple fields
	- Child table fields (dot notation)
	- Aggregate functions (SUM, AVG, COUNT, MAX, MIN)
	- Parent/grandparent references
	"""
	
	@staticmethod
	def resolve(doc, field_path: str) -> Any:
		"""
		Resolve a field value from a document
		
		Args:
			doc: Frappe document
			field_path: Field path (supports dot notation and aggregates)
			
		Returns:
			Resolved value
			
		Examples:
			- 'customer_name' → doc.customer_name
			- 'items.item_code' → list of item_codes from items table
			- 'items.qty:sum' → sum of all qty values
			- 'items.rate:avg' → average of all rate values
			- 'parent.customer_group' → doc's parent's customer_group
		"""
		if not field_path:
			return None
		
		# Check for aggregate functions
		if ':' in field_path:
			return FieldResolver._resolve_aggregate(doc, field_path)
		
		# Check for dot notation (child table or parent reference)
		if '.' in field_path:
			return FieldResolver._resolve_nested(doc, field_path)
		
		# Simple field
		return doc.get(field_path)
	
	@staticmethod
	def _resolve_nested(doc, field_path: str) -> Any:
		"""
		Resolve nested field (child table or parent)
		
		Examples:
			- 'items.item_code' → ['ITEM-001', 'ITEM-002']
			- 'parent.customer_name' → 'Acme Corp'
		"""
		parts = field_path.split('.')
		
		# Check if first part is 'parent'
		if parts[0] == 'parent' and doc.get('parent'):
			parent_doc = frappe.get_doc(doc.get('parenttype'), doc.get('parent'))
			if len(parts) == 2:
				return parent_doc.get(parts[1])
			else:
				# Multiple levels (rare but supported)
				return FieldResolver.resolve(parent_doc, '.'.join(parts[1:]))
		
		# Child table field
		child_table_fieldname = parts[0]
		child_field = parts[1] if len(parts) > 1 else None
		
		# Get child table rows
		child_rows = doc.get(child_table_fieldname)
		if not child_rows:
			return []
		
		# If no child field specified, return all rows
		if not child_field:
			return child_rows
		
		# Extract values from child field
		values = [row.get(child_field) for row in child_rows if row.get(child_field) is not None]
		return values
	
	@staticmethod
	def _resolve_aggregate(doc, field_path: str) -> Any:
		"""
		Resolve aggregate function
		
		Format: 'child_table.field:function'
		
		Supported functions:
			- sum: Sum of all values
			- avg: Average of all values
			- count: Count of non-null values
			- max: Maximum value
			- min: Minimum value
			- first: First value
			- last: Last value
		"""
		# Split path and function
		path, func = field_path.split(':')
		
		# Get values
		values = FieldResolver._resolve_nested(doc, path)
		if not values:
			return 0 if func in ['sum', 'count'] else None
		
		# Filter numeric values for numeric functions
		if func in ['sum', 'avg', 'max', 'min']:
			values = [v for v in values if isinstance(v, (int, float))]
		
		# Apply function
		if func == 'sum':
			return sum(values)
		elif func == 'avg':
			return sum(values) / len(values) if values else 0
		elif func == 'count':
			return len(values)
		elif func == 'max':
			return max(values) if values else None
		elif func == 'min':
			return min(values) if values else None
		elif func == 'first':
			return values[0] if values else None
		elif func == 'last':
			return values[-1] if values else None
		else:
			frappe.log_error(f"Unknown aggregate function: {func}", "FieldResolver")
			return None
	
	@staticmethod
	def get_child_table_fields(doctype: str) -> List[str]:
		"""
		Get all child table fieldnames for a DocType
		
		Args:
			doctype: DocType name
			
		Returns:
			List of child table fieldnames
		"""
		meta = frappe.get_meta(doctype)
		return [f.fieldname for f in meta.fields if f.fieldtype == 'Table']
	
	@staticmethod
	def get_field_type(doctype: str, fieldname: str) -> str:
		"""
		Get field type for a field
		
		Args:
			doctype: DocType name
			fieldname: Field name
			
		Returns:
			Field type
		"""
		meta = frappe.get_meta(doctype)
		field = meta.get_field(fieldname)
		return field.fieldtype if field else None
	
	@staticmethod
	def get_all_fields(doctype: str, include_child_tables: bool = False) -> List[Dict]:
		"""
		Get all fields for a DocType with metadata
		
		Args:
			doctype: DocType name
			include_child_tables: Include child table fields with dot notation
			
		Returns:
			List of field dictionaries
		"""
		meta = frappe.get_meta(doctype)
		fields = []
		
		for field in meta.fields:
			if field.fieldtype not in ['Section Break', 'Column Break', 'HTML', 'Tab Break']:
				fields.append({
					'fieldname': field.fieldname,
					'label': field.label,
					'fieldtype': field.fieldtype,
					'options': field.options
				})
				
				# Add child table fields
				if include_child_tables and field.fieldtype == 'Table' and field.options:
					child_meta = frappe.get_meta(field.options)
					for child_field in child_meta.fields:
						if child_field.fieldtype not in ['Section Break', 'Column Break']:
							fields.append({
								'fieldname': f'{field.fieldname}.{child_field.fieldname}',
								'label': f'{field.label} → {child_field.label}',
								'fieldtype': child_field.fieldtype,
								'options': child_field.options,
								'is_child': True,
								'parent_field': field.fieldname
							})
		
		return fields


# Whitelisted API for UI
@frappe.whitelist()
def get_doctype_fields(doctype, include_child_tables=False):
	"""
	Get all fields for a DocType (API endpoint)
	
	Args:
		doctype: DocType name
		include_child_tables: Include child table fields
		
	Returns:
		List of field dictionaries
	"""
	return FieldResolver.get_all_fields(doctype, include_child_tables)
