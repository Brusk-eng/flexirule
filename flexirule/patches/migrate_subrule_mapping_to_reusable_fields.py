import json

import frappe


def _parse_json(value):
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	try:
		return json.loads(value)
	except Exception:
		return {}


def execute():
	actions = frappe.get_all(
		"Rule Action",
		filters={"action_type": "Sub-Rule"},
		fields=["name", "config", "rule", "return_variable"],
		limit=0,
	)

	for action in actions:
		config = _parse_json(action.get("config"))

		input_mapping_json = config.pop("input_mapping_json", None)
		if input_mapping_json and not config.get("input_mapping"):
			config["input_mapping"] = input_mapping_json

		output_namespace = (config.pop("output_namespace", None) or "").strip()
		if output_namespace and not config.get("output_mapping"):
			config["output_mapping"] = {"__self__": f"vars.{output_namespace}"}

		if action.get("rule") and not config.get("sub_rule_name"):
			config["sub_rule_name"] = action.get("rule")

		if action.get("return_variable") and not config.get("output_mapping"):
			config["output_mapping"] = {"__self__": f"vars.{action.get('return_variable')}"}

		frappe.db.set_value(
			"Rule Action",
			action["name"],
			"config",
			json.dumps(config),
			update_modified=False,
		)
