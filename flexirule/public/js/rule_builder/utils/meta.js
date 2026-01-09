/**
 * Metadata Utilities for FlexiRule
 */

frappe.provide("flexirule.utils");
frappe.provide("flexirule.meta_cache");

/**
 * Get all fields for a DocType, including standard/system fields and child table fields.
 * Results are cached globally in flexirule.meta_cache.
 *
 * @param {string} doctype - The name of the DocType
 * @returns {Promise<Array>} - List of field options in {label, value, fieldtype, doctype} format
 */
flexirule.utils.get_doctype_fields = async function (doctype) {
	if (!doctype) return [];
	if (!flexirule.meta_cache) flexirule.meta_cache = {};
	if (flexirule.meta_cache[doctype]) return flexirule.meta_cache[doctype];

	return new Promise((resolve) => {
		frappe.model.with_doctype(doctype, async () => {
			const meta = frappe.get_meta(doctype);
			const options = [];
			const seen_fields = new Set();

			if (!meta) {
				resolve([]);
				return;
			}

			/**
			 * Internal helper to add a field option with FieldSelect-style labels.
			 */
			const add_option = (df, parent_table, table_prefix = "") => {
				if (frappe.model.no_value_type.includes(df.fieldtype)) return;
				if (df.is_virtual) return;

				const fieldname = table_prefix ? `${table_prefix}.${df.fieldname}` : df.fieldname;
				if (seen_fields.has(fieldname)) return;

				let label = "";
				if (parent_table === doctype) {
					label = __(df.label, null, parent_table);
				} else {
					// Match FieldSelect format: Label (Table)
					label = __(df.label, null, parent_table) + " (" + __(parent_table) + ")";
				}

				options.push({
					label: label,
					value: fieldname,
					fieldname: df.fieldname,
					doctype: parent_table,
					fieldtype: df.fieldtype,
				});
				seen_fields.add(fieldname);
			};

			// 1. Main Table (Standard + Fields)
			const std_filters = frappe.model.std_fields
				.filter((d) => !frappe.model.no_value_type.includes(d.fieldtype))
				.map((d) => ({ ...d, parent: doctype }));

			const main_fields = std_filters.concat(meta.fields || []);
			// Sort main fields by label like FieldSelect
			frappe.utils.sort(main_fields, "label", "string").forEach((df) => {
				add_option(df, doctype);
			});

			// 2. Child Tables
			const table_fields = (meta.fields || []).filter(
				(f) => (f.fieldtype === "Table" || f.fieldtype === "Table MultiSelect") && f.options
			);

			for (const tf of table_fields) {
				await new Promise((res) => {
					frappe.model.with_doctype(tf.options, () => {
						const child_meta = frappe.get_meta(tf.options);
						if (child_meta) {
							const child_fields = child_meta.fields || [];
							frappe.utils.sort(child_fields, "label", "string").forEach((cf) => {
								add_option(cf, tf.options, tf.fieldname);
							});
						}
						res();
					});
				});
			}

			flexirule.meta_cache[doctype] = options;
			resolve(options);
		});
	});
};

/**
 * Combine cached doctype fields with given context variables.
 *
 * @param {string} doctype - DocType name
 * @param {Array} context_vars - List of variable objects {label, value, type}
 * @returns {Promise<Array>}
 */
flexirule.utils.get_combined_fields = async function (doctype, context_vars = []) {
	const base_fields = doctype ? await flexirule.utils.get_doctype_fields(doctype) : [];
	const seen_values = new Set(base_fields.map((f) => f.value));

	// Normalize variables and filter out duplicates found in base_fields
	const vars = (context_vars || [])
		.filter((v) => {
			if (seen_values.has(v.value)) return false;

			// Handle "doc.fieldname" duplicates if "fieldname" is already in base_fields
			if (v.value && v.value.startsWith("doc.")) {
				const raw_field = v.value.replace("doc.", "");
				if (seen_values.has(raw_field)) return false;
			}

			return true;
		})
		.map((v) => ({
			label: `${__(v.label)} (${__("Variable")})`,
			value: v.value,
			fieldtype: v.type || "Data",
			is_variable: true,
		}));

	// Clone base to avoid mutating cache
	const combined = [...base_fields];

	// Append variables directly without separator
	vars.forEach((v) => combined.push(v));

	return combined;
};
