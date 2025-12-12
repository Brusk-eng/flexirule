# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Tests for Bolton Rule Engine

All process methods use the context-first pattern:
    result = method_name(context, **config)
    where context contains 'doc' and 'vars'
"""

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase


class TestRuleEngine(FrappeTestCase):
    """Test cases for Rule Engine"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user('Administrator')
        # Create test rule
        if not frappe.db.exists("Rule", "Test Validation Rule"):
            frappe.get_doc({
                "doctype": "Rule",
                "rule_name": "Test Validation Rule",
                "document_type": "ToDo",
                "trigger_event": "Validate",
                "is_active": 1,
                "priority": 10
            }).insert(ignore_permissions=True)
    
    def test_rule_creation(self):
        """Test rule is created correctly"""
        rule = frappe.get_doc("Rule", "Test Validation Rule")
        self.assertEqual(rule.document_type, "ToDo")
        self.assertEqual(rule.is_active, 1)
    
    def test_process_method_loading(self):
        """Test process methods can be loaded"""
        from flexirule.ruleflow.methods.validation import validate_required_fields
        from flexirule.ruleflow.methods.enrichment import set_default_value
        
        self.assertTrue(callable(validate_required_fields))
        self.assertTrue(callable(set_default_value))
    
    @classmethod  
    def tearDownClass(cls):
        # Cleanup - don't delete, just rollback
        frappe.db.rollback()
        super().tearDownClass()


class TestValidationMethods(FrappeTestCase):
    """Test validation process methods"""
    
    def test_validate_required_fields_pass(self):
        """Test required fields validation passes"""
        from flexirule.ruleflow.methods.validation import validate_required_fields
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
        context = {"doc": doc, "vars": {}}
        result = validate_required_fields(context, fields=["description"])
        self.assertTrue(result)
    
    def test_validate_required_fields_fail(self):
        """Test required fields validation fails"""
        from flexirule.ruleflow.methods.validation import validate_required_fields
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": ""})
        context = {"doc": doc, "vars": {}}
        
        with self.assertRaises(frappe.ValidationError):
            validate_required_fields(context, fields=["description"])
    
    def test_validate_field_pattern(self):
        """Test regex pattern validation"""
        from flexirule.ruleflow.methods.validation import validate_field_pattern
        
        doc = frappe._dict({"email": "test@example.com"})
        context = {"doc": doc, "vars": {}}
        result = validate_field_pattern(context, field="email", pattern=r".*@.*\..*")
        self.assertTrue(result)


class TestEnrichmentMethods(FrappeTestCase):
    """Test enrichment process methods"""
    
    def test_set_default_value(self):
        """Test default value setting"""
        from flexirule.ruleflow.methods.enrichment import set_default_value
        
        # Use actual document, not _dict
        doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
        context = {"doc": doc, "vars": {}}
        result = set_default_value(context, field="priority", default_value="Medium")
        
        self.assertEqual(doc.priority, "Medium")
        self.assertEqual(result, "Medium")
    
    def test_set_default_no_overwrite(self):
        """Test default doesn't overwrite existing"""
        from flexirule.ruleflow.methods.enrichment import set_default_value
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "Test", "priority": "High"})
        context = {"doc": doc, "vars": {}}
        result = set_default_value(context, field="priority", default_value="Low", overwrite=False)
        
        self.assertEqual(doc.priority, "High")
    
    def test_calculate_field_value(self):
        """Test formula calculation"""
        from flexirule.ruleflow.methods.enrichment import calculate_field_value
        
        # Use actual document with set() method
        doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
        context = {"doc": doc, "vars": {}}
        result = calculate_field_value(context, target_field="priority", formula='"High"')
        
        self.assertEqual(doc.priority, "High")

