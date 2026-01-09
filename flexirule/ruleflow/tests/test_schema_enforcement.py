import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.engine import MethodExecutionError, RuleEngine


def dummy_method(context, **kwargs):
    # Retrieve return value from config or default
    return kwargs.get("return_value", "default")

class TestSchemaEnforcement(FrappeTestCase):
    def setUp(self):
        frappe.db.rollback()

    def create_process_method(self, name, path, input_schema=None, output_schema=None):
        method = frappe.new_doc("Process Method")
        method.method_name = name
        method.method_path = path
        method.module = "Ruleflow"
        method.category = "Custom"
        if input_schema:
            method.input_schema = json.dumps(input_schema)
        if output_schema:
            method.output_schema = json.dumps(output_schema)
        method.insert(ignore_permissions=True)
        return method

    def create_rule(self, method_name):
        rule = frappe.new_doc("Rule")
        rule.rule_name = "Schema Test Rule"
        rule.document_type = "ToDo"
        rule.trigger_event = "Before Save"
        rule.execution_mode = "Synchronous"

        action = frappe.new_doc("Rule Action")
        action.action_type = "Process"
        action.process_method = method_name
        action.action_id = "act_test"
        action.action_label = "Test Action"

        rule.actions = [action]
        rule.insert(ignore_permissions=True)
        return rule

    def test_input_violation(self):
        """Test failure when inputs don't match schema"""
        schema = {
            "type": "object",
            "properties": {
                "required_field": {"type": "string"}
            },
            "required": ["required_field"]
        }
        # Method that does nothing (implementation irrelevant if input check fails first)
        method = self.create_process_method("Input Fail", "flexirule.ruleflow.tests.test_schema_enforcement.dummy_method", input_schema=schema)
        rule = self.create_rule(method.name)

        # Execute without mapping -> Missing required field
        engine = RuleEngine(rule, execution_context={"test_mode": True})

        with self.assertRaises(MethodExecutionError) as cm:
            engine.execute(frappe.new_doc("ToDo"))

        self.assertIn("Input contract violation", str(cm.exception))

    def test_output_violation(self):
        """Test failure when output doesn't match schema"""
        schema = {
            "type": "object",
            "properties": {
                "result": {"type": "integer"}
            }
        }
        # Method returns a STRING (default) but schema expects OBJECT with integer
        method = self.create_process_method("Output Fail", "flexirule.ruleflow.tests.test_schema_enforcement.dummy_method", output_schema=schema)
        rule = self.create_rule(method.name)

        engine = RuleEngine(rule, execution_context={"test_mode": True})

        with self.assertRaises(MethodExecutionError) as cm:
            engine.execute(frappe.new_doc("ToDo"))

        self.assertIn("Output contract violation", str(cm.exception))

    def test_valid_enforcement(self):
        """Test success when schemas match"""
        in_schema = {"type": "object"}
        out_schema = {"type": "string"}

        # Valid execution
        method = self.create_process_method("Valid Schema", "flexirule.ruleflow.tests.test_schema_enforcement.dummy_method",
                                          input_schema=in_schema,
                                          output_schema=out_schema)
        rule = self.create_rule(method.name)

        engine = RuleEngine(rule, execution_context={"test_mode": True})

        # Should not raise
        engine.execute(frappe.new_doc("ToDo"))
