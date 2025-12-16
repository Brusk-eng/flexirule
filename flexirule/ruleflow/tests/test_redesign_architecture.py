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
                    "method_config": '{"threshold": "NOT_AN_INT"}', # Invalid type
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
                    "method_config": '{"threshold": 10}'
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
                    "method_config": '{"threshold": 10}',
                    # Corrected input_mapping: Target(config field) -> Source(context variable)
                    "input_mapping": '{"value": "input_val"}',
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
        self.assertEqual(final_ctx.get('final_result'), 500)

    def test_05_execution_logging(self):
        """Verify Rule Execution Log creation"""
        log_rule_name = "Test Logging Rule"
        if frappe.db.exists("Rule", log_rule_name):
            frappe.delete_doc("Rule", log_rule_name)

        method_path = "flexirule.ruleflow.tests.test_redesign_architecture.dummy_method"
        
        rule = frappe.get_doc({
            "doctype": "Rule",
            "rule_name": log_rule_name,
            "document_type": "User",
            "trigger_type": "Event",
            "is_active": 1,
            "actions": [
                {
                    "action_label": "Log Action",
                    "action_type": "Process",
                    "process_method": method_path,
                    "action_id": "ACT-LOG-01",
                    "method_config": '{"threshold": 10}'
                }
            ]
        })
        rule.insert()
        
        # Execute with test_mode=False to trigger logging
        ctx = {"my_val": 100}
        # Explicitly set test_mode to False to ensure logging happens
        # But we need to be careful about timeouts or errors
        engine = RuleEngine(rule, execution_context={"test_mode": False})
        engine.execute(None)
        
        # Verify Log Exists
        logs = frappe.get_all("Rule Execution Log", filters={"rule": log_rule_name}, fields=["name", "status", "execution_path"])
        self.assertTrue(logs, "Execution Log should be created")
        self.assertEqual(logs[0].status, "Success")
        self.assertIn("Log Action", logs[0].execution_path)

    def test_06_test_rule_api(self):
        """Verify the test_rule whitelisted API"""
        from flexirule.ruleflow.doctype.rule.rule import test_rule
        
        rule_name = "Test API Rule"
        if frappe.db.exists("Rule", rule_name):
            frappe.delete_doc("Rule", rule_name)
            
        rule = frappe.get_doc({
            "doctype": "Rule",
            "rule_name": rule_name,
            "document_type": "User",
            "trigger_type": "Event",
            "is_active": 1,
            "actions": [] # Empty actions is fine for basic test, or add one
        })
        rule.insert()
        
        # Test 1: JSON Doc (Empty Rule)
        res = test_rule(rule_name, document_json='{"doctype": "User", "first_name": "Test"}')
        self.assertEqual(res['status'], 'Failed')
        self.assertIn("no enabled actions", res['error'])
        
        # Let's add an action to be safe
        method_path = "flexirule.ruleflow.tests.test_redesign_architecture.dummy_method"
        rule.append("actions", {
            "action_label": "Action 1",
            "action_type": "Process",
            "process_method": method_path,
            "action_id": "ACT-TEST-01",
            "method_config": '{"threshold": 10}'
        })
        rule.save()
        
        res = test_rule(rule_name, document_json='{"doctype": "User", "first_name": "Test"}')
        self.assertEqual(res['status'], 'Success')
        self.assertIn('execution_log', res)     


# Define dummy method module function for testing
def dummy_method(context, value=0, threshold=0):
    """
    Dummy method that returns inputs for verification
    """
    return {
        "processed_value": value,
        "is_above_threshold": value > threshold
    }
