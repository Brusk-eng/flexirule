/**
 * FlexiRule Rule Builder Store — Backward-Compatible Facade
 *
 * This file now delegates to the domain stores. All existing components
 * that import `useStore` from "./store" continue to work unchanged.
 *
 * Architecture mirrors Frappe builders (form_builder, workflow_builder):
 *   - Single defineStore for component interface
 *   - Delegates to domain stores for actual logic
 *   - New code should import directly from stores/
 *
 * Domain stores:
 *   useRuleStore    — Rule document lifecycle, fetch/save, processes
 *   useGraphStore   — Nodes, edges, topology, operations
 *   useMetaStore    — DocType metadata cache
 *   useHistoryStore — Undo/redo
 *   useUIStore      — Selection, modals, test visualization
 */
import { defineStore } from "pinia";
import { computed } from "vue";
import { normalizeActionType } from "../core/contracts";

import { useRuleStore } from "./stores/useRuleStore";
import { useGraphStore } from "./stores/useGraphStore";
import { useMetaStore } from "./stores/useMetaStore";
import { useUIStore } from "./stores/useUIStore";
import { useHistoryStore } from "./stores/useHistoryStore";

export const useStore = defineStore("rule-builder-store", () => {
	// ── Get domain store references ──
	// These are accessed lazily inside returned functions to avoid
	// Pinia initialization order issues.

	function _rule() {
		return useRuleStore();
	}
	function _graph() {
		return useGraphStore();
	}
	function _meta() {
		return useMetaStore();
	}
	function _ui() {
		return useUIStore();
	}
	function _history() {
		return useHistoryStore();
	}

	// ══════════════════════════════════════════════════
	// Expose all properties/methods as a unified interface.
	// Existing components reference store.nodes, store.selected_id, etc.
	// ══════════════════════════════════════════════════

	// --- State (delegated refs) ---
	// Rule
	const rule_name = computed({
		get: () => _rule().rule_name,
		set: (v) => (_rule().rule_name = v),
	});
	const rule_doc = computed({
		get: () => _rule().rule_doc,
		set: (v) => (_rule().rule_doc = v),
	});
	const is_dirty = computed({
		get: () => _rule().is_dirty,
		set: (v) => (_rule().is_dirty = v),
	});
	const settings = computed(() => _rule().settings);

	// Graph
	const nodes = computed({
		get: () => _graph().nodes,
		set: (v) => (_graph().nodes = v),
	});
	const edges = computed({
		get: () => _graph().edges,
		set: (v) => (_graph().edges = v),
	});

	// UI
	const selected_id = computed({
		get: () => _ui().selected_id,
		set: (v) => (_ui().selected_id = v),
	});
	const show_sidebar = computed({
		get: () => _ui().show_sidebar,
		set: (v) => (_ui().show_sidebar = v),
	});
	const show_config_modal = computed({
		get: () => _ui().show_config_modal,
		set: (v) => (_ui().show_config_modal = v),
	});
	const config_modal_mode = computed({
		get: () => _ui().config_modal_mode,
		set: (v) => (_ui().config_modal_mode = v),
	});
	const use_modern_layout = computed({
		get: () => _ui().use_modern_layout,
		set: (v) => (_ui().use_modern_layout = v),
	});
	const test_execution_path = computed({
		get: () => _ui().test_execution_path,
		set: (v) => (_ui().test_execution_path = v),
	});
	const test_context = computed({
		get: () => _ui().test_context,
		set: (v) => (_ui().test_context = v),
	});
	const local_clipboard = computed({
		get: () => _ui().local_clipboard,
		set: (v) => (_ui().local_clipboard = v),
	});

	// Processes & Rules
	const processes = computed({
		get: () => _rule().processes,
		set: (v) => (_rule().processes = v),
	});
	const available_rules = computed({
		get: () => _rule().available_rules,
		set: (v) => (_rule().available_rules = v),
	});

	// --- Computed (read-only) ---
	const is_read_only = computed(() => _rule().is_read_only);
	const effectiveDisabledIds = computed(() => _graph().effectiveDisabledIds);
	const trigger_event_options = computed(() => _rule().trigger_event_options);
	const doc_fields = computed(() => _rule().doc_fields);
	const doc_meta = computed(() => _meta().doc_meta);
	const raw_meta = computed(() => _rule().raw_meta);
	const meta_loading = computed(() => _meta().meta_loading);

	// --- Delegated actions ---
	async function fetch() {
		return _rule().fetch();
	}

	async function fetch_metadata(doctype) {
		return _meta().fetch_metadata(doctype);
	}

	function get_fields_for_doctype(doctype, alias) {
		return _meta().get_fields_for_doctype(doctype, alias);
	}

	async function save_changes() {
		return _rule().save_changes();
	}

	function mark_dirty() {
		_rule().mark_dirty();
	}

	function mark_position_change() {
		_rule().mark_position_change();
	}

	function clear_dirty() {
		_rule().clear_dirty();
	}

	function delete_node(nodeId) {
		const deleted = _graph().delete_node(nodeId, _rule().is_read_only);
		if (deleted) {
			if (_ui().selected_id === nodeId) _ui().selected_id = null;
			mark_dirty();
		}
	}

	function delete_edge(edgeId) {
		const deleted = _graph().delete_edge(edgeId, _rule().is_read_only);
		if (deleted) mark_dirty();
	}

	function touch_node(nodeId) {
		_graph().touch_node(nodeId);
	}

	function toggle_node_enabled(nodeId) {
		_graph().toggle_node_enabled(nodeId);
		mark_dirty();
	}

	function insert_node_on_edge(edgeId, nodeType) {
		const id = _graph().insert_node_on_edge(edgeId, nodeType);
		if (id) mark_dirty();
		return id;
	}

	/**
	 * Live-updates an edge on the canvas when the user changes a next-step via
	 * the ActionSettings autocomplete (without going through insert_node_on_edge).
	 *
	 * @param {string} sourceId    - ID of the source node
	 * @param {string} handle      - "true" | "false" | "default"
	 * @param {string} newTargetId - ID of the new target node
	 */
	function reconnect_node_edge(sourceId, handle, newTargetId) {
		const graph = _graph();
		const edges = graph.edges;

		// Remove the existing edge on this handle
		const existingIdx = edges.value.findIndex(
			(e) => e.source === sourceId && e.sourceHandle === handle
		);
		if (existingIdx !== -1) {
			edges.value.splice(existingIdx, 1);
		}

		// Add new edge if a target was selected
		if (newTargetId) {
			edges.value.push({
				id: `e-${sourceId}-${newTargetId}-${handle}`,
				source: sourceId,
				target: newTargetId,
				sourceHandle: handle,
				type: "add",
			});
		}

		mark_dirty();
	}

	function paste_on_edge(edgeId, pastedNodes, pastedEdges) {
		const id = _graph().paste_on_edge(edgeId, pastedNodes, pastedEdges);
		if (id) mark_dirty();
		return id;
	}

	function get_default_node_data(type, label) {
		return _graph().get_default_node_data(type, label);
	}

	function getEffectivelyDisabledIds() {
		return _graph().getEffectivelyDisabledIds();
	}

	function undo() {
		_rule().undo();
	}

	function redo() {
		_rule().redo();
	}

	function can_undo() {
		return _rule().can_undo();
	}

	function can_redo() {
		return _rule().can_redo();
	}

	function commit_history() {
		_history().commit(() => _graph().getGraphSnapshot());
	}

	async function getAvailableVariables(upToNodeId) {
		return _graph().getAvailableVariables(upToNodeId, _rule().rule_doc);
	}

	async function activate_rule() {
		return _rule().activate_rule();
	}

	async function deactivate_rule() {
		return _rule().deactivate_rule();
	}

	async function simulate_rule(docname) {
		return _rule().simulate_rule(docname);
	}

	async function preview_execution(docname) {
		return _rule().preview_execution(docname);
	}

	async function fetch_processes() {
		return _rule().fetch_processes();
	}

	async function get_process_operations(process_name) {
		return _rule().get_process_operations(process_name);
	}

	async function get_operation_config_fields(process_name, operation_name, frm) {
		return _rule().get_operation_config_fields(process_name, operation_name, frm);
	}

	async function fetch_available_rules() {
		return _rule().fetch_available_rules();
	}

	function open_config(nodeId) {
		const configMode = settings.value?.action_config_mode || "Sidebar";
		selected_id.value = nodeId;
		if (configMode === "Dialog") {
			show_config_modal.value = true;
			config_modal_mode.value = "setup";
		} else {
			show_sidebar.value = true;
		}
	}

	function set_test_result(path, context) {
		_ui().set_test_result(path, context);
	}

	function clear_test_result() {
		_ui().clear_test_result();
	}

	function next_config_node() {
		_ui().navigate_node(_graph().nodes, 1);
	}

	function prev_config_node() {
		_ui().navigate_node(_graph().nodes, -1);
	}
	function pasteNodes(nodes, edges, position) {
		const pasted = _graph().pasteNodes(nodes, edges, position);
		if (pasted.length) mark_dirty();
		return pasted;
	}

	return {
		// State
		rule_name,
		rule_doc,
		nodes,
		edges,
		selected_id,
		show_sidebar,
		show_config_modal,
		config_modal_mode,
		use_modern_layout,
		processes,
		available_rules,
		is_dirty,
		settings,

		// Computed
		effectiveDisabledIds,
		trigger_event_options,
		doc_fields,
		doc_meta,
		raw_meta,
		meta_loading,
		test_execution_path,
		test_context,
		is_read_only,

		// Lifecycle
		fetch,
		fetch_metadata,
		get_fields_for_doctype,
		save_changes,

		// Dirty tracking
		mark_dirty,
		mark_position_change,
		clear_dirty,

		// Node/Edge operations
		delete_node,
		delete_edge,
		touch_node,
		toggle_node_enabled,
		insert_node_on_edge,
		reconnect_node_edge,
		paste_on_edge,
		get_default_node_data,
		getEffectivelyDisabledIds,

		// Undo/Redo
		undo,
		redo,
		can_undo,
		can_redo,
		commit_history,

		// Variables
		getAvailableVariables,

		// Rule lifecycle
		activate_rule,
		deactivate_rule,

		// Testing (Phase 2)
		simulate_rule,
		preview_execution,

		// Processes
		fetch_processes,
		get_process_operations,
		get_operation_config_fields,
		fetch_available_rules,

		// UI navigation
		next_config_node,
		prev_config_node,

		// Test
		set_test_result,
		clear_test_result,

		// Node operations
		pasteNodes,
		open_config,
	};
});
