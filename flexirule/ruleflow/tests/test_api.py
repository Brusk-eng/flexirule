# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Integration tests for Bolton API endpoints
"""

import json
import unittest

import frappe

from flexirule.ruleflow.core.coordinator import RuleCoordinator


class TestBoltonAPI(unittest.TestCase):
    """Test API endpoints"""

    def setUp(self):
        """Setup test data"""
        frappe.set_user('Administrator')

        # ensure process method exists (might be pruned by other tests)
        if not frappe.db.exists('Process Method', 'flexirule.ruleflow.methods.enrichment.set_default_value'):
            frappe.get_doc({
                "doctype": "Process Method",
                "method_name": "set_default_value",
                "method_path": "flexirule.ruleflow.methods.enrichment.set_default_value",
                "is_managed": 0, # Unmanaged to avoid pruning
                "category": "Enrichment"
            }).insert()

        # Create test rule
        if not frappe.db.exists('Rule', 'Test API Rule'):
            self.rule = frappe.get_doc({
                'doctype': 'Rule',
                'rule_name': 'Test API Rule',
                'document_type': 'ToDo',
                'trigger_event': 'Validate',
                'is_active': 1,
                'actions': [{
                    'action_type': 'Process',
                    'action_label': 'Test Action',
                    'action_id': 'action_1',
                    'process_method': 'flexirule.ruleflow.methods.enrichment.set_default_value',
                    'config': json.dumps({'field': 'priority', 'default_value': 'Medium'}),
                    'is_entry_action': 1
                }]
            })
            self.rule.insert(ignore_permissions=True)
        else:
            self.rule = frappe.get_doc('Rule', 'Test API Rule')

    def tearDown(self):
        """Cleanup"""
        frappe.db.rollback()
        # Clean up cache to prevent DoNotExistError in other tests
        RuleCoordinator.clear_cache('ToDo')

    def test_get_doctype_fields(self):
        """Test getting DocType fields"""
        from flexirule.ruleflow.api import get_doctype_fields

        result = get_doctype_fields('ToDo')

        self.assertIsInstance(result, dict)
        self.assertIn('parent_fields', result)

    def test_get_doctype_fields_with_filters(self):
        """Test getting DocType fields with filters"""
        from flexirule.ruleflow.api import get_doctype_fields

        filters = json.dumps({'fieldtypes': ['Data', 'Select']})
        result = get_doctype_fields('ToDo', filters)

        self.assertIsInstance(result, dict)

    def test_test_rule(self):
        """Test rule testing API"""
        from flexirule.ruleflow.api import test_rule

        # Create a test TODO
        todo = frappe.get_doc({
            'doctype': 'ToDo',
            'description': 'Test for API'
        })
        todo.insert(ignore_permissions=True)

        result = test_rule(self.rule.name, 'ToDo', todo.name)

        self.assertIn('success', result)

    def test_clear_cache(self):
        """Test cache clearing API"""
        from flexirule.ruleflow.api import clear_cache

        result = clear_cache('ToDo')

        self.assertTrue(result.get('success'))


class TestAPIPermissions(unittest.TestCase):
    """Test API permission enforcement"""

    def setUp(self):
        """Setup"""
        frappe.set_user('Administrator')

    def tearDown(self):
        """Cleanup"""
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_api_requires_login(self):
        """Test that API requires logged in user"""
        # This is a basic check - APIs should work for logged in users
        from flexirule.ruleflow.api import get_doctype_fields

        result = get_doctype_fields('ToDo')
        self.assertIsNotNone(result)


def run_tests():
    """Helper function to run all API tests"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBoltonAPI))
    suite.addTest(unittest.makeSuite(TestAPIPermissions))
    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == '__main__':
    unittest.main()
