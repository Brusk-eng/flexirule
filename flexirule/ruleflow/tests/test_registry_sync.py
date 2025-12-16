import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from flexirule.ruleflow.core.registry import sync_process_methods

class TestRegistrySync(FrappeTestCase):
    def test_sync_custom_module(self):
        # 1. Mock hooks to include our test module
        # Note: We need to patch where it is USED or the original function
        # Since sync_process_methods imports frappe, and calls frappe.get_hooks
        # matching frappe.get_hooks works.
        
        original_get_hooks = frappe.get_hooks
        
        def mock_get_hooks(hook=None, default=None, app_name=None):
            if hook == "flexirule_allowed_modules":
                return ["flexirule.ruleflow.methods.test_registry"]
            if hook == "global_search_doctypes":
                return []
            return original_get_hooks(hook, default, app_name)
            
        with patch("frappe.get_hooks", side_effect=mock_get_hooks), \
             patch("frappe.search.sqlite_search.get_search_classes", return_value=[]), \
             patch("frappe.db.commit"):
            # 2. Run Sync
            sync_process_methods()
            
            # 3. Check Result
            method_path = "flexirule.ruleflow.methods.test_registry.check_registry_sync"
            self.assertTrue(frappe.db.exists("Process Method", method_path), "Process Method should be created by sync")
            
            doc = frappe.get_doc("Process Method", method_path)
            self.assertEqual(doc.method_name, "Check Registry Sync")
            self.assertEqual(doc.return_type, "Boolean")
            self.assertEqual(doc.is_managed, 1)
            self.assertEqual(doc.category, "Validation")

    def tearDown(self):
        frappe.db.rollback()
