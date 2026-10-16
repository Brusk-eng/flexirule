import assert from "node:assert/strict";
import { stableStringify } from "./stable_serialization.mjs";
import { hasGraphStateChanged, shouldRecordExplicitGraphCommit } from "./graph_dirty_state.mjs";

const baseline = stableStringify([
	{
		id: "action-1",
		type: "process",
		data: { action_type: "Query Records", config: { limit: 20, fields: ["name"] } },
	},
]);

// Equivalent nested objects remain clean when only property insertion order changes.
const sameDataDifferentKeyOrder = [
	{
		data: { config: { fields: ["name"], limit: 20 }, action_type: "Query Records" },
		type: "process",
		id: "action-1",
	},
];
assert.equal(hasGraphStateChanged(baseline, sameDataDifferentKeyOrder), false);

// Real action configuration changes and array-order changes remain dirty.
assert.equal(
	hasGraphStateChanged(baseline, [
		{
			id: "action-1",
			type: "process",
			data: { action_type: "Query Records", config: { fields: ["name"], limit: 50 } },
		},
	]),
	true
);
assert.equal(hasGraphStateChanged(baseline, [{ id: "action-1", type: "process", data: { config: { fields: ["customer", "name"], limit: 20 } } }]), true);
assert.equal(hasGraphStateChanged(null, sameDataDifferentKeyOrder), false);

// Explicit user commits must be observable even before the initial baseline exists.
assert.equal(
	shouldRecordExplicitGraphCommit({
		isReadOnly: false,
		initialState: null,
		currentSnapshot: sameDataDifferentKeyOrder,
	}),
	true
);

// No-op commits stay clean, while read-only rules can never be committed.
assert.equal(
	shouldRecordExplicitGraphCommit({
		isReadOnly: false,
		initialState: baseline,
		currentSnapshot: sameDataDifferentKeyOrder,
	}),
	false
);
assert.equal(
	shouldRecordExplicitGraphCommit({
		isReadOnly: true,
		initialState: baseline,
		currentSnapshot: sameDataDifferentKeyOrder,
	}),
	false
);

console.log("graph dirty-state tests passed");
