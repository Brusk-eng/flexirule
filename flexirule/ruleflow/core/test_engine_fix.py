import frappe
from flexirule.ruleflow.core.engine import RuleEngine
from unittest.mock import MagicMock

def test_engine_fix():
    # Mock the rule document structure provided by the user
    rule_doc = frappe._dict({
        "name": "Test New Process",
        "is_active": 1,
        "actions": [
            frappe._dict({
                "action_id": "root",
                "action_type": "Entry Action",
                "action_label": "Manual",
                "is_enabled": 1, 
                "next_step_if_true": "ACT-ACP3"
            }),
            frappe._dict({
                "action_id": "ACT-ACP3",
                "action_type": "Process",
                "action_label": "New Process",
                "is_enabled": 1,
                "process_name": "Deduplication",
                "operation": "find_similar_records",
                "config": '{"overall_threshold":0.8}',
                "on_error": "Stop"
            })
        ],
        "execution_mode": "Synchronous", 
        "max_execution_time": 30,
        "debug_mode": 1
    })

    # Mock Process Doc
    process_doc = MagicMock()
    process_doc.name = "Deduplication"
    process_doc.execute.return_value = "Mock Result"
    
    # Mock frappe.get_cached_doc
    original_get_cached = frappe.get_cached_doc
    def mock_get_cached(doctype, name):
        if doctype == "Process" and name == "Deduplication":
            return process_doc
        return original_get_cached(doctype, name)
    
    frappe.get_cached_doc = mock_get_cached
    frappe.db.exists = MagicMock(return_value=True)

    try:
        engine = RuleEngine(rule_doc)
        context = engine.execute(frappe._dict({"name": "TestDoc"}))
        print("Execution Success:", context)
    except Exception as e:
        print("Execution Failed:", str(e))
        import traceback
        traceback.print_exc()
    finally:
        # Restore original
        frappe.get_cached_doc = original_get_cached

if __name__ == "__main__":
    frappe.connect()
    test_engine_fix()
