# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.sub_rule_contract import (
	get_sub_rule_contract,
	validate_sub_rule_contract,
)


class TestSubRuleInterfaceContract(FrappeTestCase):
	def setUp(self):
		self.inferred_inputs = [
			{
				"fieldname": "party",
				"label": "Party",
				"fieldtype": "Link",
				"options": "Customer",
				"reqd": 1,
				"source": {"kind": "inferred_input"},
			}
		]
		self.inferred_outputs = [
			{
				"fieldname": "document_counts",
				"label": "Document Counts",
				"fieldtype": "Table",
				"reqd": 0,
				"source": {"kind": "sub_rule_output"},
				"children": [
					{
						"fieldname": "document_type",
						"label": "Document Type",
						"fieldtype": "Data",
						"reqd": 0,
						"source": {"kind": "literal"},
					},
					{
						"fieldname": "issued_count",
						"label": "Issued Count",
						"fieldtype": "Int",
						"reqd": 0,
						"source": {"kind": "aggregate"},
					},
				],
			}
		]

	def test_explicit_contract_normalizes_and_validates_declared_schemas(self):
		rule = {
			"name": "Customer Document Summary",
			"trigger_type": "Callable Event",
			"exposed_as_subrule": 1,
			"input_schema": json.dumps(
				[
					{
						"fieldname": "party",
						"label": "Customer",
						"fieldtype": "Link",
						"options": "Customer",
						"mandatory": 1,
					},
					{"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "reqd": 0},
				]
			),
			"output_schema": json.dumps(self.inferred_outputs),
		}
		with (
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_input_schema",
				return_value=self.inferred_inputs,
			),
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_output_schema",
				return_value=self.inferred_outputs,
			),
		):
			contract = get_sub_rule_contract(rule)

		self.assertTrue(contract["valid"], contract["errors"])
		self.assertTrue(contract["input_schema_declared"])
		self.assertTrue(contract["output_schema_declared"])
		self.assertEqual(contract["input_schema"][0]["reqd"], 1)
		self.assertNotIn("mandatory", contract["input_schema"][0])
		self.assertEqual(contract["output_schema"][0]["source"]["kind"], "sub_rule_output")
		self.assertEqual(contract["output_schema"][0]["children"][0]["source"]["kind"], "literal")

	def test_explicit_input_schema_must_declare_detected_required_variables(self):
		rule = {
			"name": "Incomplete Input Contract",
			"input_schema": json.dumps(
				[{"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "reqd": 0}]
			),
			"output_schema": json.dumps(self.inferred_outputs),
		}
		with (
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_input_schema",
				return_value=self.inferred_inputs,
			),
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_output_schema",
				return_value=self.inferred_outputs,
			),
		):
			contract = get_sub_rule_contract(rule)

		self.assertFalse(contract["valid"])
		self.assertTrue(any("party" in error for error in contract["errors"]))

	def test_explicit_output_schema_cannot_claim_an_unproduced_field(self):
		rule = {
			"name": "Incomplete Output Contract",
			"input_schema": json.dumps(self.inferred_inputs),
			"output_schema": json.dumps(
				[{"fieldname": "unknown_result", "label": "Unknown Result", "fieldtype": "Data"}]
			),
		}
		with (
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_input_schema",
				return_value=self.inferred_inputs,
			),
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_output_schema",
				return_value=self.inferred_outputs,
			),
		):
			contract = get_sub_rule_contract(rule)

		self.assertFalse(contract["valid"])
		self.assertTrue(any("unknown_result" in error for error in contract["errors"]))

	def test_legacy_rule_uses_inferred_contract_without_becoming_invalid(self):
		rule = {"name": "Legacy Callable Rule"}
		with (
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_input_schema",
				return_value=self.inferred_inputs,
			),
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_output_schema",
				return_value=self.inferred_outputs,
			),
		):
			contract = get_sub_rule_contract(rule)

		self.assertTrue(contract["valid"], contract["errors"])
		self.assertEqual(contract["input_schema_source"], "inferred")
		self.assertEqual(contract["output_schema_source"], "inferred")
		self.assertEqual(contract["input_schema"][0]["fieldname"], "party")

	def test_exposed_callable_rule_contract_validation_uses_public_interface(self):
		rule = {
			"name": "Incomplete Input Contract",
			"trigger_type": "Callable Event",
			"exposed_as_subrule": 1,
			"input_schema": json.dumps([]),
			"output_schema": json.dumps(self.inferred_outputs),
		}
		with (
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_input_schema",
				return_value=self.inferred_inputs,
			),
			patch(
				"flexirule.ruleflow.core.sub_rule_contract._inferred_output_schema",
				return_value=self.inferred_outputs,
			),
		):
			errors = validate_sub_rule_contract(rule)

		self.assertTrue(errors)
		self.assertTrue(any("party" in error for error in errors))
