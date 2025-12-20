import json
import os
import sys
from types import ModuleType

# Mock Frappe
mock_frappe = ModuleType('frappe')
mock_frappe._ = lambda x: x
mock_frappe.whitelist = lambda: (lambda f: f)
mock_frappe.utils = ModuleType('utils')
mock_frappe.utils.now = lambda: "2025-01-01"
sys.modules['frappe'] = mock_frappe

sys.path.append("/home/erpnext/frappe-bench/apps/flexirule")

# Mock frappe.get_meta and other stuff if needed, but let's try direct import
try:
    from flexirule.ruleflow.core.compiler import ConditionCompiler
    from flexirule.ruleflow.utils.field_resolver import FieldResolver
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_repro():
    compiler = ConditionCompiler()
    
    # Standard condition for is_group == 0
    conditions = {
        "op": "and",
        "conditions": [
            {
                "left": { "ref": "doc.is_group" },
                "op": "==",
                "right": { "value": 0 }
            }
        ]
    }
    
    compiled = compiler.compile(conditions)
    print(f"Compiled Expression: {compiled}")
    
    # Mock Document
    class MockDoc:
        def __init__(self, data):
            self.data = data
        def get(self, key, default=None):
            val = self.data.get(key, default)
            print(f"DEBUG: MockDoc.get({key}) -> {val} (type: {type(val)})")
            return val
        def as_dict(self):
            return self.data

    doc = MockDoc({"is_group": 0, "name": "Test"})
    
    eval_globals = {
        'doc': doc,
        'resolve': FieldResolver.resolve,
        'True': True,
        'False': False,
        'None': None
    }
    
    try:
        # Simplified eval for test
        result = eval(compiled, {"__builtins__": {}}, eval_globals)
        print(f"Eval Result (is_group=0): {result}")
    except Exception as e:
        print(f"Eval Failed: {e}")

    # Test with is_group=1
    # Test with string "0"
    conditions_str = {
        "op": "and",
        "conditions": [
            {
                "left": { "ref": "doc.is_group" },
                "op": "==",
                "right": { "value": "0" }
            }
        ]
    }
    compiled_str = compiler.compile(conditions_str)
    print(f"Compiled Expression (string '0'): {compiled_str}")
    result_str = eval(compiled_str, {"__builtins__": {}}, eval_globals)
    print(f"Eval Result (string '0' vs int 0): {result_str}")

if __name__ == "__main__":
    test_repro()
