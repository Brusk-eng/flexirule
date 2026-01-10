# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Unit tests for FlexiRule Process Methods
"""

import unittest
import frappe
from flexirule.ruleflow.doctype.process.process import Process


class TestValidationMethods(unittest.TestCase):
    """Test validation process methods using the new Process architecture"""

    def setUp(self):
        """Setup test document and context"""
        self.doc = frappe.get_doc({"doctype": "ToDo", "description": "Test ToDo"})
        self.context = {"doc": self.doc, "vars": {}}
        self.process = frappe.get_doc("Process", "Validation")

    def test_validate_required_fields_success(self):
        """Test required field validation passes when fields present"""
        self.doc.description = "Valid description"

        result = self.process.execute(
            self.context, func="required_fields", config={"fields": ["description"]}
        )

        self.assertTrue(result)

    def test_validate_required_fields_failure(self):
        """Test required field validation fails when fields missing"""
        self.doc.description = None

        with self.assertRaises(frappe.ValidationError):
            self.process.execute(
                self.context, func="required_fields", config={"fields": ["description"]}
            )

    def test_validate_field_pattern_success(self):
        """Test pattern validation succeeds with valid pattern"""
        doc = frappe._dict({"email": "test@example.com"})
        context = {"doc": doc, "vars": {}}

        result = self.process.execute(
            context,
            func="field_pattern",
            config={
                "field": "email",
                "pattern_type": "Custom Regex",
                "pattern": r".*@.*\..*",
            },
        )

        self.assertTrue(result)

    def test_validate_field_pattern_empty_passes(self):
        """Test that empty values pass pattern validation"""
        doc = frappe._dict({"email": ""})
        context = {"doc": doc, "vars": {}}

        result = self.process.execute(
            context,
            func="field_pattern",
            config={
                "field": "email",
                "pattern_type": "Custom Regex",
                "pattern": r".*@.*\..*",
            },
        )

        self.assertTrue(result)


class TestEnrichmentMethods(unittest.TestCase):
    """Test enrichment process methods using the new Process architecture"""

    def setUp(self):
        """Setup test data"""
        self.doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
        self.context = {"doc": self.doc, "vars": {}}
        self.process = frappe.get_doc("Process", "Enrichment")

    def test_set_value(self):
        """Test setting field values"""
        result = self.process.execute(
            self.context,
            func="set_value",
            config={"field": "priority", "value": "Medium"},
        )

        self.assertEqual(result, "Medium")
        self.assertEqual(self.doc.priority, "Medium")

    def test_set_value_no_overwrite(self):
        """Test that set_value doesn't overwrite existing value unless told to"""
        self.doc.priority = "High"

        result = self.process.execute(
            self.context,
            func="set_value",
            config={"field": "priority", "value": "Low", "overwrite": 0},
        )

        self.assertEqual(self.doc.priority, "High")

    def test_calculate_value(self):
        """Test field calculation using Safe Eval"""
        self.doc.description = "Test"

        result = self.process.execute(
            self.context,
            func="calculate_value",
            config={"target_field": "priority", "formula": '"High"'},
        )

        self.assertEqual(result, "High")
        self.assertEqual(self.doc.priority, "High")


class TestNotificationMethods(unittest.TestCase):
    """Test notification process methods using the new Process architecture"""

    def setUp(self):
        """Setup test data"""
        frappe.set_user("Administrator")
        self.doc = frappe.get_doc(
            {"doctype": "ToDo", "description": "Test Notification"}
        )
        self.doc.insert(ignore_permissions=True)
        self.context = {"doc": self.doc, "vars": {}}
        self.process = frappe.get_doc("Process", "Notification")

    def tearDown(self):
        """Cleanup"""
        frappe.db.rollback()

    def test_add_comment(self):
        """Test comment creation"""
        comment_name = self.process.execute(
            self.context,
            func="add_comment",
            config={"comment_text": "Test comment from rule"},
        )

        self.assertIsNotNone(comment_name)

        # Verify comment was created
        comment = frappe.get_doc("Comment", comment_name)
        self.assertEqual(comment.content, "Test comment from rule")


class TestDeduplicationMethods(unittest.TestCase):
    """Test deduplication process methods using the new Process architecture"""

    def setUp(self):
        """Setup test data"""
        frappe.set_user("Administrator")
        # Create test ToDo items
        self.doc1 = frappe.get_doc(
            {"doctype": "ToDo", "description": "First test item for dedup"}
        )
        self.doc1.insert(ignore_permissions=True)

        self.doc2 = frappe.get_doc(
            {"doctype": "ToDo", "description": "First test item for dedup"}
        )
        self.context = {"doc": self.doc2, "vars": {}}
        self.process = frappe.get_doc("Process", "Deduplication")

    def tearDown(self):
        """Cleanup"""
        frappe.db.rollback()

    def test_find_duplicates(self):
        """Test duplicate detection"""
        # doc2 needs a name for the exclusion filter
        self.doc2.name = "temp-new"

        # Deduplication.execute calls its module's execute, which dispatches 'find_duplicates'
        result = self.process.execute(
            self.context,
            func="find_duplicates",
            config={
                "overall_threshold": 0.8,
                "fields_config": [
                    {"fieldname": "description", "weight": 100, "algorithm": "Exact"}
                ],
            },
        )

        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        # Result should contain match names
        match_names = [m.get("name") for m in result]
        self.assertIn(self.doc1.name, match_names)


def run_tests():
    """Helper function to run all method tests"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestValidationMethods))
    suite.addTest(unittest.makeSuite(TestEnrichmentMethods))
    suite.addTest(unittest.makeSuite(TestNotificationMethods))
    suite.addTest(unittest.makeSuite(TestDeduplicationMethods))
    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == "__main__":
    unittest.main()
