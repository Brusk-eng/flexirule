import assert from "node:assert/strict";
import { test } from "node:test";
import {
	isConsoleRegressionMessage,
	isKnownRouterRaceException,
	REGRESSION_CONSOLE_PATTERN,
} from "../../../../../cypress/reboot/support/regression_guards.mjs";

test("isConsoleRegressionMessage detects known grid and schema regressions", () => {
	assert.equal(
		isConsoleRegressionMessage("Error: Could not find grid field 'target_field'"),
		true
	);
	assert.equal(
		isConsoleRegressionMessage(
			"TypeError: Cannot set property hasResolvedOutputSchema of undefined"
		),
		true
	);
	assert.equal(isConsoleRegressionMessage("grid field 'options' not found in row"), true);
});

test("isConsoleRegressionMessage rejects unrelated console messages", () => {
	assert.equal(isConsoleRegressionMessage("Server responded with 404"), false);
	assert.equal(isConsoleRegressionMessage("Navigated to /app/rule"), false);
	assert.equal(isConsoleRegressionMessage("show_page event fired"), false);
	assert.equal(isConsoleRegressionMessage(null), false);
	assert.equal(isConsoleRegressionMessage(undefined), false);
});

test("isKnownRouterRaceException approves specific Frappe router race signature", () => {
	const errWithStack = {
		message: "Uncaught TypeError: Cannot read properties of undefined (reading 'name')",
		stack: "at show_page (desk.js:123)\nat frappe.views.page.show_page (page.js:45)",
	};
	assert.equal(isKnownRouterRaceException(errWithStack), true);

	const errInMsg = {
		message:
			"Cannot read properties of undefined (reading 'name') at frappe.views.page.show_page",
	};
	assert.equal(isKnownRouterRaceException(errInMsg), true);
});

test("isKnownRouterRaceException rejects unrelated exceptions", () => {
	// Mentions show_page but NOT the specific TypeError
	const unrelatedShowPage = {
		message: "Uncaught Error: failed to render page in show_page",
		stack: "at show_page (desk.js:10)",
	};
	assert.equal(isKnownRouterRaceException(unrelatedShowPage), false);

	// Mentions 'reading name' but NOT router context
	const unrelatedTypeError = {
		message: "Cannot read properties of undefined (reading 'name')",
		stack: "at renderUserAvatar (user.js:50)",
	};
	assert.equal(isKnownRouterRaceException(unrelatedTypeError), false);

	assert.equal(isKnownRouterRaceException(null), false);
	assert.equal(isKnownRouterRaceException(new Error("random error")), false);
});
