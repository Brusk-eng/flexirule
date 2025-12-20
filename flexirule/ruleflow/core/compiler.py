
import json
import frappe
from frappe import _

class ConditionCompiler:
	"""
	Compiles Standardized JSON conditions into optimized Python expressions.
	Schema:
	- Group: { "op": "and|or", "conditions": [...] }
	- Condition: { "left": Operand, "op": "==", "right": Operand }
	- Collection: { "op": "any|all", "collection": "path", "alias": "x", "where": Group }
	- Operand: { "ref": "scope.path" } | { "value": <literal> }
	"""

	OPERATOR_MAP = {
		'==': '==',
		'!=': '!=',
		'>': '>',
		'<': '<',
		'>=': '>=',
		'<=': '<=',
		'in': 'in',
		'not in': 'not in',
		'is': 'is',
		'is not': 'is not',
		# Logical (Group)
		'and': 'and',
		'or': 'or'
	}

	def compile(self, conditions) -> str:
		if not conditions:
			return ""
			
		if isinstance(conditions, str):
			try: conditions = json.loads(conditions)
			except: return ""

		# Wrap list in AND group (legacy/root support)
		if isinstance(conditions, list):
			conditions = {"op": "and", "conditions": conditions}
			
		return self._compile_node(conditions, scopes={'doc', 'old_doc', 'row', 'vars', 'item'})

	def _compile_node(self, node, scopes=None):
		if not isinstance(node, dict):
			return ""
		
		if scopes is None:
			scopes = {'doc', 'old_doc', 'row', 'vars', 'item'}
			
		# 1. Detect Type
		# Collection
		if "collection" in node and "where" in node:
			return self._compile_collection(node, scopes)
			
		# Group (has 'conditions' list)
		if "conditions" in node and isinstance(node["conditions"], list):
			return self._compile_group(node, scopes)
			
		# Condition (has 'left')
		if "left" in node:
			return self._compile_condition(node, scopes)
			
		# Fallback/Empty
		return ""

	def _compile_group(self, node, scopes):
		subs = node.get("conditions", [])
		if not subs: return ""
		
		op = node.get("op", "and").lower()
		py_op = " and " if op == "and" else " or "
		
		compiled_subs = [s for s in (self._compile_node(sub, scopes) for sub in subs) if s]
		if not compiled_subs: return ""
		
		if len(compiled_subs) == 1 and not node.get("op"): # Single node, no op needed
			return compiled_subs[0]
			
		return f"({py_op.join(compiled_subs)})"

	def _compile_condition(self, node, scopes):
		left = node.get("left")
		right = node.get("right")
		op = node.get("op", "==")
		
		lhs_code = self._compile_operand(left, scopes)
		
		# Special Unary/Method Operators
		if op == 'is_set':
			return f"({lhs_code} is not None and {lhs_code} != '')"
		if op == 'is_not_set':
			return f"({lhs_code} is None or {lhs_code} == '')"
		if op == 'has_changed':
			# Special handling: left must be a ref
			if isinstance(left, dict) and 'ref' in left:
				ref_val = left['ref'] # e.g. doc.status
				parts = ref_val.split('.')
				if len(parts) > 1 and parts[0] == 'doc':
					# Construct old_doc ref: old_doc.status
					old_doc_ref = f"old_doc.{'.'.join(parts[1:])}"
					rhs_code = self._resolve_ref(old_doc_ref, scopes)
					return f"({lhs_code} != {rhs_code})"
			return "False"

		rhs_code = self._compile_operand(right, scopes)
		py_op = self.OPERATOR_MAP.get(op, "==")
		
		# Contains/Not Contains logic
		if op == 'contains':
			return f"({rhs_code} in str({lhs_code}) if {lhs_code} else False)"
		if op == 'not_contains':
			return f"({rhs_code} not in str({lhs_code}) if {lhs_code} else True)"
			
		return f"{lhs_code} {py_op} {rhs_code}"

	def _compile_collection(self, node, scopes):
		# { "op": "any", "collection": "doc.items", "alias": "item", "where": {...} }
		collection_ref = node.get("collection") # "doc.items"
		op = node.get("op", "any") # any | all | none
		alias = node.get("alias", "row")
		where = node.get("where")
		
		iterator = self._resolve_ref(collection_ref, scopes)
		
		# Push alias to active scopes
		new_scopes = scopes.copy()
		new_scopes.add(alias)
		
		condition_code = self._compile_node(where, new_scopes) or "True"
		
		func = "any"
		prefix = ""
		if op == "all": func = "all"
		if op == "none": 
			func = "any"
			prefix = "not "
			
		# Expression: any(condition for alias in collection)
		return f"{prefix}{func}({condition_code} for {alias} in ({iterator} or []))"

	def _compile_operand(self, operand, scopes):
		# { "ref": "doc.status" } or { "value": "x" }
		if not isinstance(operand, dict):
			return "''" 
			
		if "ref" in operand:
			return self._resolve_ref(operand["ref"], scopes)
		
		if "value" in operand:
			val = operand["value"]
			if val is None: return "''"
			return repr(val)
			
		return "''"

	def _resolve_ref(self, path, scopes):
		# "doc.status" -> resolve(doc, 'status')
		# "row.qty" -> resolve(row, 'qty')
		if not path: return "''"
		
		parts = path.split('.')
		scope = parts[0] # doc, old_doc, row, vars, item(legacy) or collection alias
		
		if scope not in scopes:
			return "''"
			
		if len(parts) == 1:
			return scope
			
		subpath = '.'.join(parts[1:])
		return f"resolve({scope}, '{subpath}')"
