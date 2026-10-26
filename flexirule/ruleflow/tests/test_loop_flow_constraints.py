import json

from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.validation_service import _validate_flow_constraints


class TestLoopFlowConstraints(FrappeTestCase):
	def test_loop_requires_a_body_path(self):
		result = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": None,
					"next_step_if_false": "after",
				},
				{
					"action_id": "after",
					"action_type": "Stop",
					"action_label": "End",
					"next_step_if_true": None,
					"next_step_if_false": None,
				},
			],
		)

		self.assertFalse(result["valid"])
		self.assertTrue(
			any("missing its required body path" in error for error in result["errors"]),
			result["errors"],
		)
		self.assertFalse(
			any("missing its required false path" in error for error in result["errors"]),
			result["errors"],
		)

	def test_loop_with_body_and_after_last_paths_passes_path_validation(self):
		result = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": "body",
					"next_step_if_false": "after",
				},
				{
					"action_id": "body",
					"action_type": "Assignment",
					"action_label": "Update Item",
					"next_step_if_true": "loop",
					"next_step_if_false": None,
				},
				{
					"action_id": "after",
					"action_type": "Stop",
					"action_label": "End",
					"next_step_if_true": None,
					"next_step_if_false": None,
				},
			],
		)

		self.assertFalse(
			any("missing its required body path" in error for error in result["errors"]),
			result["errors"],
		)
		self.assertFalse(
			any("missing its required false path" in error for error in result["errors"]),
			result["errors"],
		)

	def test_loop_rejects_nonexistent_body_destination(self):
		result = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": "missing-body",
					"next_step_if_false": "after",
				},
				{
					"action_id": "after",
					"action_type": "Stop",
					"action_label": "End",
					"next_step_if_true": None,
					"next_step_if_false": None,
				},
			],
		)

		self.assertTrue(
			any("points to missing body action" in error for error in result["errors"]),
			result["errors"],
		)

	def test_loop_rejects_nonexistent_after_last_destination(self):
		result = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": "body",
					"next_step_if_false": "missing-after",
				},
				{
					"action_id": "body",
					"action_type": "Assignment",
					"action_label": "Update Item",
					"next_step_if_true": "loop",
					"next_step_if_false": None,
				},
			],
		)

		self.assertTrue(
			any("points to missing After Last action" in error for error in result["errors"]),
			result["errors"],
		)

	def test_loop_rejects_same_destination_for_body_and_after_last(self):
		result = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": "shared",
					"next_step_if_false": "shared",
				},
				{
					"action_id": "shared",
					"action_type": "Assignment",
					"action_label": "Update Item",
					"next_step_if_true": "loop",
					"next_step_if_false": None,
				},
			],
		)

		self.assertTrue(
			any("different destinations for its body and After Last" in error for error in result["errors"]),
			result["errors"],
		)

	def test_loop_body_must_have_a_route_back_to_owning_loop(self):
		result = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": "body",
					"next_step_if_false": "after",
				},
				{
					"action_id": "body",
					"action_type": "Assignment",
					"action_label": "Update Item",
					"next_step_if_true": "after",
					"next_step_if_false": None,
				},
				{
					"action_id": "after",
					"action_type": "Stop",
					"action_label": "End",
					"next_step_if_true": None,
					"next_step_if_false": None,
				},
			],
		)

		self.assertTrue(
			any("no body path that returns to the Loop" in error for error in result["errors"]),
			result["errors"],
		)

	def test_nested_loop_after_last_can_return_to_enclosing_loop(self):
		result = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "outer",
					"action_type": "Loop",
					"action_label": "Outer Loop",
					"next_step_if_true": "inner",
					"next_step_if_false": "done",
				},
				{
					"action_id": "inner",
					"action_type": "Loop",
					"action_label": "Inner Loop",
					"next_step_if_true": "inner-body",
					"next_step_if_false": "outer",
				},
				{
					"action_id": "inner-body",
					"action_type": "Assignment",
					"action_label": "Inner Body",
					"next_step_if_true": "inner",
					"next_step_if_false": None,
				},
				{
					"action_id": "done",
					"action_type": "Stop",
					"action_label": "End",
					"next_step_if_true": None,
					"next_step_if_false": None,
				},
			],
		)

		self.assertFalse(
			any("no body path that returns to the Loop" in error for error in result["errors"]),
			result["errors"],
		)

	def test_loop_body_can_return_through_switch_case_when_fallback_does_not(self):
		result = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": "switch",
					"next_step_if_false": "after",
				},
				{
					"action_id": "switch",
					"action_type": "Switch",
					"action_label": "Route Item",
					"config": json.dumps({"expression": "doc.status", "cases": {"Done": "loop"}}),
					"next_step_if_true": "fallback",
					"next_step_if_false": "fallback",
				},
				{
					"action_id": "fallback",
					"action_type": "Stop",
					"action_label": "Fallback Stop",
					"next_step_if_true": None,
					"next_step_if_false": None,
				},
				{
					"action_id": "after",
					"action_type": "Stop",
					"action_label": "End",
					"next_step_if_true": None,
					"next_step_if_false": None,
				},
			],
		)

		self.assertFalse(
			any("no body path that returns to the Loop" in error for error in result["errors"]),
			result["errors"],
		)

	def test_loop_rejects_self_referential_body_and_after_last(self):
		self_referential_body = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": "loop",
					"next_step_if_false": "after",
				},
				{
					"action_id": "after",
					"action_type": "Stop",
					"action_label": "End",
					"next_step_if_true": None,
					"next_step_if_false": None,
				},
			],
		)
		self.assertTrue(
			any("cannot use itself as its body" in error for error in self_referential_body["errors"]),
			self_referential_body["errors"],
		)

		self_referential_after_last = _validate_flow_constraints(
			{"is_active": 0},
			[
				{
					"action_id": "loop",
					"action_type": "Loop",
					"action_label": "Loop Items",
					"next_step_if_true": "body",
					"next_step_if_false": "loop",
				},
				{
					"action_id": "body",
					"action_type": "Assignment",
					"action_label": "Update Item",
					"next_step_if_true": "loop",
					"next_step_if_false": None,
				},
			],
		)
		self.assertTrue(
			any(
				"cannot route After Last back to itself" in error
				for error in self_referential_after_last["errors"]
			),
			self_referential_after_last["errors"],
		)
