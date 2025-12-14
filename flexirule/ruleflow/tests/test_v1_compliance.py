import frappe
import unittest
import json
from flexirule.ruleflow.core.coordinator import RuleCoordinator
from flexirule.ruleflow.core.engine import RuleEngine
from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity

class TestV1Compliance(unittest.TestCase):
	def setUp(self):
		pass

	def test_eligibility_mode_strict(self):
		"""
		V1 Contract: Mode check (Sync/Async)
		"""
		# Create a dummy rule doc
		rule = frappe.new_doc('Rule')
		rule.is_active = 1
		rule.trigger_event = 'Before Save'
		rule.document_type = 'ToDo'
		# Only memory, don't save
		
		# Test Signature
		val = RuleCoordinator.check_eligibility(rule, frappe.new_doc('ToDo'), 'Before Save')
		# Expect tuple
		self.assertIsInstance(val, tuple)
		is_eligible, reason = val
		
		self.assertTrue(is_eligible)
		
		# Test Mismatch Event
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, frappe.new_doc('ToDo'), 'After Save')
		self.assertFalse(is_eligible)
		self.assertIn("Event mismatch", reason)

		# Test Trigger Condition (JSON)
		rule.trigger_condition = json.dumps([{"field": "status", "operator": "==", "value": "Open"}])
		# Note: The test setup below assumes ConditionEvaluator handles the list-based JSON format
		# If ConditionEvaluator expects a different key, we might need to adjust.
		# Based on evaluator.py: it expects a list of conditions or object.
		# Let's check evaluator.py again lightly effectively. 
		# evaluator.py: self.conditions = json.loads(conditions_json). 
		# _evaluate_group expects list of dicts. {'left':..., 'operator':..., 'right':...}
		# My update in coordinator uses `evaluator.evaluate(doc)`.
		
		# Let's construct a valid condition JSON for ConditionEvaluator
		condition_json = json.dumps([
			{"left": {"type": "field", "value": "status"}, "operator": "==", "right": "Open"}
		])
		rule.trigger_condition = condition_json
		
		doc = frappe.new_doc('ToDo')
		doc.status = "Closed"
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, doc, 'Before Save')
		self.assertFalse(is_eligible)
		self.assertIn("Trigger Condition (JSON) mismatch", reason)
		
		doc.status = "Open"
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, doc, 'Before Save')
		self.assertTrue(is_eligible)

	def test_graph_cycle_detection(self):
		"""
		V1 Contract: Acyclic Graph
		"""
		rule = frappe.new_doc('Rule')
		rule.append('actions', {
			'action_id': 'A',
			'action_type': 'Process', 
			'action_label': 'Step A',
			'next_step_if_true': 'B'
		})
		rule.append('actions', {
			'action_id': 'B',
			'action_type': 'Process', 
			'action_label': 'Step B',
			'next_step_if_true': 'A' # Cycle
		})
		
		with self.assertRaises(frappe.ValidationError) as cm:
			validate_graph_integrity(rule)
		self.assertIn("Cycle detected", str(cm.exception))

	def test_orphan_detection(self):
		"""
		V1 Contract: Connected Graph (No orphans)
		"""
		rule = frappe.new_doc('Rule')
		rule.append('actions', {
			'action_id': 'A',
			'action_type': 'Process', 
			'action_label': 'Step A',
			'is_entry_action': 1,
			'next_step_if_true': 'B' # B doesn't exist yet
		})
		# Valid so far if B was added, but let's add C which is disconnected
		rule.append('actions', {
			'action_id': 'C',
			'action_type': 'Process',
			'action_label': 'Step C'
		})
		
		with self.assertRaises(frappe.ValidationError) as cm:
			validate_graph_integrity(rule)
		self.assertIn("Unreachable", str(cm.exception))
