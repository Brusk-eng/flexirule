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

	def test_rule_action_condition_persistence_and_execution_matrix(self):
		"""
		Verify Rule Action condition persistence across database insert, reload,
		compilation, execution semantics (true/false paths in RuleEngine), and export/import roundtrip.
		Covers:
		- Raw Python string condition expression
		- Structured condition tree (JSON list/dict)
		- Legacy condition_json payload
		- Absent/empty condition
		"""
		from flexirule.ruleflow.core.condition_payload import get_condition_payload
		from flexirule.ruleflow.core.engine import RuleEngine
		from flexirule.ruleflow.utils.import_export import import_rule

		todo_match = frappe.get_doc({"doctype": "ToDo", "description": "MATCH"}).insert(
			ignore_permissions=True
		)
		self.addCleanup(
			lambda: frappe.delete_doc("ToDo", todo_match.name, force=True, ignore_permissions=True)
		)

		todo_mismatch = frappe.get_doc({"doctype": "ToDo", "description": "OTHER"}).insert(
			ignore_permissions=True
		)
		self.addCleanup(
			lambda: frappe.delete_doc("ToDo", todo_mismatch.name, force=True, ignore_permissions=True)
		)

		# 1. Raw Python string condition expression
		rule_str_name = f"{self._test_prefix}_Str_Cond"
		raw_str_expr = "doc.description == 'MATCH'"
		rule_str = (
			RuleBuilder(rule_str_name)
			.document_type("ToDo")
			.active(1)
			.entry_action(next_step="cond_str")
			.condition(
				"Check Raw Str Cond",
				raw_str_expr,
				next_true="stop_true",
				next_false="stop_false",
				action_id="cond_str",
			)
			.stop("Match Stop", action_id="stop_true")
			.stop("Mismatch Stop", action_id="stop_false")
			.build()
		)

		reloaded_str = frappe.get_doc("Rule", rule_str.name)
		cond_action_str = next(a for a in reloaded_str.actions if a.action_id == "cond_str")
		self.assertIn("doc.description == 'MATCH'", cond_action_str.config)
		self.assertEqual(cond_action_str.compiled_expression, "doc.description == 'MATCH'")

		# Execution on reloaded rule: matching doc -> true branch, non-matching -> false branch
		RuleEngine(reloaded_str).execute(todo_match)
		res_match = getattr(frappe.local, "execution_payload", {})
		self.assertEqual(res_match.get("status"), "Success")
		self.assertIn("Match Stop", [s.get("action") for s in res_match.get("path_trace", [])])

		RuleEngine(reloaded_str).execute(todo_mismatch)
		res_mismatch = getattr(frappe.local, "execution_payload", {})
		self.assertEqual(res_mismatch.get("status"), "Success")
		self.assertIn("Mismatch Stop", [s.get("action") for s in res_mismatch.get("path_trace", [])])

		# Export / Import round-trip and execution verification on raw string rule
		exported_str = export_rule(reloaded_str.name)
		imp_str_name = f"{rule_str_name}_Imp"
		exported_str["rule"]["rule_name"] = imp_str_name
		import_rule(exported_str)
		imported_str = frappe.get_doc("Rule", imp_str_name)
		imp_str_action = next(a for a in imported_str.actions if a.action_id == "cond_str")
		self.assertEqual(imp_str_action.compiled_expression, "doc.description == 'MATCH'")

		RuleEngine(imported_str).execute(todo_match)
		res_imp_str = getattr(frappe.local, "execution_payload", {})
		self.assertEqual(res_imp_str.get("status"), "Success")
		self.assertIn("Match Stop", [s.get("action") for s in res_imp_str.get("path_trace", [])])

		# 2. Structured condition tree (JSON array)
		rule_tree_name = f"{self._test_prefix}_Tree_Cond"
		tree_payload = [{"left": {"ref": "doc.description"}, "op": "==", "right": {"value": "MATCH"}}]
		rule_tree = (
			RuleBuilder(rule_tree_name)
			.document_type("ToDo")
			.active(1)
			.entry_action(next_step="cond_tree")
			.condition(
				"Check Tree Cond",
				tree_payload,
				next_true="stop_true",
				next_false="stop_false",
				action_id="cond_tree",
			)
			.stop("Match Stop", action_id="stop_true")
			.stop("Mismatch Stop", action_id="stop_false")
			.build()
		)

		reloaded_tree = frappe.get_doc("Rule", rule_tree.name)
		cond_action_tree = next(a for a in reloaded_tree.actions if a.action_id == "cond_tree")
		self.assertTrue(cond_action_tree.compiled_expression)
		self.assertIn("MATCH", cond_action_tree.compiled_expression)

		# Export / Import round-trip and execution verification on structured tree rule
		exported_tree = export_rule(reloaded_tree.name)
		imp_tree_name = f"{rule_tree_name}_Imp"
		exported_tree["rule"]["rule_name"] = imp_tree_name
		import_rule(exported_tree)
		imported_tree = frappe.get_doc("Rule", imp_tree_name)
		imp_tree_action = next(a for a in imported_tree.actions if a.action_id == "cond_tree")
		self.assertTrue(imp_tree_action.compiled_expression)
		self.assertIn("MATCH", imp_tree_action.compiled_expression)

		RuleEngine(imported_tree).execute(todo_match)
		res_imp_tree = getattr(frappe.local, "execution_payload", {})
		self.assertEqual(res_imp_tree.get("status"), "Success")
		self.assertIn("Match Stop", [s.get("action") for s in res_imp_tree.get("path_trace", [])])

		# 3. Legacy condition_json payload
		rule_legacy_name = f"{self._test_prefix}_Legacy_Cond"
		rule_legacy = (
			RuleBuilder(rule_legacy_name)
			.document_type("ToDo")
			.active(1)
			.entry_action(next_step="cond_legacy")
			.condition(
				"Check Legacy Cond",
				tree_payload,
				next_true="stop_true",
				next_false="stop_false",
				action_id="cond_legacy",
				use_legacy_field=True,
			)
			.stop("Match Stop", action_id="stop_true")
			.stop("Mismatch Stop", action_id="stop_false")
			.build()
		)

		reloaded_legacy = frappe.get_doc("Rule", rule_legacy.name)
		cond_action_legacy = next(a for a in reloaded_legacy.actions if a.action_id == "cond_legacy")
		self.assertIsNotNone(get_condition_payload(cond_action_legacy))
		self.assertTrue(cond_action_legacy.compiled_expression)

		RuleEngine(reloaded_legacy).execute(todo_match)
		res_legacy = getattr(frappe.local, "execution_payload", {})
		self.assertEqual(res_legacy.get("status"), "Success")
		self.assertIn("Match Stop", [s.get("action") for s in res_legacy.get("path_trace", [])])

		# 4. Explicitly empty condition ({}) -> compiles to "True" and executes true branch
		rule_empty_name = f"{self._test_prefix}_Empty_Cond"
		rule_empty = (
			RuleBuilder(rule_empty_name)
			.document_type("ToDo")
			.active(1)
			.entry_action(next_step="cond_empty")
			.condition(
				"Empty Cond",
				{},
				next_true="stop_true",
				next_false="stop_false",
				action_id="cond_empty",
			)
			.stop("Match Stop", action_id="stop_true")
			.stop("Mismatch Stop", action_id="stop_false")
			.build()
		)

		reloaded_empty = frappe.get_doc("Rule", rule_empty.name)
		cond_action_empty = next(a for a in reloaded_empty.actions if a.action_id == "cond_empty")
		self.assertEqual(cond_action_empty.compiled_expression, "True")

		RuleEngine(reloaded_empty).execute(todo_match)
		res_empty = getattr(frappe.local, "execution_payload", {})
		self.assertEqual(res_empty.get("status"), "Success")
		self.assertIn("Match Stop", [s.get("action") for s in res_empty.get("path_trace", [])])
