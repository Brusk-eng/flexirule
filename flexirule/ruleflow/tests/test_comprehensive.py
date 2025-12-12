# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Comprehensive Unit Test Suite for Bolton Rule Engine
"""

import frappe
import unittest
import json
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock


def create_test_rule(name, doctype="ToDo", event="Validate", actions=None):
    """Helper to create test rules"""
    if frappe.db.exists("Rule", name):
        return frappe.get_doc("Rule", name)
    
    rule = frappe.get_doc({
        "doctype": "Rule",
        "rule_name": name,
        "document_type": doctype,
        "trigger_event": event,
        "is_active": 1,
        "priority": 100,
        "max_execution_time": 30
    })
    
    if actions:
        for action in actions:
            rule.append("actions", action)
    
    rule.insert(ignore_permissions=True)
    return rule


class TestRuleEngine(FrappeTestCase):
    """Test RuleEngine class"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user('Administrator')
    
    def test_engine_initialization(self):
        """Test engine initializes correctly"""
        from flexirule.ruleflow.core.engine import RuleEngine
        
        rule = create_test_rule("Test Engine Init")
        engine = RuleEngine(rule)
        
        self.assertEqual(engine.rule.name, "Test Engine Init")
        self.assertIsInstance(engine.execution_log, list)
    
    def test_engine_validates_disabled_rule(self):
        """Test engine rejects disabled rules"""
        from flexirule.ruleflow.core.engine import RuleEngine
        from flexirule.ruleflow.core.exceptions import RuleDisabledError
        
        rule = create_test_rule("Test Disabled Rule")
        rule.is_active = 0
        rule.save()
        
        engine = RuleEngine(rule)
        doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
        
        with self.assertRaises(RuleDisabledError):
            engine.execute(doc)
    
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()


