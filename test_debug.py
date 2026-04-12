import frappe

from flexirule.ruleflow.tests.test_advanced_rule_flows import TestAdvancedRuleFlows

frappe.init(site="insight.test")
frappe.connect()

test_obj = TestAdvancedRuleFlows()
frappe.set_user("Administrator")
nested_rule = test_obj._create_nested_callable_rule()
print("nested rule name:", nested_rule.name)
print("is_active before refetch:", nested_rule.is_active)
print("is_active refetched:", frappe.get_value("Rule", nested_rule.name, "is_active"))
