/**
 * FlexiRule Utils: Safe Expression Evaluation
 *
 * Wraps frappe.utils.eval for dependency expression evaluation.
 * Provides error handling and boolean coercion for depends_on expressions.
 */

frappe.provide("flexirule.utils");

flexirule.utils = flexirule.utils || {};

/**
 * Safely evaluate a dependency expression string.
 *
 * @param {string} expr - The expression to evaluate (e.g., "doc.mode == 'field'")
 * @param {Object} context - Evaluation context containing { doc, parent, row }
 * @returns {boolean} - Result of expression, false on error
 */
flexirule.utils.safe_eval = function (expr, context) {
	if (!expr || typeof expr !== "string") {
		return true; // No expression means no condition (always visible)
	}

	// Build evaluation context
	const eval_context = {
		doc: context.doc || {},
		parent: context.parent || {},
		row: context.row || {},
		// Add common Frappe globals
		frappe: frappe,
		__: __,
		cint: cint,
		cstr: cstr,
		flt: flt,
		in_list: in_list,
		is_null: is_null,
	};

	try {
		// Use Frappe's eval utility which handles the expression safely
		const result = frappe.utils.eval(expr, eval_context);
		return Boolean(result);
	} catch (e) {
		console.warn(`[FlexiRule] Expression evaluation failed: "${expr}"`, e);
		return false;
	}
};

/**
 * Evaluate multiple expressions and return all results.
 *
 * @param {Object} expressions - Object with expression strings { key: expr_string }
 * @param {Object} context - Evaluation context
 * @returns {Object} - Object with boolean results { key: boolean }
 */
flexirule.utils.eval_all = function (expressions, context) {
	const results = {};
	for (const key in expressions) {
		if (expressions.hasOwnProperty(key)) {
			results[key] = flexirule.utils.safe_eval(expressions[key], context);
		}
	}
	return results;
};
