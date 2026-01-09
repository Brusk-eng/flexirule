/**
 * FlexiRule Table Schema Utilities
 *
 * Provides schema normalization and variant resolution for FlexiTable columns.
 * Handles dynamic column definitions where the rendered control type
 * depends on row state.
 */

frappe.provide("flexirule");

flexirule.FlexiTableSchema = {};

/**
 * Normalize column definitions to ensure consistent structure.
 *
 * @param {Array} columns - Raw column definitions
 * @returns {Array} - Normalized columns
 */
flexirule.FlexiTableSchema.normalize_columns = function (columns) {
	if (!columns || !Array.isArray(columns)) {
		return [];
	}

	return columns.map((col) => {
		// Ensure basic properties
		const normalized = {
			fieldname: col.fieldname || "",
			label: col.label || frappe.unscrub(col.fieldname || ""),
			fieldtype: col.fieldtype || "Data",
			options: col.options || "",
			width: col.width || null,
			reqd: col.reqd || 0,
			read_only: col.read_only || 0,
			hidden: col.hidden || 0,
			default: col.default,
			depends_on: col.depends_on || "",
			mandatory_depends_on: col.mandatory_depends_on || "",
			read_only_depends_on: col.read_only_depends_on || "",
		};

		// Handle variant columns
		if (col.variants && Array.isArray(col.variants)) {
			normalized.variants = col.variants.map((v) => ({
				fieldtype: v.fieldtype || "Data",
				options: v.options || "",
				condition: v.condition || "", // Expression to determine when this variant applies
				get_options: v.get_options || null, // Function to get dynamic options
			}));
		}

		// Custom render function (for widgets)
		if (col.render) {
			normalized.render = col.render;
		}

		// Change handler
		if (col.onchange) {
			normalized.onchange = col.onchange;
		}

		return normalized;
	});
};

/**
 * Resolve which variant to use for a column based on row state.
 *
 * @param {Object} column - Normalized column definition
 * @param {Object} row - Row data object
 * @param {Object} context - Evaluation context { doc, parent }
 * @returns {Object} - Resolved df (DocField-like object)
 */
flexirule.FlexiTableSchema.resolve_variant = function (column, row, context = {}) {
	// Build base df from column
	const base_df = {
		fieldname: column.fieldname,
		label: column.label,
		fieldtype: column.fieldtype,
		options: column.options,
		reqd: column.reqd,
		read_only: column.read_only,
		hidden: column.hidden,
		default: column.default,
		depends_on: column.depends_on,
		mandatory_depends_on: column.mandatory_depends_on,
		read_only_depends_on: column.read_only_depends_on,
	};

	// If no variants, return base df
	if (!column.variants || column.variants.length === 0) {
		return base_df;
	}

	// Evaluate each variant's condition
	const eval_context = {
		doc: context.doc || {},
		parent: context.parent || {},
		row: row || {},
	};

	for (const variant of column.variants) {
		if (variant.condition) {
			const matches = flexirule.utils.safe_eval(variant.condition, eval_context);
			if (matches) {
				// Apply variant overrides
				const resolved_df = Object.assign({}, base_df, {
					fieldtype: variant.fieldtype,
					options: variant.options,
				});

				// Handle dynamic options
				if (variant.get_options && typeof variant.get_options === "function") {
					resolved_df.options = variant.get_options(row, context);
				}

				return resolved_df;
			}
		}
	}

	// No variant matched, return base
	return base_df;
};

/**
 * Get default row values from column definitions.
 *
 * @param {Array} columns - Normalized columns
 * @returns {Object} - Default row object
 */
flexirule.FlexiTableSchema.get_column_defaults = function (columns) {
	const defaults = {};

	columns.forEach((col) => {
		if (col.default !== undefined) {
			defaults[col.fieldname] = col.default;
		} else {
			// Type-specific defaults
			switch (col.fieldtype) {
				case "Check":
					defaults[col.fieldname] = 0;
					break;
				case "Int":
				case "Float":
				case "Currency":
				case "Percent":
					defaults[col.fieldname] = 0;
					break;
				default:
					defaults[col.fieldname] = "";
			}
		}
	});

	return defaults;
};

/**
 * Check if a column has variant definitions.
 *
 * @param {Object} column - Column definition
 * @returns {boolean}
 */
flexirule.FlexiTableSchema.has_variants = function (column) {
	return column.variants && column.variants.length > 0;
};

/**
 * Create a variant key for comparison (to detect variant changes).
 *
 * @param {Object} df - Resolved DocField
 * @returns {string} - Key representing the variant
 */
flexirule.FlexiTableSchema.get_variant_key = function (df) {
	return `${df.fieldtype}:${df.options || ""}`;
};
