/**
 * Shared regression guard patterns and matchers for Cypress UI suites and unit tests.
 */
export const REGRESSION_CONSOLE_PATTERN =
	/could not find grid field|grid field.*not found|cannot set property hasResolvedOutputSchema/i;

/**
 * Checks if a console message matches known Rule Builder console regressions.
 *
 * @param {string} message
 * @returns {boolean}
 */
export function isConsoleRegressionMessage(message) {
	if (!message || typeof message !== "string") return false;
	return REGRESSION_CONSOLE_PATTERN.test(message);
}

/**
 * Predicate for transient Frappe desk workspace router race condition during programmatic route changes.
 * Only returns true for the specific Frappe Desk router race signature.
 *
 * @param {Error|object} err
 * @returns {boolean}
 */
export function isKnownRouterRaceException(err) {
	if (!err) return false;
	const msg = String(err?.message || "");
	const stack = String(err?.stack || "");
	const full = `${msg}\n${stack}`;

	const hasTypeError = msg.includes("Cannot read properties of undefined (reading 'name')");
	const hasRouterContext =
		full.includes("show_page") ||
		full.includes("set_route") ||
		full.includes("frappe.views.page");

	return hasTypeError && hasRouterContext;
}
