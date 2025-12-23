from unittest.mock import patch
import frappe
from frappe.tests.utils import FrappeTestCase
from flexirule.ruleflow.core.registry import sync_process_methods

class TestRegistrySync(FrappeTestCase):
    def test_sync_custom_module(self):
        def mock_get_hooks(hook=None, default=None, app_name=None):
            if hook == "flexirule_allowed_modules":
                return ["flexirule.ruleflow.methods.test_registry"]
            return []

        with patch("frappe.get_hooks", side_effect=mock_get_hooks), \
             patch.object(frappe.db, "commit"), \
             patch("frappe.search.sqlite_search.get_search_classes", return_value=[]):
            sync_process_methods()

            method_path = "flexirule.ruleflow.methods.test_registry.check_registry_sync"
            self.assertTrue(frappe.db.exists("Process Method", method_path))

            doc = frappe.get_doc("Process Method", method_path)
            self.assertEqual(doc.method_name, "Check Registry Sync")
            self.assertEqual(doc.return_type, "Boolean")
            self.assertEqual(doc.is_managed, 1)
            self.assertEqual(doc.category, "Validation")

    def tearDown(self):
        frappe.db.rollback()
    def tearDown(self):
        frappe.db.rollback()
