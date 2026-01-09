/**
 * Parse config_schema and generate Frappe-compliant field definitions
 */
export function parseSchemaToFields(schema, documentType) {
	if (!schema) return [];

	// Support Frappe-style field definitions
	if (schema.fields && Array.isArray(schema.fields)) {
		return schema.fields;
	}

	if (!schema.properties) return [];

	const fields = [];
	const properties = schema.properties;
	const required = schema.required || [];

	Object.entries(properties).forEach(([fieldname, prop]) => {
		const field = {
			fieldname: fieldname,
			label: prop.title || fieldname,
			description: prop.description,
			reqd: required.includes(fieldname) ? 1 : 0,
			default: prop.default,
		};

		// Handle custom x-fieldtype extensions
		if (prop["x-fieldtype"]) {
			switch (prop["x-fieldtype"]) {
				case "DocField":
					field.fieldtype = "Autocomplete";
					field.options = () => getDocTypeFields(documentType);
					break;
				case "Code":
					field.fieldtype = "Code";
					field.options = "Python";
					break;
				case "Expression":
					field.fieldtype = "Small Text";
					field.description = (field.description || "") + " (Python expression)";
					break;
				default:
					field.fieldtype = "Data";
			}
		}
		// Handle standard JSON Schema types
		else if (prop.enum) {
			field.fieldtype = "Select";
			field.options = prop.enum.join("\n");
		} else if (prop.type === "boolean") {
			field.fieldtype = "Check";
		} else if (prop.type === "number" || prop.type === "integer") {
			field.fieldtype = prop.type === "integer" ? "Int" : "Float";
		} else {
			field.fieldtype = "Data";
		}

		// Handle dependencies
		if (prop["x-depends-on"]) {
			field.depends_on = `eval:doc.${prop["x-depends-on"]}`;
		}

		fields.push(field);
	});

	return fields;
}

function getDocTypeFields(doctype) {
	if (!doctype) return [];

	try {
		const meta = frappe.get_meta(doctype);
		if (!meta) return [];

		return meta.fields
			.filter((f) => !frappe.model.no_value_type.includes(f.fieldtype))
			.map((f) => ({
				label: `${f.label} (${f.fieldtype})`,
				value: f.fieldname,
				description: f.fieldtype,
			}));
	} catch (e) {
		console.error("Error getting doctype fields:", e);
		return [];
	}
}

export function validateConfigAgainstSchema(config, schema) {
	if (!schema || !schema.required) return { valid: true };

	const errors = [];
	const configObj = typeof config === "string" ? JSON.parse(config) : config;

	schema.required.forEach((fieldname) => {
		if (!configObj[fieldname]) {
			const prop = schema.properties[fieldname];
			errors.push(`${prop.title || fieldname} is required`);
		}
	});

	return {
		valid: errors.length === 0,
		errors: errors,
	};
}
