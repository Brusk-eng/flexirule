# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Scheduler module - Entry points for scheduled rule execution.

Called from hooks.py scheduler_events.
"""

import frappe
from frappe import _


def check_scheduled_rules():
	"""
	Called from scheduler_events['all'] - runs every minute.
	Finds due Rule Schedulers and enqueues them.
	"""
	for scheduler_name in frappe.get_all("Rule Scheduler", filters={"stopped": 0}, pluck="name"):
		try:
			scheduler = frappe.get_doc("Rule Scheduler", scheduler_name)
			scheduler.enqueue()
		except Exception as e:
			frappe.log_error(f"Failed to check scheduler {scheduler_name}", str(e))


def run_scheduled_rule(scheduler_name):
	"""
	Background job entry point.
	Called via frappe.enqueue from RuleScheduler.enqueue().
	"""
	try:
		scheduler = frappe.get_doc("Rule Scheduler", scheduler_name)
		scheduler.execute()
	except Exception as e:
		frappe.log_error(f"Scheduled rule execution failed: {scheduler_name}", str(e))
