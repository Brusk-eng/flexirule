/**
 * Metadata Utilities for FlexiRule
 */

frappe.provide("flexirule.utils");
frappe.provide("flexirule.meta_cache");
frappe.provide("flexirule.processes");

/**
 * Get all fields for a DocType, including standard/system fields and child table fields.
 * Results are cached globally in flexirule.meta_cache.
 *
 * @param {string} doctype - The name of the DocType
 * @param {string} prefix - Optional prefix for field values (e.g. 'doc')
 * @returns {Promise<Array>} - List of field options in {label, value, fieldtype, doctype} format
 */
flexirule.utils.get_doctype_fields = async function (doctype, prefix = "") {
	if (!doctype) return [];

	const cache_key = prefix ? `${doctype}:${prefix}` : doctype;
	if (flexirule.meta_cache[cache_key]) return flexirule.meta_cache[cache_key];

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

				let fieldname = df.fieldname;
				if (table_prefix) {
					fieldname = `${table_prefix}.${df.fieldname}`;
				} else if (prefix) {
					fieldname = `${prefix}.${df.fieldname}`;
				}

				if (seen_fields.has(fieldname)) return;

				let label = "";
				if (parent_table === doctype) {
					label = __(df.label, null, parent_table);
					if (prefix && !table_prefix) {
						label = `${prefix}.${df.fieldname} (${label})`;
					}
				} else {
					// Match FieldSelect format: Label (Table)
					label = __(df.label, null, parent_table) + " (" + __(parent_table) + ")";
					if (table_prefix) {
						label = `${table_prefix}.${df.fieldname} (${__(df.label, null, parent_table)})`;
					}
				}

				options.push({
					label: label,
					value: fieldname,
					fieldname: df.fieldname,
					doctype: parent_table,
					fieldtype: df.fieldtype,
					// Fallback Description: Type -> Options
					description: df.description || (df.options ? `${df.fieldtype} → ${df.options}` : df.fieldtype)
				});
				seen_fields.add(fieldname);
			};

			// 1. Standard Fields (if it's the main doctype and has doc prefix)
			if (prefix === "doc") {
				const stdFields = [
					{ label: "Name", fieldname: "name", fieldtype: "Data" },
					{ label: "Owner", fieldname: "owner", fieldtype: "Data" },
					{ label: "Creation", fieldname: "creation", fieldtype: "Datetime" },
					{ label: "Modified", fieldname: "modified", fieldtype: "Datetime" },
					{ label: "Modified By", fieldname: "modified_by", fieldtype: "Data" },
					{ label: "DocStatus", fieldname: "docstatus", fieldtype: "Int" },
				];
				stdFields.forEach((f) => add_option(f, doctype));
			}

			// 2. Main Table Fields
			const fields = meta.fields || [];
			frappe.utils.sort(fields, "label", "string").forEach((df) => {
				add_option(df, doctype);
			});

			// 3. Child Tables
			const table_fields = fields.filter(
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

			flexirule.meta_cache[cache_key] = options;
			resolve(options);
		});
	});
};

/**
 * Combine cached doctype fields with given context variables.
 *
 * @param {string} doctype - DocType name
 * @param {Array} context_vars - List of variable objects {label, value, type}
 * @param {string} prefix - Optional prefix for DocType fields
 * @returns {Promise<Array>}
 */
flexirule.utils.get_combined_fields = async function (doctype, context_vars = [], prefix = "") {
	const base_fields = doctype ? await flexirule.utils.get_doctype_fields(doctype, prefix) : [];
	const seen_values = new Set(base_fields.map((f) => f.value));

	// Normalize variables and filter out duplicates found in base_fields
	const vars = (context_vars || [])
		.filter((v) => {
			if (seen_values.has(v.value)) return false;
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

/**
 * Lazy load a process adapter JS file.
 *
 * @param {string} process_name - Name of the process
 * @returns {Promise<void>}
 */
flexirule.utils.load_process_adapter = async function (process_name) {
	if (!process_name) return;

	// Already loaded?
	if (flexirule.processes[process_name]) {
		return;
	}

	try {
		const response = await frappe.call({
			method: "flexirule.ruleflow.doctype.process.process.get_script",
			args: { process_name },
		});

		if (response.message && response.message.script) {
			// Use Function constructor for evaluation
			try {
				new Function(response.message.script)();
			} catch (e) {
				console.error(`Failed to evaluate adapter for ${process_name}:`, e);
			}
		}
	} catch (e) {
		console.warn(`Adapter not found or failed to load for ${process_name}`);
	}
};

/**
 * Get a loaded process adapter.
 * 
 * @param {string} process_name 
 * @returns {Object|null}
 */
flexirule.utils.get_process_adapter = function (process_name) {
	return flexirule.processes[process_name] || null;
};

/**
 * Get operations for a process, ensuring the adapter is loaded first.
 *
 * @param {string} process_name - Name of the process
 * @param {Array} db_operations - Optional pre-loaded operations from DB
 * @returns {Promise<Array>}
 */
flexirule.utils.get_process_operations = async function (process_name, db_operations = []) {
	if (!process_name) return [];

	// 1. If we have DB operations, use them (they are authoritative for visible operations)
	if (db_operations && db_operations.length > 0) {
		return db_operations;
	}

	// 2. Otherwise load adapter and get from JS
	await flexirule.utils.load_process_adapter(process_name);
	const adapter = flexirule.utils.get_process_adapter(process_name);
	if (!adapter) return [];

	return adapter.get_visible_operations?.() || adapter.operations || [];
};

/**
 * Get config fields for an operation, ensuring the adapter is loaded.
 */
flexirule.utils.get_operation_config_fields = async function (process_name, operation_name, frm) {
	if (!process_name || !operation_name) return [];

	await flexirule.utils.load_process_adapter(process_name);
	const adapter = flexirule.utils.get_process_adapter(process_name);
	if (!adapter) return [];

	const operation = adapter.get_operation?.(operation_name);
	if (!operation) return [];

	if (typeof operation.get_config_fields === "function") {
		return operation.get_config_fields(frm);
	}

	return [];
};

/**
 * Get field property (type and options) for a field in a DocType.
 * Useful for resolving metadata for mapped fields.
 * 
 * @param {string} doctype 
 * @param {string} fieldname 
 * @returns {Promise<{fieldtype: string, options: string|null}>}
 */
/**
 * Get field options for a specific row in the configuration grid.
 * Used by Autocomplete fields via get_query.
 * 
 * @param {Object} row_doc - The row document from the grid
 * @returns {Array} - List of options {label, value, description}
 */
