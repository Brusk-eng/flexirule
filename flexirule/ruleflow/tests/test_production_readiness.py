import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import get_action_context_schema, test_rule, validate_rule_document
from flexirule.ruleflow.core.contracts import normalize_trigger_type
from flexirule.ruleflow.core.coordinator import RuleCoordinator


class TestProductionReadiness(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def _unique(self, prefix):
		return f"{prefix}-{frappe.generate_hash(length=6)}"

	def _make_rule(self, payload):
		return frappe.get_doc({"doctype": "Rule", **payload}).insert(ignore_permissions=True)

	def test_test_rule_returns_direct_execution_result_without_persisted_log(self):
		rule = self._make_rule(
			{
				"rule_name": self._unique("Test Rule Direct"),
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "set_description",
						"action_type": "Set Value",
						"action_label": "Set Description",
						"target_field": "description",
						"value_template": "Validated by FlexiRule",
						"is_enabled": 1,
					}
				],
			}
		)
		before_logs = frappe.db.count("Rule Execution Log", {"rule": rule.name})

		response = test_rule(
			rule.name,
			document_json=json.dumps({"doctype": "ToDo", "description": "Original"}),
			save_log=0,
		)

		self.assertTrue(response["success"])
		self.assertEqual(response["status"], "Success")
		self.assertFalse(response["log_persisted"])
		self.assertTrue(response["execution_path"])
		self.assertTrue(any("Set Description" in msg for msg in response["messages"]))
		self.assertEqual(frappe.db.count("Rule Execution Log", {"rule": rule.name}), before_logs)

	def test_test_rule_persists_log_only_when_requested(self):
		rule = self._make_rule(
			{
				"rule_name": self._unique("Test Rule Log"),
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "set_description",
						"action_type": "Set Value",
						"action_label": "Set Description",
						"target_field": "description",
						"value_template": "Persist log",
						"is_enabled": 1,
					}
				],
			}
		)
		before_logs = frappe.db.count("Rule Execution Log", {"rule": rule.name})

		response = test_rule(
			rule.name,
			document_json=json.dumps({"doctype": "ToDo", "description": "Original"}),
			save_log=1,
		)

		self.assertTrue(response["success"])
		self.assertTrue(response["log_persisted"])
		self.assertEqual(frappe.db.count("Rule Execution Log", {"rule": rule.name}), before_logs + 1)

	def test_callable_rule_is_normalized_and_requires_document_type(self):
		result = validate_rule_document(
			{
				"trigger_type": "Callable Rule",
				"document_type": None,
				"actions": [],
			}
		)
		self.assertFalse(result["valid"])
		self.assertTrue(any("document_type" in err for err in result["errors"]))

		rule = self._make_rule(
			{
				"rule_name": self._unique("Legacy Callable"),
				"document_type": "ToDo",
				"trigger_type": "Callable Event",
				"priority": "0",
				"is_active": 0,
			}
		)
		self.assertEqual(normalize_trigger_type(rule.trigger_type), "Callable Rule")

	def test_sub_rule_supports_input_mapping_and_returns_payload(self):
		sub_rule = self._make_rule(
			{
				"rule_name": self._unique("Phone Validator"),
				"document_type": "ToDo",
				"trigger_type": "Callable Event",
				"priority": "0",
				"exposed_as_subrule": 1,
				"is_active": 1,
				"actions": [
					{
						"action_id": "set_description",
						"action_type": "Set Value",
						"action_label": "Apply Check",
						"target_field": "description",
						"value_template": "{{ vars.incoming_text }} / checked",
						"is_enabled": 1,
					}
				],
			}
		)
		parent_rule = self._make_rule(
			{
				"rule_name": self._unique("Parent Caller"),
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "call_subrule",
						"action_type": "Sub-Rule",
						"action_label": "Call Sub Rule",
						"rule": sub_rule.name,
						"config": json.dumps({"input_mapping": {"incoming_text": "doc.description"}}),
						"return_variable": "subrule_result",
						"return_type": "Dict",
						"is_enabled": 1,
					}
				],
			}
		)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "hello"})

		result = RuleCoordinator.execute_rule(parent_rule.name, {"doc": doc}, dry_run=True)

		self.assertEqual(doc.description, "hello / checked")
		self.assertEqual(result["vars"]["subrule_result"]["rule"], sub_rule.name)
		self.assertTrue(result["vars"]["subrule_result"]["path_trace"])

	def test_action_context_schema_returns_flat_variable_dtos(self):
		rule = self._make_rule(
			{
				"rule_name": self._unique("Context DTO"),
				"document_type": "Contact",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 0,
				"actions": [
					{
						"action_id": "query_contacts",
						"action_type": "Query Records",
						"action_label": "Query Contacts",
						"reference_doctype": "Contact",
						"operation": "Query List",
						"config": json.dumps({"fields": ["name", "email_id"], "limit": 5}),
						"return_variable": "query_result",
						"return_type": "List of Dict",
						"resolved_output_schema": json.dumps(
							[
								{"fieldname": "name", "fieldtype": "Data"},
								{"fieldname": "email_id", "fieldtype": "Data"},
							]
						),
						"next_step_if_true": "apply_status",
						"is_enabled": 1,
					},
					{
						"action_id": "apply_status",
						"action_type": "Set Value",
						"action_label": "Apply Status",
						"target_field": "status",
						"value_template": "Checked",
						"is_enabled": 1,
					},
				],
			}
		)

		result = get_action_context_schema(rule.name, "apply_status")
		values = {row["value"]: row for row in result["available_variables"]}

		self.assertIn("query_result", values)
		self.assertIn("query_result.name", values)
		self.assertIn("query_result.email_id", values)
		self.assertEqual(values["query_result"]["source_action_id"], "query_contacts")
		self.assertEqual(values["query_result.name"]["fieldtype"], "Data")
