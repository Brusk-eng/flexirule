import assert from "node:assert/strict";
import { test } from "node:test";
import { createPinia, setActivePinia } from "pinia";

global.__ = (s) => s;
global.flexirule = {
	utils: {
		safe_json_parse: (val, defaultVal = null) => {
			if (!val) return defaultVal;
			if (typeof val === "object") return val;
			try {
				return JSON.parse(val);
			} catch {
				return defaultVal;
			}
		},
		to_title_case: (str) => str,
	},
};

const { useGraphStore } = await import(
	"../../../../../flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js"
);

test("get_visual_data_payload excludes full node.data and action type/label for action nodes", () => {
	setActivePinia(createPinia());
	const store = useGraphStore();

	store.nodes = [
		{
			id: "node-1",
			type: "process",
			label: "Action Label",
			position: { x: 100, y: 200 },
			direction: "LR",
			data: {
				action_id: "node-1",
				action_type: "Query Records",
				config: { secret: "do_not_duplicate" },
			},
		},
		{
			id: "visual-note-1",
			type: "note",
			label: "Sticky Note",
			position: { x: 300, y: 400 },
			is_visual_only: true,
			data: { text: "Visual note text" },
		},
	];

	store.edges = [
		{
			id: "e-node-1",
			source: "node-1",
			target: "visual-note-1",
			sourceHandle: "default",
			targetHandle: null,
		},
	];

	const payload = store.get_visual_data_payload("LR");

	const actionPayloadNode = payload.find((item) => item.id === "node-1");
	assert.ok(actionPayloadNode, "action node present in payload");
	assert.equal(actionPayloadNode.data, undefined, "action data must not be duplicated");
	assert.equal(actionPayloadNode.type, undefined, "type is omitted for standard action node");
	assert.equal(actionPayloadNode.label, undefined, "label is omitted for standard action node");
	assert.deepEqual(actionPayloadNode.position, { x: 100, y: 200 });

	const visualOnlyNode = payload.find((item) => item.id === "visual-note-1");
	assert.ok(visualOnlyNode, "visual-only node present in payload");
	assert.equal(visualOnlyNode.is_visual_only, true);
	assert.equal(visualOnlyNode.type, "note");
	assert.equal(visualOnlyNode.label, "Sticky Note");
});

test("merge_visual_layout updates positions without overwriting action data or resurrecting stale orphans", () => {
	setActivePinia(createPinia());
	const store = useGraphStore();

	// Action nodes derived from doc.actions
	store.nodes = [
		{
			id: "action-1",
			type: "process",
			label: "Authoritative Action",
			position: { x: 0, y: 0 },
			data: {
				action_id: "action-1",
				action_type: "Assignment",
				config: { target: "new_value" },
			},
		},
	];
	store.edges = [];

	// Legacy or stale visual_data containing action data and a deleted orphan action
	const visualData = [
		{
			id: "action-1",
			position: { x: 150, y: 250 },
			type: "process",
			label: "Old Stale Label",
			data: {
				action_type: "Assignment",
				config: { target: "OLD_STALE_VALUE" },
			},
		},
		{
			id: "deleted-orphan-action",
			position: { x: 500, y: 500 },
			type: "process",
			label: "Deleted Action",
			data: {
				action_type: "Query Records",
				config: { query: "secret" },
			},
		},
		{
			id: "legitimate-visual-only",
			position: { x: 600, y: 600 },
			type: "annotation",
			label: "Annotation",
			is_visual_only: true,
		},
	];

	store.merge_visual_layout(visualData);

	// 1. Position updated for action-1
	const actionNode = store.nodes.find((n) => n.id === "action-1");
	assert.ok(actionNode);
	assert.deepEqual(actionNode.position, { x: 150, y: 250 });
	// Action config and label MUST remain unchanged from doc.actions
	assert.equal(actionNode.data.config.target, "new_value");
	assert.equal(actionNode.label, "Authoritative Action");

	// 2. Deleted orphan action node MUST NOT be resurrected
	const orphanNode = store.nodes.find((n) => n.id === "deleted-orphan-action");
	assert.equal(orphanNode, undefined, "stale orphan action record must not be restored");

	// 3. Legitimate visual-only node IS restored
	const visualOnlyNode = store.nodes.find((n) => n.id === "legitimate-visual-only");
	assert.ok(visualOnlyNode, "explicit visual-only node is preserved");
});
