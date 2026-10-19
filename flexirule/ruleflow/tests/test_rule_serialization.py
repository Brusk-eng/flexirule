import json
import unittest
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import validate_rule_document
from flexirule.ruleflow.tests.builder import RuleBuilder
from flexirule.ruleflow.utils.import_export import export_rule


class TestRuleSerialization(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self._test_prefix = f"FRX_SER_{uuid.uuid4().hex[:8]}"

	def tearDown(self):
		if hasattr(self, "_test_prefix"):
			rules = frappe.get_all(
				"Rule", filters={"rule_name": ["like", f"{self._test_prefix}%"]}, fields=["name", "is_active"]
			)
			for r in rules:
				if r.is_active:
					frappe.db.set_value("Rule", r.name, "is_active", 0, update_modified=False)
			for r in rules:
				frappe.delete_doc("Rule", r.name, force=True, ignore_permissions=True)
		super().tearDown()

	def test_serialized_export_payload_keys_and_schema(self):
		"""
		Verify that export_rule() serializes a real Rule document with full
		canonical structure, actions, exact values, and without deprecated fields like 'is_sub_rule'.
		"""
		rule_name = f"{self._test_prefix}_Export_Test"
		rule = (
			RuleBuilder(rule_name)
			.document_type("ToDo")
			.active(0)
			.entry_action(label="Start Gate", next_step="stop_1")
			.stop("Success Stop", action_id="stop_1")
			.build()
		)

		exported = export_rule(rule.name)

		# Top-level envelope assertions
		self.assertEqual(exported.get("flexirule_version"), "1.0")
		self.assertIn("export_date", exported)
		self.assertIn("rule", exported)

		rule_payload = exported["rule"]
		canonical_rule_keys = {
			"rule_name",
			"document_type",
			"trigger_event",
			"rule_type",
			"priority",
			"is_active",
			"conditions_json",
			"options_json",
			"visual_data",
			"actions",
		}
		self.assertEqual(set(rule_payload.keys()), canonical_rule_keys)
		self.assertEqual(rule_payload["rule_name"], rule_name)
		self.assertEqual(rule_payload["document_type"], "ToDo")
		self.assertEqual(rule_payload["trigger_event"], "Validate")
		self.assertEqual(rule_payload["priority"], "10")
		self.assertEqual(rule_payload["is_active"], 0)
		self.assertEqual(len(rule_payload["actions"]), 2)

		# Verify action structure & field values
		act_0 = rule_payload["actions"][0]
		self.assertEqual(act_0["action_id"], "root")
		self.assertEqual(act_0["action_label"], "Start Gate")
		self.assertEqual(act_0["action_type"], "Entry Action")
		self.assertEqual(act_0["is_enabled"], 1)
		self.assertEqual(act_0["next_step_if_true"], "stop_1")

		act_1 = rule_payload["actions"][1]
		self.assertEqual(act_1["action_id"], "stop_1")
		self.assertEqual(act_1["action_label"], "Success Stop")
		self.assertEqual(act_1["action_type"], "Stop")
		self.assertEqual(act_1["is_enabled"], 1)

		# Confirm deprecated fields are absent at rule and action levels
		for deprecated in ("is_sub_rule", "is_subrule", "sub_rule"):
			self.assertNotIn(deprecated, rule_payload)
			self.assertNotIn(deprecated, act_0)

	def test_payload_structure_and_validation_service(self):
		"""
		Verify that validate_rule_document() validates serialized payload structure against
		the rule definition validation service.
		"""
		rule_name = f"{self._test_prefix}_Validate_Test"
		rule = (
			RuleBuilder(rule_name)
			.document_type("ToDo")
			.active(0)
			.entry_action(next_step="stop_1")
			.stop("Success Stop", action_id="stop_1")
			.build()
		)

		exported = export_rule(rule.name)
		validation = validate_rule_document(exported["rule"], mode="draft")

		self.assertTrue(validation.get("valid"))
		self.assertEqual(validation.get("errors"), [])

	def test_export_import_roundtrip_contract(self):
		"""
		Verify full round-trip export -> import rule serialization integrity,
		including action configuration, condition JSON, assignment config, and branching links.
		"""
		source_name = f"{self._test_prefix}_Source_Rule"
		target_name = f"{self._test_prefix}_Imported_Rule"

		cond_expr = [{"left": {"ref": "doc.description"}, "op": "!=", "right": {"value": ""}}]
		assign_config = [{"target": "doc.description", "operator": "set", "value": "Roundtrip Value"}]

		source_rule = (
			RuleBuilder(source_name)
			.document_type("ToDo")
			.active(0)
			.entry_action(next_step="cond_1")
			.condition(
				"Check Description", cond_expr, next_true="assign_1", next_false="stop_1", action_id="cond_1"
			)
			.assignment("Set Description", assign_config, next_step="stop_1", action_id="assign_1")
			.stop("Success Stop", action_id="stop_1")
			.build()
		)

		exported = export_rule(source_rule.name)
		exported["rule"]["rule_name"] = target_name

		from flexirule.ruleflow.utils.import_export import import_rule

		imported_name = import_rule(exported)
		self.assertEqual(imported_name, target_name)

		imported_doc = frappe.get_doc("Rule", imported_name)
		self.assertEqual(imported_doc.document_type, "ToDo")
		self.assertEqual(len(imported_doc.actions), 4)

		action_ids = [a.action_id for a in imported_doc.actions]
		self.assertEqual(action_ids, ["root", "cond_1", "assign_1", "stop_1"])

		# Verify branching links and configuration JSON on Condition action
		cond_act = imported_doc.actions[1]
		self.assertEqual(cond_act.action_id, "cond_1")
		self.assertEqual(cond_act.next_step_if_true, "assign_1")
		self.assertEqual(cond_act.next_step_if_false, "stop_1")

		# Verify assignment action configuration
		assign_act = imported_doc.actions[2]
		self.assertEqual(assign_act.action_id, "assign_1")
		self.assertEqual(assign_act.next_step_if_true, "stop_1")
		parsed_config = json.loads(assign_act.config)
		self.assertEqual(parsed_config[0]["value"], "Roundtrip Value")

	def test_import_rule_overwrite_clears_stale_actions(self):
		"""
		Verify import_rule(overwrite=True) removes stale actions and updates action ordering.
		"""
		rule_name = f"{self._test_prefix}_Overwrite_Rule"

		# Create initial rule with 3 actions
		initial_rule = (
			RuleBuilder(rule_name)
			.document_type("ToDo")
			.active(0)
			.entry_action(next_step="assign_1")
			.assignment(
				"Set Description",
				[{"target": "doc.description", "operator": "set", "value": "A"}],
				next_step="stop_1",
				action_id="assign_1",
			)
			.stop("Success", action_id="stop_1")
			.build()
		)
		self.assertEqual(len(initial_rule.actions), 3)

		# Build updated rule export with only 2 actions
		updated_export = {
			"flexirule_version": "1.0",
			"rule": {
				"rule_name": rule_name,
				"document_type": "ToDo",
				"trigger_event": "Validate",
				"priority": "10",
				"is_active": 0,
				"actions": [
					{
						"action_id": "root",
						"action_label": "New Start",
						"action_type": "Entry Action",
						"is_enabled": 1,
						"next_step_if_true": "stop_1",
					},
					{
						"action_id": "stop_1",
						"action_label": "New Stop",
						"action_type": "Stop",
						"is_enabled": 1,
					},
				],
			},
		}

		from flexirule.ruleflow.utils.import_export import import_rule

		imported_name = import_rule(updated_export, overwrite=True)
		self.assertEqual(imported_name, rule_name)

		updated_doc = frappe.get_doc("Rule", imported_name)
		self.assertEqual(len(updated_doc.actions), 2)
		action_ids = [a.action_id for a in updated_doc.actions]
		self.assertEqual(action_ids, ["root", "stop_1"])
		self.assertNotIn("assign_1", action_ids)