class TestRuleCoordinator(FrappeTestCase):
    """Test RuleCoordinator class"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user('Administrator')
    
    def test_has_active_rules_caching(self):
        """Test rule existence check uses cache"""
        from flexirule.ruleflow.core.coordinator import RuleCoordinator
        
        RuleCoordinator.clear_cache()
        create_test_rule("Test Cache Rule", doctype="ToDo", event="Before Save")
        
        result1 = RuleCoordinator.has_active_rules("ToDo", "Before Save")
        result2 = RuleCoordinator.has_active_rules("ToDo", "Before Save")
        
        self.assertEqual(result1, result2)
        self.assertTrue(result1)
    
    def test_clear_cache(self):
        """Test cache clearing"""
        from flexirule.ruleflow.core.coordinator import RuleCoordinator
        
        RuleCoordinator.clear_cache("ToDo")
        RuleCoordinator.clear_cache()
    
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()


class TestScoringEngine(FrappeTestCase):
    """Test ScoringEngine for fuzzy matching"""
    
    def test_exact_scorer(self):
        """Test exact match scoring"""
        from flexirule.ruleflow.core.scoring import ScoringEngine
        
        rule = MagicMock()
        rule.options_json = "{}"
        
        engine = ScoringEngine(rule)
        
        self.assertEqual(engine._score_field("Hello", "Hello", "exact"), 1.0)
        self.assertEqual(engine._score_field("Hello", "World", "exact"), 0.0)
    
    def test_fuzzy_scorer(self):
        """Test fuzzy match scoring"""
        from flexirule.ruleflow.core.scoring import ScoringEngine
        
        rule = MagicMock()
        rule.options_json = "{}"
        engine = ScoringEngine(rule)
        
        score = engine._score_field("Hello World", "Hello Wrold", "fuzzy")
        self.assertGreater(score, 0.8)
    
    def test_fingerprint_creation(self):
        """Test document fingerprinting"""
        from flexirule.ruleflow.core.scoring import ScoringEngine
        
        doc = frappe._dict({"name": "Test", "email": "test@example.com"})
        fp = ScoringEngine.create_fingerprint(doc, ["name", "email"])
        
        self.assertIsInstance(fp, str)
        self.assertEqual(len(fp), 32)


class TestNormalizationMethods(FrappeTestCase):
    """Test normalization process methods"""
    
    def test_normalize_field_lowercase(self):
        """Test lowercase transformation"""
        from flexirule.ruleflow.methods.normalization import normalize_field
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "HELLO WORLD"})
        context = {"doc": doc, "vars": {}}
        result = normalize_field(context, source_field="description", transformations=["lowercase"])
        
        self.assertEqual(result, "hello world")
        self.assertEqual(doc.description, "hello world")
    
    def test_normalize_field_multiple(self):
        """Test multiple transformations"""
        from flexirule.ruleflow.methods.normalization import normalize_field
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "  HELLO   WORLD  "})
        context = {"doc": doc, "vars": {}}
        result = normalize_field(context, source_field="description",
                                 transformations=["trim", "lowercase", "remove_extra_spaces"])
        
        self.assertEqual(result, "hello world")
    
    def test_normalize_field_to_context(self):
        """Test normalizing to context"""
        from flexirule.ruleflow.methods.normalization import normalize_field_to_context
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "HELLO"})
        context = {"doc": doc, "vars": {}}
        
        key = normalize_field_to_context(context, source_field="description",
                                         transformations=["lowercase"])
        
        self.assertEqual(doc.description, "HELLO")  # Not modified
        self.assertEqual(context["vars"]["normalized_description"], "hello")
    
    def test_normalize_for_comparison(self):
        """Test read-only normalization"""
        from flexirule.ruleflow.methods.normalization import normalize_for_comparison
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "HELLO"})
        context = {"doc": doc, "vars": {}}
        result = normalize_for_comparison(context, source_field="description",
                                          transformations=["lowercase"])
        
        self.assertEqual(doc.description, "HELLO")
        self.assertEqual(result, "hello")
    
    def test_all_transformations(self):
        """Test all transformation types"""
        from flexirule.ruleflow.methods.normalization import apply_transformations
        
        self.assertEqual(apply_transformations("  hello  ", ["trim"]), "hello")
        self.assertEqual(apply_transformations("HELLO", ["lowercase"]), "hello")
        self.assertEqual(apply_transformations("hello", ["uppercase"]), "HELLO")
        self.assertEqual(apply_transformations("hello world", ["remove_spaces"]), "helloworld")
        self.assertEqual(apply_transformations("hello, world!", ["remove_punctuation"]), "hello world")
        self.assertEqual(apply_transformations("hello   world", ["remove_extra_spaces"]), "hello world")
        self.assertEqual(apply_transformations("hello123", ["remove_numbers"]), "hello")
        self.assertEqual(apply_transformations("Hello World", ["slug"]), "hello-world")
        self.assertEqual(apply_transformations("abc123def456", ["digits_only"]), "123456")
        self.assertEqual(apply_transformations("hello world", ["title_case"]), "Hello World")


class TestValidationMethods(FrappeTestCase):
    """Test validation process methods"""
    
    def test_validate_required_fields_success(self):
        """Test required fields pass when present"""
        from flexirule.ruleflow.methods.validation import validate_required_fields
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
        context = {"doc": doc, "vars": {}}
        result = validate_required_fields(context, fields=["description"])
        self.assertTrue(result)
    
    def test_validate_required_fields_failure(self):
        """Test required fields fail when missing"""
        from flexirule.ruleflow.methods.validation import validate_required_fields
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": ""})
        context = {"doc": doc, "vars": {}}
        
        with self.assertRaises(frappe.ValidationError):
            validate_required_fields(context, fields=["description"])
    
    def test_validate_field_pattern(self):
        """Test pattern validation"""
        from flexirule.ruleflow.methods.validation import validate_field_pattern
        
        doc = frappe._dict({"email": "test@example.com"})
        context = {"doc": doc, "vars": {}}
        result = validate_field_pattern(context, field="email", pattern=r".*@.*\..*")
        self.assertTrue(result)
    
    def test_validate_value_in_range(self):
        """Test numeric range validation"""
        from flexirule.ruleflow.methods.validation import validate_value_in_range
        
        doc = frappe._dict({"amount": 50})
        context = {"doc": doc, "vars": {}}
        result = validate_value_in_range(context, field="amount", min_value=0, max_value=100)
        self.assertTrue(result)


class TestEnrichmentMethods(FrappeTestCase):
    """Test enrichment process methods"""
    
    def test_set_default_value(self):
        """Test setting default value"""
        from flexirule.ruleflow.methods.enrichment import set_default_value
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
        context = {"doc": doc, "vars": {}}
        result = set_default_value(context, field="priority", default_value="Medium")
        
        self.assertEqual(result, "Medium")
        self.assertEqual(doc.priority, "Medium")
    
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
        
        doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
        context = {"doc": doc, "vars": {}}
        result = calculate_field_value(context, target_field="priority", formula='"High"')
        
        self.assertEqual(doc.priority, "High")


class TestDeduplicationMethods(FrappeTestCase):
    """Test deduplication process methods"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user('Administrator')
    
    def test_find_duplicates_by_fields(self):
        """Test exact duplicate detection"""
        from flexirule.ruleflow.methods.deduplication import find_duplicates_by_fields
        
        existing = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Duplicate Test Item"
        }).insert(ignore_permissions=True)
        
        new_doc = frappe.get_doc({"doctype": "ToDo", "description": "Duplicate Test Item"})
        new_doc.name = "temp-new-doc"
        context = {"doc": new_doc, "vars": {}}
        
        duplicates = find_duplicates_by_fields(context, fields=["description"])
        self.assertIn(existing.name, duplicates)
    
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()


