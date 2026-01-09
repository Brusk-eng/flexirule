import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.engine import (
    MethodExecutionError,
    ReadOnlyDocument,
    RuleEngine,
)


class TestExecutionConstraints(FrappeTestCase):
    def setUp(self):
        frappe.db.rollback()

    def test_pure_method_cannot_mutate(self):
        """Test that a 'Pure' method cannot mutate the document"""
        # 1. Create a Pure Process Method
        vm = frappe.new_doc("Process Method")
        vm.method_name = "Test Pure Mutation"
        vm.method_path = "flexirule.ruleflow.tests.test_constraints.pure_mutation_attempt"
        vm.category = "Custom"
        vm.side_effects = "Pure"
        vm.transactional = 0
        vm.is_enabled = 1
        vm.insert(ignore_permissions=True)

        # 2. Create Rule with this action
        rule = frappe.new_doc("Rule")
        rule.rule_name = "Pure Constraint Rule"
        rule.document_type = "ToDo"
        rule.trigger_event = "Before Save"
        rule.execution_mode = "Synchronous"

        action = frappe.new_doc("Rule Action")
        action.action_id = "act_pure_mut"
        action.action_type = "Process"
        action.action_label = "Try Mutation"
        action.process_method = vm.name
        action.is_enabled = 1

        rule.actions = [action]
        rule.insert(ignore_permissions=True)

        # 3. Execute
        doc = frappe.new_doc("ToDo")
        doc.description = "Original"

        engine = RuleEngine(rule, execution_context={"test_mode": True})

        # Expect failure
        with self.assertRaises(Exception) as cm:
            engine.execute(doc)

        self.assertIn("Cannot mutate document in Pure method", str(cm.exception))

    def test_async_action_constraints(self):
        """Test that Async action cannot have outputs or follow-up steps"""
        # 1. Method
        vm = frappe.new_doc("Process Method")
        vm.method_name = "Test Async Valid"
        vm.method_path = "frappe.utils.now" # Safe
        vm.category = "Custom"
        vm.side_effects = "External Call" # Allowed for async
        vm.transactional = 0
        vm.insert(ignore_permissions=True)

        # 2. Create Rule
        rule = frappe.new_doc("Rule")
        rule.rule_name = "Async Constraint Rule"
        rule.document_type = "ToDo"
        rule.trigger_event = "Before Save"
        rule.execution_mode = "Synchronous"
        rule.insert(ignore_permissions=True) # Insert first to get name if needed

        # 3. Action with Output Mapping (Should Fail)
        action = frappe.new_doc("Rule Action")
        action.action_id = "act_async_out"
        action.action_type = "Process"
        action.action_label = "Async With Output"
        action.process_method = vm.name
        action.is_async = 1
        action.output_mapping = '{"result": "vars.x"}'

        # We need to manually construct the engine or mock the action object
        # because we can't save the Action with invalid state if we add validation to Action.py later.
        # But for now, validation is in Engine.

        rule.actions = [action]
        engine = RuleEngine(rule, execution_context={"test_mode": True})

        with self.assertRaises(MethodExecutionError) as cm:
            engine.execute(frappe.new_doc("ToDo"))

        self.assertIn("cannot have output mapping", str(cm.exception))

    def test_transactional_in_async_rule(self):
        """Test that Transactional method cannot run in Async Rule"""
        # 1. Transactional Method
        vm = frappe.new_doc("Process Method")
        vm.method_name = "Test Transactional"
        vm.method_path = "frappe.utils.now"
        vm.category = "Custom"
        vm.transactional = 1
        vm.insert(ignore_permissions=True)

        # 2. Async Rule
        rule = frappe.new_doc("Rule")
        rule.rule_name = "Async Trans Rule"
        rule.document_type = "ToDo"
        rule.trigger_event = "Before Save"
        rule.execution_mode = "Asynchronous"

        action = frappe.new_doc("Rule Action")
        action.action_id = "act_trans_async"
        action.action_type = "Process"
        action.action_label = "Trans Action"
        action.process_method = vm.name

        rule.actions = [action]
        rule.insert(ignore_permissions=True)

        engine = RuleEngine(rule, execution_context={"test_mode": True})

        with self.assertRaises(MethodExecutionError) as cm:
            engine.execute(frappe.new_doc("ToDo"))

        self.assertIn("cannot be executed in Asynchronous Rule", str(cm.exception))

    def test_async_action_mutation(self):
        """Test that Async action cannot mutate doc even if it tries"""
        # 1. External Call Method (Technically allowed in Async)
        # But we want to ensure it fails if it MUTATES the trigger doc
        vm = frappe.new_doc("Process Method")
        vm.method_name = "Async Mutation Attempt"
        vm.method_path = "flexirule.ruleflow.tests.test_constraints.async_mutation_attempt"
        vm.category = "Custom"
        vm.side_effects = "External Call" # "External Call" makes it eligible for Async check in engine
        vm.transactional = 0
        vm.insert(ignore_permissions=True)

        # 2. Sync Rule (but Action is Async)
        rule = frappe.new_doc("Rule")
        rule.rule_name = "Async Mutation Rule"
        rule.document_type = "ToDo"
        rule.trigger_event = "Before Save"
        rule.execution_mode = "Synchronous"

        action = frappe.new_doc("Rule Action")
        action.action_id = "act_async_mut"
        action.action_type = "Process"
        action.action_label = "Try Async Mutation"
        action.process_method = vm.name
        action.is_async = 1

        rule.actions = [action]
        rule.insert(ignore_permissions=True)

        # 3. Execute
        engine = RuleEngine(rule, execution_context={"test_mode": True})

        # Expect failure from ReadOnlyDocument
        # Although it runs in "External Call" mode, Engine should force ReadOnlyDocument for Async actions
        with self.assertRaises(Exception) as cm:
            engine.execute(frappe.new_doc("ToDo"))

        self.assertIn("Cannot mutate document", str(cm.exception))

    def test_async_secondary_doc_creation(self):
        """
        Test that Async actions CAN create new documents (secondary effect)
        while still being prevented from mutating the trigger doc.
        """
        # 1. Method
        vm = frappe.new_doc("Process Method")
        vm.method_name = "Async Secondary Creation"
        vm.method_path = "flexirule.ruleflow.tests.test_constraints.async_secondary_creation_attempt"
        vm.category = "Custom"
        vm.side_effects = "External Call"
        vm.creates_new_docs = 1
        vm.transactional = 0
        vm.insert(ignore_permissions=True)

        # 2. Rule
        rule = frappe.new_doc("Rule")
        rule.rule_name = "Async Creation Rule"
        rule.document_type = "ToDo"
        rule.trigger_event = "Before Save"
        rule.execution_mode = "Synchronous"

        action = frappe.new_doc("Rule Action")
        action.action_id = "act_create"
        action.action_type = "Process"
        action.action_label = "Async Create"
        action.process_method = vm.name
        action.is_async = 1

        rule.actions = [action]
        rule.insert(ignore_permissions=True)

        # 3. Execute
        engine = RuleEngine(rule, execution_context={"test_mode": True})

        # Should NOT raise exception
        engine.execute(frappe.new_doc("ToDo"))

        # Verify note created
        self.assertTrue(frappe.db.exists("Note", {"title": "Created from Async Rule"}), "Secondary doc should be created")


def pure_mutation_attempt(context, **kwargs):
    doc = context['doc']
    doc.description = "Mutated" # Should fail

def async_mutation_attempt(context, **kwargs):
    doc = context['doc']
    doc.description = "Mutated Async" # Should fail due to ReadOnlyDocument wrapper

def async_secondary_creation_attempt(context, **kwargs):
    import frappe
    # This should be allowed
    note = frappe.get_doc({
        "doctype": "Note",
        "title": "Created from Async Rule",
        "public": 1
    })
    note.insert(ignore_permissions=True)
    return note.name
