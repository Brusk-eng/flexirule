# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from flexirule.ruleflow.core.engine import RuleEngine
from flexirule.ruleflow.doctype.process_method.process_method import ProcessMethod

class TestRedesignArchitecture(FrappeTestCase):
    
    def test_01_process_method_naming(self):
        """Verify Process Method uses method_path as name"""
        method_path = "flexirule.ruleflow.tests.test_redesign_architecture.dummy_method"
        method_name = "Dummy Method"
        
        if frappe.db.exists("Process Method", method_path):
            frappe.delete_doc("Process Method", method_path)
            
        doc = frappe.get_doc({
            "doctype": "Process Method",
            "method_name": method_name,
            "method_path": method_path,
            "category": "Custom",
            "return_type": "None",
            "is_enabled": 1
        })
        doc.insert()
        
        self.assertEqual(doc.name, method_path, "Process Method name should be method_path")
        
    def test_02_validation_schema(self):
        """Verify Schema Validation on Save"""
        method_path = "flexirule.ruleflow.tests.test_redesign_architecture.dummy_method"
        
        # Ensure method exists
        if not frappe.db.exists("Process Method", method_path):
            self.test_01_process_method_naming()

        # 1. Update method with schema
        pm = frappe.get_doc("Process Method", method_path)
        pm.config_schema = '{"type": "object", "properties": {"threshold": {"type": "integer"}}, "required": ["threshold"]}'
        pm.input_schema = pm.config_schema # Use same for input validation
        pm.save()
        
        # 2. Create Rule with Invalid Config
        rule = frappe.get_doc({
            "doctype": "Rule",
            "rule_name": "Test Validation Rule",
            "document_type": "User",
            "trigger_type": "Event",
            "is_active": 0, # Draft first
            "actions": [
                {
                    "action_label": "Invalid Action",
                    "action_type": "Process",
                    "process_method": method_path,
                    "configuration": '{"threshold": "NOT_AN_INT"}', # Invalid type
                    "action_id": "ACT-001"
                }
            ]
        })
        
        # Should throw ValidationError because configuration doesn't match schema
        with self.assertRaises(frappe.exceptions.ValidationError):
            rule.save()
            
    def test_03_input_mapping(self):
        """Verify Context -> Input Mapping"""
        mapping_rule_name = "Test Mapping Rule"
        if frappe.db.exists("Rule", mapping_rule_name):
            frappe.delete_doc("Rule", mapping_rule_name)

        method_path = "flexirule.ruleflow.tests.test_redesign_architecture.dummy_method"
        # Ensure method exists
        if not frappe.db.exists("Process Method", method_path):
            self.test_01_process_method_naming()
        
        rule = frappe.get_doc({
            "doctype": "Rule",
            "rule_name": mapping_rule_name,
            "document_type": "User",
            "trigger_type": "Event",
            "is_active": 1,
            "actions": [
                {
                    "action_label": "Mapped Action",
                    "action_type": "Process",
                    "process_method": method_path,
                    "action_id": "ACT-MAP-01",
                    # Map context variable 'my_val' to param 'value'
                    "input_mapping": '{"my_val": "value"}', 
                    "configuration": '{"threshold": 10}'
                }
            ]
        })
        rule.insert()
        
        # Execute Engine
        ctx = {"my_val": 999}
        engine = RuleEngine(rule, execution_context=ctx)
        result = engine.execute(None) # No doc needed for this test
        
        # We can't easily inspect the 'config' passed to method inside a test without mocking
        # But we can verify no error occurred and result was returned
        self.assertIsNotNone(result)

    def test_04_output_mapping(self):
        """Verify Result -> Context Mapping"""
        output_rule_name = "Test Output Mapping Rule"
        if frappe.db.exists("Rule", output_rule_name):
            frappe.delete_doc("Rule", output_rule_name)

        method_path = "flexirule.ruleflow.tests.test_redesign_architecture.dummy_method"
        # Ensure method exists
        if not frappe.db.exists("Process Method", method_path):
            self.test_01_process_method_naming()
        
        rule = frappe.get_doc({
            "doctype": "Rule",
            "rule_name": output_rule_name,
            "document_type": "User",
            "trigger_type": "Event",
            "is_active": 1,
            "actions": [
                {
                    "action_label": "Action with Output",
                    "action_type": "Process",
                    "process_method": method_path,
                    "action_id": "ACT-OUT-01",
                    "configuration": '{"threshold": 10}',
                    # Pass a value via mapping to ensure result
                    "input_mapping": '{"input_val": "value"}',
                    # Map result "processed_value" to context "final_result"
                    "output_mapping": '{"processed_value": "final_result"}'
                }
            ]
        })
        rule.insert()
        
        # Execute
        ctx = {"input_val": 500}
        engine = RuleEngine(rule, execution_context=ctx)
        final_ctx = engine.execute(None)
        
        # Check if context has 'final_result' = 500
        # dummy_method returns {"processed_value": value}
        self.assertEqual(final_ctx.get('final_result'), 500)

# Define dummy method module function for testing
def dummy_method(context, value=0, threshold=0):
    """
    Dummy method that returns inputs for verification
    """
    return {
        "processed_value": value,
        "is_above_threshold": value > threshold
    }