class TestPermissions(FrappeTestCase):
    """Test permission checking"""
    
    def test_validate_safe_eval_blocks_dangerous(self):
        """Test dangerous patterns are blocked"""
        from flexirule.ruleflow.core.permissions import validate_safe_eval
        
        dangerous = ["import os", "__import__('os')", "exec('code')", "eval('code')"]
        
        for expr in dangerous:
            with self.assertRaises(frappe.ValidationError):
                validate_safe_eval(expr)
    
    def test_validate_safe_eval_allows_safe(self):
        """Test safe expressions are allowed"""
        from flexirule.ruleflow.core.permissions import validate_safe_eval
        
        safe = ["doc.name == 'test'", "doc.amount > 100", "len(doc.items) > 0"]
        
        for expr in safe:
            validate_safe_eval(expr)


class TestAPI(FrappeTestCase):
    """Test whitelisted API functions"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user('Administrator')
    
    def test_get_doctype_fields(self):
        """Test field retrieval API"""
        from flexirule.ruleflow.api import get_doctype_fields
        
        result = get_doctype_fields("ToDo")
        
        self.assertIn("parent_fields", result)
        self.assertIn("child_tables", result)
    
    def test_get_process_methods(self):
        """Test process method listing"""
        from flexirule.ruleflow.api import get_process_methods
        
        result = get_process_methods()
        self.assertIsInstance(result, list)
    
    def test_clear_cache_api(self):
        """Test cache clearing API"""
        from flexirule.ruleflow.api import clear_cache
        
        result = clear_cache()
        self.assertTrue(result.get("success"))
    
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()


class TestImportExport(FrappeTestCase):
    """Test rule import/export functionality"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user('Administrator')
    
    def test_export_rule(self):
        """Test rule export"""
        from flexirule.ruleflow.utils.import_export import export_rule
        
        rule = create_test_rule("Test Export Rule")
        export_data = export_rule(rule.name)
        
        self.assertIn("flexirule_version", export_data)
        self.assertIn("rule", export_data)
    
    def test_import_rule(self):
        """Test rule import"""
        from flexirule.ruleflow.utils.import_export import export_rule, import_rule
        
        rule = create_test_rule("Test Import Source")
        export_data = export_rule(rule.name)
        export_data["rule"]["rule_name"] = "Test Import Target"
        
        imported_name = import_rule(export_data)
        self.assertIsNotNone(imported_name)
    
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()


if __name__ == '__main__':
    unittest.main()
