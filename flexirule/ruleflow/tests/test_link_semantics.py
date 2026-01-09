import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.compiler import ConditionCompiler
from flexirule.ruleflow.core.evaluator import ConditionEvaluator, check_link_match


class TestLinkSemantics(FrappeTestCase):
	def test_check_link_match_helper(self):
		# Test the helper function directly
		# Match
		self.assertTrue(check_link_match("ValA", ["DT", "ValA"], "=="))
		self.assertTrue(check_link_match("ValA", ["DT", ["ValA", "ValB"]], "in"))

		# Mismatch
		self.assertFalse(check_link_match("ValB", ["DT", "ValA"], "=="))
		self.assertFalse(check_link_match("ValC", ["DT", ["ValA", "ValB"]], "in"))

		# Invalid Structure (Safety)
		self.assertFalse(check_link_match("ValA", "NotAList", "=="))
		self.assertFalse(check_link_match("ValA", ["JustOneItem"], "=="))

	def test_compiler_generation(self):
		compiler = ConditionCompiler()

		# Case: Link Equality
		cond = {
			"left": {"ref": "doc.link_field"},
			"op": "==",
			"right": {"value": ["DoctypeA", "ValueA"]}
		}
		code = compiler.compile(cond)
		self.assertIn("check_link_match", code)
		self.assertIn("['DoctypeA', 'ValueA']", code)

	def test_evaluator_integration(self):
		# Create a dummy doc
		doc = frappe._dict({"link_field": "TargetValue"})

		# Condition: doc.link_field == ["AnyDocType", "TargetValue"]
		cond = {
			"left": {"ref": "doc.link_field"},
			"op": "==",
			"right": {"value": ["AnyDocType", "TargetValue"]}
		}

		evaluator = ConditionEvaluator(frappe.as_json([cond]))
		self.assertTrue(evaluator.evaluate(doc))

		# Change doc value
		doc.link_field = "WrongValue"
		self.assertFalse(evaluator.evaluate(doc))

	def test_in_operator_tuple(self):
		doc = frappe._dict({"status": "Draft"})

		# Condition: doc.status in ["StatusDoc", ["Draft", "Open"]]
		cond = {
			"left": {"ref": "doc.status"},
			"op": "in",
			"right": {"value": ["StatusDoc", ["Draft", "Open"]]}
		}

		evaluator = ConditionEvaluator(frappe.as_json([cond]))
		self.assertTrue(evaluator.evaluate(doc))

		doc.status = "Closed"
		self.assertFalse(evaluator.evaluate(doc))
