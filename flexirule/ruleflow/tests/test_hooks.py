# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow import hooks


class TestRuleHooks(FrappeTestCase):
	def test_execute_rules_accepts_rename_args(self):
		doc = SimpleNamespace(doctype="ToDo", name="HOOK-TEST")

		with patch("flexirule.ruleflow.hooks.execute_rules_from_event") as execute_from_event:
			hooks.execute_rules(doc, "before_rename", "OLD-NAME", "NEW-NAME", False)

		execute_from_event.assert_called_once_with(doc, "Before Rename")

	def test_execute_rules_maps_before_print(self):
		doc = SimpleNamespace(doctype="ToDo", name="HOOK-PRINT")

		with patch("flexirule.ruleflow.hooks.execute_rules_from_event") as execute_from_event:
			hooks.execute_rules(doc, "before_print", print_settings={})

		execute_from_event.assert_called_once_with(doc, "Before Print")
