# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Unit tests for Bolton Process Methods

All methods use the context-first pattern:
    result = method_name(context, **config)
    where context contains 'doc' and 'vars'
"""

import frappe
import unittest
from flexirule.ruleflow.methods import validation, enrichment, notifications, deduplication


class TestValidationMethods(unittest.TestCase):
    """Test validation process methods"""
    
    def setUp(self):
        """Setup test document and context"""
        self.doc = frappe.get_doc({
            'doctype': 'ToDo',
            'description': 'Test ToDo'
        })
        self.context = {'doc': self.doc, 'vars': {}}
    
    def test_validate_required_fields_success(self):
        """Test required field validation passes when fields present"""
        self.doc.description = 'Valid description'
        
        result = validation.validate_required_fields(
            self.context,
            fields=['description']
        )
        
        self.assertTrue(result)
    
    def test_validate_required_fields_failure(self):
        """Test required field validation fails when fields missing"""
        self.doc.description = None
        
        with self.assertRaises(frappe.ValidationError):
            validation.validate_required_fields(
                self.context,
                fields=['description']
            )
    
    def test_validate_field_pattern_success(self):
        """Test pattern validation succeeds with valid pattern"""
        # Use a doc with the field set
        doc = frappe._dict({'email': 'test@example.com'})
        context = {'doc': doc, 'vars': {}}
        
        result = validation.validate_field_pattern(
            context,
            field='email',
            pattern=r'.*@.*\..*'
        )
        
        self.assertTrue(result)
    
    def test_validate_field_pattern_empty_passes(self):
        """Test that empty values pass pattern validation"""
        doc = frappe._dict({'email': ''})
        context = {'doc': doc, 'vars': {}}
        
        result = validation.validate_field_pattern(
            context,
            field='email',
            pattern=r'.*@.*\..*'
        )
        
        self.assertTrue(result)


class TestEnrichmentMethods(unittest.TestCase):
    """Test enrichment process methods"""
    
    def setUp(self):
        """Setup test data"""
        # Use actual document instead of _dict for .set() method
        self.doc = frappe.get_doc({
            'doctype': 'ToDo',
            'description': 'Test'
        })
        self.context = {'doc': self.doc, 'vars': {}}
    
    def test_set_default_value(self):
        """Test setting default values"""
        result = enrichment.set_default_value(
            self.context,
            field='priority',
            default_value='Medium'
        )
        
        self.assertEqual(result, 'Medium')
        self.assertEqual(self.doc.priority, 'Medium')
    
    def test_set_default_value_no_overwrite(self):
        """Test that default doesn't overwrite existing value"""
        self.doc.priority = 'High'
        
        result = enrichment.set_default_value(
            self.context,
            field='priority',
            default_value='Low',
            overwrite=False
        )
        
        self.assertEqual(result, 'High')
        self.assertEqual(self.doc.priority, 'High')
    
    def test_calculate_field_value(self):
        """Test field calculation"""
        self.doc.description = "Test"
        
        result = enrichment.calculate_field_value(
            self.context,
            target_field='priority',  # Use a field that exists
            formula='"High"'  # Simple string result
        )
        
        self.assertEqual(result, 'High')
        self.assertEqual(self.doc.priority, 'High')


class TestNotificationMethods(unittest.TestCase):
    """Test notification process methods"""
    
    def setUp(self):
        """Setup test data"""
        frappe.set_user('Administrator')
        self.doc = frappe.get_doc({
            'doctype': 'ToDo',
            'description': 'Test Notification'
        })
        self.doc.insert(ignore_permissions=True)
        self.context = {'doc': self.doc, 'vars': {}}
    
    def tearDown(self):
        """Cleanup"""
        frappe.db.rollback()
    
    def test_create_comment(self):
        """Test comment creation"""
        comment_name = notifications.create_comment(
            self.context,
            comment_text='Test comment from rule'
        )
        
        self.assertIsNotNone(comment_name)
        
        # Verify comment was created
        comment = frappe.get_doc('Comment', comment_name)
        self.assertEqual(comment.content, 'Test comment from rule')


class TestDeduplicationMethods(unittest.TestCase):
    """Test deduplication process methods"""
    
    def setUp(self):
        """Setup test data"""
        frappe.set_user('Administrator')
        # Create test ToDo items
        self.doc1 = frappe.get_doc({
            'doctype': 'ToDo',
            'description': 'First test item for dedup'
        })
        self.doc1.insert(ignore_permissions=True)
        
        self.doc2 = frappe.get_doc({
            'doctype': 'ToDo',
            'description': 'First test item for dedup'  # Duplicate description
        })
        # Don't insert doc2 yet - we're testing duplicate detection before save
        
        self.context = {'doc': self.doc2, 'vars': {}}
    
    def tearDown(self):
        """Cleanup"""
        frappe.db.rollback()
    
    def test_find_duplicates_by_fields(self):
        """Test exact duplicate detection"""
        # doc2 needs a name for the exclusion filter
        self.doc2.name = 'temp-new'
        
        duplicates = deduplication.find_duplicates_by_fields(
            self.context,
            fields=['description']
        )
        
        self.assertGreaterEqual(len(duplicates), 1)
        self.assertIn(self.doc1.name, duplicates)


def run_tests():
    """Helper function to run all method tests"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestValidationMethods))
    suite.addTest(unittest.makeSuite(TestEnrichmentMethods))
    suite.addTest(unittest.makeSuite(TestNotificationMethods))
    suite.addTest(unittest.makeSuite(TestDeduplicationMethods))
    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == '__main__':
    unittest.main()


def run_tests():
    """Helper function to run all method tests"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestValidationMethods))
    suite.addTest(unittest.makeSuite(TestEnrichmentMethods))
    suite.addTest(unittest.makeSuite(TestNotificationMethods))
    suite.addTest(unittest.makeSuite(TestDeduplicationMethods))
    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == '__main__':
    unittest.main()
