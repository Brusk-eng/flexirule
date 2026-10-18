import uuid

import frappe

from flexirule.ruleflow.tests.builder import RuleBuilder
from flexirule.ruleflow.tests.factories import make_test_contact
from flexirule.ruleflow.tests.test_case import FlexiRuleTestCase


class TestRuleRefactored(FlexiRuleTestCase):
	def setUp(self):
		super().setUp()
		self._test_prefix = f"FRX_REFACT_{uuid.uuid4().hex[:8]}"

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

	def test_active_rule_requires_next_step(self):
		# Using RuleBuilder to verify validation logic
		builder = (
			RuleBuilder(f"{self._test_prefix}_Missing_False_Path")
			.document_type("ToDo")
			.entry_action(next_step="condition_1")
			.condition(
				"Check",
				'[{"left":{"ref":"doc.description"},"op":"!=","right":{"value":""}}]',
				next_true="stop_1",
			)
			.stop("Stop", action_id="stop_1")
		)

		with self.assertRaises(frappe.ValidationError):
			builder.build()

	def test_notify_email_validation(self):
		builder = (
			RuleBuilder(f"{self._test_prefix}_Notify_Validation")
			.document_type("ToDo")
			.entry_action(next_step="notify_1")
			.add_action(
				action_id="notify_1",
				action_type="Notify",
				action_label="Notify Email",
				operation="Email",
				value_template="Hello {{ doc.description }}",
				config="{}",
			)
		)

		with self.assertRaises(frappe.ValidationError):
			builder.build()

	def test_sub_rule_visibility_validation(self):
		# Target not exposed as subrule
		target_rule = (
			RuleBuilder(f"{self._test_prefix}_Hidden_Target")
			.document_type("ToDo")
			.subrule(exposed=0)
			.entry_action()
			.build()
		)

		parent_builder = (
			RuleBuilder(f"{self._test_prefix}_Parent_Rule")
			.document_type("ToDo")
			.entry_action(next_step="call_sub")
			.sub_rule_call("Call Target", target_rule.name, action_id="call_sub")
		)

		with self.assertRaises(frappe.ValidationError):
			parent_builder.build()
