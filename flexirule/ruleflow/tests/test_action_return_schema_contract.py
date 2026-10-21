# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.contract_dto import ContractDTOBuilder
from flexirule.ruleflow.core.validation_service import _validate_action_contracts


class TestActionReturnSchemaContract(FrappeTestCase):
	def _validate_action(self, action_type: str, **overrides) -> list[str]:
		action = {
			"action_type": action_type,
			"action_label": f"Test {action_type}",
			"operation": None,
			"return_type": None,
			"return_variable": None,
			"resolved_output_schema": "[]",
			"mutation_mode": None,
			"config": "{}",
			**overrides,
		}
		errors: list[str] = []
		_validate_action_contracts(
			action,
			action_type,
			action["action_label"],
			operation_metadata={},
			errors=errors,
			mode="draft",
		)
		return errors

	def test_empty_serialized_schema_does_not_require_return_variable_for_non_result_actions(self):
		for action_type in ("Entry Action", "Condition", "Assignment", "Stop"):
			with self.subTest(action_type=action_type):
				errors = self._validate_action(
					action_type,
					return_type="List of Records",
					resolved_output_schema="[]",
				)
				self.assertFalse(
					any("requires Return Variable Name for Return Schema" in error for error in errors),
					errors,
				)

	def test_hidden_return_type_with_empty_schema_does_not_require_return_variable(self):
		errors = self._validate_action(
			"Query Records",
			operation="Fetch Records",
			return_type="List of Records",
			resolved_output_schema="[]",
		)
		self.assertFalse(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_populated_schema_requires_return_variable_for_schema_capable_action(self):
		errors = self._validate_action(
			"Query Records",
			operation="Fetch Records",
			return_type="List of Records",
			resolved_output_schema='[{"fieldname": "name", "label": "Name"}]',
		)
		self.assertTrue(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_selected_visible_return_type_requires_return_variable(self):
		errors = self._validate_action(
			"Document Action",
			operation="Create New",
			return_type="Single Record",
			resolved_output_schema="[]",
		)
		self.assertTrue(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_loop_item_alias_requirement_is_preserved(self):
		errors = self._validate_action("Loop", operation=None, return_variable=None)
		self.assertTrue(
			any("requires Return Variable Name" in error for error in errors),
			errors,
		)

	def test_sub_rule_return_schema_capability_is_shared_with_frontend_dto(self):
		contract = HandlerRegistry.get_action_contract("Sub-Rule")
		self.assertTrue(contract.get("supports_return_schema"))
		dto = ContractDTOBuilder.build()
		self.assertIn("Sub-Rule", dto["action_types_with_return_schema"])
		self.assertNotIn("Condition", dto["action_types_with_return_schema"])
		self.assertNotIn("Assignment", dto["action_types_with_return_schema"])

	def test_has_resolved_output_schema_all_empty_and_populated_representations(self):
		from typing import Any

		from flexirule.ruleflow.core.contract_utils import _has_resolved_output_schema

		empty_cases: list[Any] = [
			None,
			"",
			"   ",
			"null",
			"[]",
			"{}",
			[],
			{},
			{"fields": []},
			{"properties": {}},
			[{"fieldname": ""}],
			[{"fieldname": "   "}],
			{"fields": [{"fieldname": ""}]},
			"invalid json {",
			{"foo": "bar"},
		]
		for empty_case in empty_cases:
			with self.subTest(case=empty_case):
				self.assertFalse(
					_has_resolved_output_schema(empty_case), f"Expected False for {empty_case!r}"
				)

		populated_cases: list[Any] = [
			[{"fieldname": "name"}],
			'[{"fieldname": "name"}]',
			{"fields": [{"fieldname": "name"}]},
			{"properties": {"qty": {"type": "integer"}}},
			'{"type": "object", "properties": {"qty": {"type": "integer"}}}',
		]
		for pop_case in populated_cases:
			with self.subTest(case=pop_case):
				self.assertTrue(_has_resolved_output_schema(pop_case), f"Expected True for {pop_case!r}")

	def test_operation_level_override_supports_return_schema_disabled(self):
		errors = self._validate_action(
			"Query Records",
			operation="Exist Record",
			return_type="Yes / No",
			resolved_output_schema='[{"fieldname": "name"}]',
		)
		self.assertFalse(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_yes_no_return_type_does_not_require_return_variable_without_schema(self):
		errors = self._validate_action(
			"Query Records",
			operation="Fetch Records",
			return_type="Yes / No",
			resolved_output_schema="[]",
		)
		self.assertFalse(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_disallowed_mutation_mode_does_not_create_false_positive_return_variable_requirement(self):
		errors = self._validate_action(
			"Query Records",
			operation="Fetch Records",
			mutation_mode="Batch Database Set",
			return_variable=None,
		)
		self.assertTrue(
			any("does not allow mutation mode 'Batch Database Set'" in error for error in errors),
			errors,
		)
		self.assertFalse(
			any("requires Return Variable Name when Mutation Mode is set" in error for error in errors),
			errors,
		)

	def test_permitted_mutation_mode_requires_return_variable(self):
		errors = self._validate_action(
			"Query Records",
			operation="Fetch Records",
			mutation_mode="Set Context Variable",
			return_variable=None,
		)
		self.assertTrue(
			any("requires Return Variable Name when Mutation Mode is set" in error for error in errors),
			errors,
		)

	def test_process_operation_policy_inference_empty_vs_populated(self):
		from flexirule.ruleflow.core.contracts import infer_process_operation_policy

		empty_op = {
			"writes_to": "None",
			"writes_vars": "[]",
			"output_schema": "{}",
		}
		policy = infer_process_operation_policy(empty_op)
		self.assertFalse(policy.get("require_return_variable"))
		self.assertFalse(policy.get("supports_return_schema"))
		self.assertFalse(policy.get("has_operation_output_schema"))

		context_op = {
			"writes_to": "Context",
			"writes_vars": "[]",
			"output_schema": "{}",
		}
		policy = infer_process_operation_policy(context_op)
		self.assertTrue(policy.get("require_return_variable"))

		vars_op = {
			"writes_to": "None",
			"writes_vars": '[{"fieldname": "target_var"}]',
			"output_schema": "{}",
		}
		policy = infer_process_operation_policy(vars_op)
		self.assertTrue(policy.get("require_return_variable"))

		schema_op = {
			"writes_to": "None",
			"writes_vars": "[]",
			"output_schema": '{"type": "object", "properties": {"qty": {"type": "integer"}}}',
		}
		policy = infer_process_operation_policy(schema_op)
		self.assertTrue(policy.get("supports_return_schema"))
		self.assertTrue(policy.get("has_operation_output_schema"))
		self.assertFalse(policy.get("require_return_variable"))

	def test_process_operation_with_populated_output_schema_requires_return_variable_during_validation(self):
		import json

		op_meta = {
			"writes_to": "None",
			"writes_vars": "[]",
			"output_schema": '{"type": "object", "properties": {"qty": {"type": "integer"}}}',
			"action_overrides": json.dumps(
				{
					"contract_v2": {
						"adapter_key": "lookup",
						"capabilities": {
							"writes_to": "None",
						},
						"policy": {
							"supports_return_schema": True,
							"has_operation_output_schema": True,
						},
						"config_schema": {"type": "object"},
						"result_schema": {"type": "object", "properties": {"qty": {"type": "integer"}}},
					}
				}
			),
		}
		action = {
			"action_type": "Process",
			"process_name": "SampleProc",
			"operation": "run_op",
			"action_label": "Test Process",
			"return_variable": None,
			"resolved_output_schema": "[]",
		}
		errors: list[str] = []
		_validate_action_contracts(
			action,
			"Process",
			"Test Process",
			operation_metadata={"SampleProc:run_op": op_meta},
			errors=errors,
			mode="draft",
		)
		self.assertTrue(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_genuine_write_requirement_cannot_be_canceled_by_explicit_override(self):
		from flexirule.ruleflow.core.contracts import infer_process_operation_policy

		context_op_with_override = {
			"writes_to": "Context",
			"writes_vars": "[]",
			"output_schema": "{}",
			"action_overrides": '{"policy": {"require_return_variable": false}}',
		}
		policy = infer_process_operation_policy(context_op_with_override)
		self.assertTrue(policy.get("require_return_variable"))
		self.assertTrue(policy.get("has_genuine_write"))

	def test_process_contract_v2_populated_writes_vars_with_writes_to_none_requires_return_variable(self):
		import json

		op_meta = {
			"writes_to": "None",
			"writes_vars": '[{"fieldname": "out_var"}]',
			"output_schema": "{}",
			"action_overrides": json.dumps(
				{
					"contract_v2": {
						"adapter_key": "lookup",
						"capabilities": {
							"writes_to": "None",
						},
						"policy": {
							"supports_return_schema": False,
						},
						"config_schema": {"type": "object"},
						"result_schema": {"type": "object"},
					}
				}
			),
		}
		action = {
			"action_type": "Process",
			"process_name": "SampleProc",
			"operation": "write_op",
			"action_label": "Test Write Process",
			"return_variable": None,
			"resolved_output_schema": "[]",
		}
		errors: list[str] = []
		_validate_action_contracts(
			action,
			"Process",
			"Test Write Process",
			operation_metadata={"SampleProc:write_op": op_meta},
			errors=errors,
			mode="draft",
		)
		self.assertTrue(
			any("requires Return Variable Name" in error for error in errors),
			errors,
		)

	def test_process_contract_v2_empty_writes_vars_with_writes_to_none_does_not_require_return_variable(self):
		import json

		op_meta = {
			"writes_to": "None",
			"writes_vars": "[]",
			"output_schema": "{}",
			"action_overrides": json.dumps(
				{
					"contract_v2": {
						"adapter_key": "lookup",
						"capabilities": {
							"writes_to": "None",
						},
						"policy": {
							"supports_return_schema": False,
						},
						"config_schema": {"type": "object"},
						"result_schema": {"type": "object"},
					}
				}
			),
		}
		action = {
			"action_type": "Process",
			"process_name": "SampleProc",
			"operation": "no_write_op",
			"action_label": "Test No Write Process",
			"return_variable": None,
			"resolved_output_schema": "[]",
		}
		errors: list[str] = []
		_validate_action_contracts(
			action,
			"Process",
			"Test No Write Process",
			operation_metadata={"SampleProc:no_write_op": op_meta},
			errors=errors,
			mode="draft",
		)
		self.assertFalse(
			any("requires Return Variable Name" in error for error in errors),
			errors,
		)

	def test_contradictory_explicit_policy_overrides_inferred_schema(self):
		from flexirule.ruleflow.core.contracts import infer_process_operation_policy

		op_with_override = {
			"writes_to": "None",
			"writes_vars": "[]",
			"output_schema": '{"type": "object", "properties": {"qty": {"type": "integer"}}}',
			"action_overrides": '{"policy": {"supports_return_schema": false}}',
		}
		policy = infer_process_operation_policy(op_with_override)
		self.assertFalse(policy.get("supports_return_schema"))

	def test_dto_consistency_for_return_schema_action_types(self):
		dto = ContractDTOBuilder.build()
		expected_types = {"Query Records", "Document Action", "Process", "Sub-Rule"}
		for action_type in expected_types:
			self.assertIn(action_type, dto["action_types_with_return_schema"])
		for non_schema_type in ("Condition", "Entry Action", "Assignment", "Stop"):
			self.assertNotIn(non_schema_type, dto["action_types_with_return_schema"])
