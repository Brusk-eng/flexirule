#!/usr/bin/env python3
"""
Debug script to understand the test failure
"""
import frappe

# Initialize frappe
frappe.connect()

# Create a dummy rule doc like in the test
rule = frappe.new_doc('Rule')
rule.is_active = 1
rule.trigger_event = 'Before Save'
rule.document_type = 'ToDo'

print("Rule attributes:")
print(f"is_active: {getattr(rule, 'is_active', 'NOT_SET')}")
print(f"trigger_event: {getattr(rule, 'trigger_event', 'NOT_SET')}")
print(f"document_type: {getattr(rule, 'document_type', 'NOT_SET')}")
print(f"trigger_condition: {repr(getattr(rule, 'trigger_condition', 'NOT_SET'))}")
print(f"trigger_condition_expression: {repr(getattr(rule, 'trigger_condition_expression', 'NOT_SET'))}")

print("\nUsing .get():")
print(f"rule.get('trigger_condition'): {repr(rule.get('trigger_condition'))}")
print(f"rule.get('trigger_condition_expression'): {repr(rule.get('trigger_condition_expression'))}")

print("\nBoolean checks:")
print(f"bool(rule.get('trigger_condition')): {bool(rule.get('trigger_condition'))}")
print(f"bool(rule.get('trigger_condition_expression')): {bool(rule.get('trigger_condition_expression'))}")

from flexirule.ruleflow.core.coordinator import RuleCoordinator

# Test eligibility
val = RuleCoordinator.check_eligibility(rule, frappe.new_doc('ToDo'), 'Before Save')
print(f"\nEligibility result: {val}")
print(f"is_eligible: {val[0]}")
print(f"reason: {val[1]}")

frappe.destroy()