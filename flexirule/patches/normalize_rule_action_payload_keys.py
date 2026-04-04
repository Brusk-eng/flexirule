import json

import frappe

ALIAS_TO_CANONICAL = {
	"target_doctype": "reference_doctype",
	"target_docname": "reference_docname",
	"result_handling": "mutation_mode",
}


def _parse_json(value):
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	try:
		return json.loads(value)
	except Exception:
		return {}


def _normalize_config(config: dict) -> dict:
	for legacy, canonical in ALIAS_TO_CANONICAL.items():
		if legacy in config and canonical not in config:
			config[canonical] = config.pop(legacy)
	return config


def execute():
	actions = frappe.get_all(
		"Rule Action",
		fields=[
			"name",
			"action_type",
			"config",
			"rule",
			"reference_doctype",
			"reference_docname",
			"mutation_mode",
		],
		limit=0,
	)

	for action in actions:
		config = _normalize_config(_parse_json(action.get("config")))

		for _, canonical in ALIAS_TO_CANONICAL.items():
			if config.get(canonical):
				current = action.get(canonical)
				if not current:
					frappe.db.set_value(
						"Rule Action",
						action["name"],
						canonical,
						config.get(canonical),
						update_modified=False,
					)

		if action.get("action_type") == "Sub-Rule" and action.get("rule") and not config.get("sub_rule_name"):
			config["sub_rule_name"] = action.get("rule")

		frappe.db.set_value(
			"Rule Action",
			action["name"],
			"config",
			json.dumps(config),
			update_modified=False,
		)

	rules = frappe.get_all(
		"Rule", fields=["name", "visual_data"], filters={"visual_data": ["is", "set"]}, limit=0
	)
	for rule in rules:
		try:
			visual_data = json.loads(rule.get("visual_data") or "[]")
		except Exception:
			continue

		changed = False
		for item in visual_data:
			node_data = item.get("data") if isinstance(item, dict) else None
			if not isinstance(node_data, dict):
				continue
			for legacy, canonical in ALIAS_TO_CANONICAL.items():
				if legacy in node_data and canonical not in node_data:
					node_data[canonical] = node_data.pop(legacy)
					changed = True
			if node_data.get("rule") and not node_data.get("sub_rule_name"):
				node_data["sub_rule_name"] = node_data.get("rule")
				changed = True

		if changed:
			frappe.db.set_value(
				"Rule",
				rule["name"],
				"visual_data",
				json.dumps(visual_data),
				update_modified=False,
			)
