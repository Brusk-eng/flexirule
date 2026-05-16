import json

import frappe


def execute():
	"""Migrate legacy 'Set Value' actions to 'Assignment' batch actions."""

	actions = frappe.get_all(
		"Rule Action",
		filters={"action_type": "Set Value"},
		fields=["name", "operation", "target_field", "value_template", "config"],
	)

	for action in actions:
		target_field = action.target_field or ""
		operation = action.operation or "Current Document"

		# Determine target prefix
		target = target_field
		if not target.startswith("doc.") and not target.startswith("vars."):
			if operation == "Context Variable":
				target = f"vars.{target_field}"
			else:
				target = f"doc.{target_field}"

		# Parse existing config to extract UI state
		existing_config = {}
		if action.config:
			try:
				existing_config = json.loads(action.config)
			except Exception:
				pass

		text_generator_ui = existing_config.get(
			"text_generator_ui",
			{"version": 2, "segments": [{"type": "text", "content": action.value_template or ""}]},
		)

		assignment_config = [
			{
				"target": target,
				"operator": "set",
				"value_template": action.value_template,
				"value_template_ui": text_generator_ui,
			}
		]

		# Update the action record via SQL to avoid validation loops
		frappe.db.sql(
			"""
			UPDATE `tabRule Action`
			SET
				action_type = 'Assignment',
				config = %s,
				operation = NULL,
				target_field = NULL,
				value_template = NULL
			WHERE name = %s
		""",
			(json.dumps(assignment_config), action.name),
		)

	# Update visual_data in Rule to change node type
	rules = frappe.db.sql(
		"""
		SELECT name, visual_data
		FROM `tabRule`
		WHERE visual_data LIKE '%"action_type": "Set Value"%'
		   OR visual_data LIKE '%"Set Value"%'
	""",
		as_dict=True,
	)

	for rule in rules:
		if not rule.visual_data:
			continue
		try:
			data = json.loads(rule.visual_data)
			changed = False
			for node in data.get("nodes", []):
				if node.get("data", {}).get("action_type") == "Set Value":
					node["data"]["action_type"] = "Assignment"
					# Keep the label if it was customized, or reset
					if node["data"].get("label") == "Set Value":
						node["data"]["label"] = "Assignment"
					changed = True
			if changed:
				frappe.db.set_value("Rule", rule.name, "visual_data", json.dumps(data), update_modified=False)
		except Exception:
			pass
