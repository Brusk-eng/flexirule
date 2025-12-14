import { defineStore } from "pinia";
import { ref, watch } from "vue";

export const useStore = defineStore("rule-builder-store", () => {
    let rule_name = ref(null);
    let rule_doc = ref(null);
    let graph = ref({ elements: [], selected: null });
    let process_methods = ref([]);
    let is_dirty = ref(false);
    let initial_state = ref(null);

    // Undo/Redo history
    let history = ref([]);
    let history_index = ref(-1);
    const MAX_HISTORY = 50;

    async function fetch() {
        if (!rule_name.value) return;

        const result = await frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Rule", name: rule_name.value }
        });

        if (result.message) {
            frappe.model.sync(result.message);
            rule_doc.value = frappe.get_doc("Rule", rule_name.value);
        }

        await fetch_process_methods();

        const visual_data = rule_doc.value.visual_data && typeof rule_doc.value.visual_data === "string"
            ? JSON.parse(rule_doc.value.visual_data)
            : null;

        if (visual_data && visual_data.length > 0) {
            graph.value.elements = visual_data;
        } else if (rule_doc.value.actions && rule_doc.value.actions.length > 0) {
            sync_actions_to_graph();
        } else {
            graph.value.elements = [{
                id: 'start',
                type: 'start',
                position: { x: 100, y: 100 },
                label: 'Start',
                data: {
                    document_type: rule_doc.value.document_type,
                    trigger_event: rule_doc.value.trigger_event
                }
            }];
        }

        setup_breadcrumbs();
        initial_state.value = JSON.stringify(getStateSnapshot());
        is_dirty.value = false;

        // Initialize history
        commit_history();
    }

    // ==================
    // UNDO/REDO
    // ==================
    function commit_history() {
        const state = JSON.stringify(graph.value.elements);

        // Remove future states if we're not at the end
        if (history_index.value < history.value.length - 1) {
            history.value = history.value.slice(0, history_index.value + 1);
        }

        // Don't add duplicate states
        if (history.value.length > 0 && history.value[history.value.length - 1] === state) {
            return;
        }

        history.value.push(state);

        // Limit history size
        if (history.value.length > MAX_HISTORY) {
            history.value.shift();
        }

        history_index.value = history.value.length - 1;
    }

    function undo() {
        if (history_index.value > 0) {
            history_index.value--;
            graph.value.elements = JSON.parse(history.value[history_index.value]);
            is_dirty.value = true;
        }
    }

    function redo() {
        if (history_index.value < history.value.length - 1) {
            history_index.value++;
            graph.value.elements = JSON.parse(history.value[history_index.value]);
            is_dirty.value = true;
        }
    }

    function can_undo() {
        return history_index.value > 0;
    }

    function can_redo() {
        return history_index.value < history.value.length - 1;
    }

    function setup_breadcrumbs() {
        let breadcrumbs = `
            <li><a href="/app/rule">${__("Rule")}</a></li>
            <li><a href="/app/rule/${rule_name.value}">${__(rule_doc.value?.rule_name || rule_name.value)}</a></li>
            <li class="disabled"><a href="#">${__("Builder")}</a></li>
        `;
        frappe.breadcrumbs.clear();
        frappe.breadcrumbs.$breadcrumbs.append(breadcrumbs);
    }

    function getStateSnapshot() {
        return graph.value.elements.map(el => {
            if (el.position) {
                return {
                    id: el.id, type: el.type, label: el.label, data: el.data,
                    position: { x: Math.round(el.position.x), y: Math.round(el.position.y) }
                };
            } else {
                return { id: el.id, source: el.source, target: el.target, sourceHandle: el.sourceHandle };
            }
        }).sort((a, b) => a.id.localeCompare(b.id));
    }

    function checkDirty() {
        if (!initial_state.value) return false;
        return JSON.stringify(getStateSnapshot()) !== initial_state.value;
    }

    function sync_actions_to_graph() {
        const nodes = [];
        const edges = [];

        nodes.push({
            id: 'start', type: 'start', position: { x: 100, y: 100 }, label: 'Start',
            data: {
                document_type: rule_doc.value.document_type,
                trigger_event: rule_doc.value.trigger_event,
                trigger_filters: rule_doc.value.trigger_filters
            }
        });

        rule_doc.value.actions.forEach((action, index) => {
            const nodeId = action.action_id || `action-${index}`;
            nodes.push({
                id: nodeId,
                type: (action.action_type || 'Process').toLowerCase(),
                position: { x: action.position_x || 300, y: action.position_y || (150 + index * 120) },
                label: action.action_label || `Action ${index + 1}`,
                data: {
                    action_id: nodeId, action_type: action.action_type, action_label: action.action_label,
                    process_method: action.process_method, method_config: action.method_config,
                    condition_expression: action.condition_expression, is_enabled: action.is_enabled,
                    on_error: action.on_error, next_step_if_true: action.next_step_if_true,
                    next_step_if_false: action.next_step_if_false,
                    timeout: action.timeout, priority: action.priority,
                    retry_count: action.retry_count, return_variable: action.return_variable,
                    is_async: action.is_async, name: action.name // Preserve DB name
                }
            });
        });

        rule_doc.value.actions.forEach((action, index) => {
            const nodeId = action.action_id || `action-${index}`;
            if (action.next_step_if_true) {
                edges.push({
                    id: `e-${nodeId}-${action.next_step_if_true}-true`,
                    source: nodeId, target: action.next_step_if_true,
                    sourceHandle: action.action_type === 'Condition' ? 'true' : 'default'
                });
            }
            if (action.next_step_if_false) {
                edges.push({
                    id: `e-${nodeId}-${action.next_step_if_false}-false`,
                    source: nodeId, target: action.next_step_if_false, sourceHandle: 'false'
                });
            }
        });

        graph.value.elements = [...nodes, ...edges];
    }

    async function fetch_process_methods() {
        try {
            const methods = await frappe.db.get_list('Process Method', {
                fields: ['name', 'method_name', 'category', 'config_schema', 'description', 'method_path'],
                filters: { is_enabled: 1 }, limit: 0
            });
            process_methods.value = methods || [];
        } catch { process_methods.value = []; }
    }

    async function get_process_method_schema(method_name) {
        if (!method_name) return null;
        const method = process_methods.value.find(m => m.name === method_name);
        if (method?.config_schema) {
            try { return JSON.parse(method.config_schema); } catch { return null; }
        }
        return null;
    }

    function mark_dirty() {
        is_dirty.value = true;
        commit_history();
    }

    function mark_position_change() {
        is_dirty.value = checkDirty();
        if (is_dirty.value) commit_history();
    }

    function clear_dirty() {
        initial_state.value = JSON.stringify(getStateSnapshot());
        is_dirty.value = false;
    }

    async function save_changes() {
        frappe.dom.freeze(__("Saving..."));
        try {
            const fresh = await frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Rule", name: rule_name.value }
            });

            // Capture current is_active state before syncing fresh data
            const currentIsActive = rule_doc.value.is_active;

            frappe.model.sync(fresh.message);
            let doc = frappe.get_doc("Rule", rule_name.value);

            // Restore is_active
            doc.is_active = currentIsActive;

            doc.visual_data = JSON.stringify(clean_graph_data());

            // Save Start Node Filters
            const startNode = graph.value.elements.find(el => el.id === 'start');
            if (startNode?.data?.trigger_filters) {
                doc.trigger_filters = startNode.data.trigger_filters;
            } else {
                doc.trigger_filters = null;
            }

            const nodes = graph.value.elements.filter(el => el.position && el.id !== 'start');
            const edgesList = graph.value.elements.filter(el => el.source);

            // Topological sort for execution order
            const orderedNodes = getTopologicalSort(nodes, edgesList);

            doc.actions = orderedNodes.map((node, idx) => {
                const outgoing = edgesList.filter(e => e.source === node.id);
                const true_edge = outgoing.find(e => e.sourceHandle === 'true' || e.sourceHandle === 'default');
                const false_edge = outgoing.find(e => e.sourceHandle === 'false');

                // Determine lineage
                const incoming = edgesList.find(e => e.target === node.id);
                const is_entry_action = incoming && incoming.source === 'start' ? 1 : 0;
                // If not from root, prev_action_id comes from the source node's action_id (or id)
                // Note: The source node in the graph is `incoming.source`.
                // We need to match this to a node to get its action_id if available, though typically id IS the action_id.
                // However, `data.action_id` is reliable.
                let prev_action_id = null;
                if (!is_entry_action && incoming) {
                    const parentNode = nodes.find(n => n.id === incoming.source);
                    prev_action_id = parentNode?.data?.action_id || incoming.source;
                }

                return {
                    name: node.data?.name || undefined, // Preserve existing name to avoid delete/insert
                    idx: idx + 1, // 1-based index
                    action_id: node.data?.action_id || node.id,
                    action_label: node.label,

                    is_entry_action: is_entry_action,
                    prev_action_id: prev_action_id,

                    action_type: node.data?.action_type,
                    is_enabled: node.data?.is_enabled !== undefined ? node.data.is_enabled : 1,
                    process_method: node.data?.process_method || null,
                    method_config: node.data?.method_config || null,
                    condition_expression: node.data?.condition_expression || null,
                    on_error: node.data?.on_error || 'Stop',

                    timeout: node.data?.timeout || 30,
                    priority: node.data?.priority || 0,
                    retry_count: node.data?.retry_count || 0,
                    return_variable: node.data?.return_variable || null,
                    is_async: node.data?.is_async || 0,

                    next_step_if_true: true_edge?.target || null,
                    next_step_if_false: false_edge?.target || null,
                    position_x: Math.round(node.position.x),
                    position_y: Math.round(node.position.y)
                };
            });

            await frappe.call({ method: "frappe.client.save", args: { doc } });
            frappe.toast(__("Saved"));
            clear_dirty();
        } catch (e) {
            frappe.msgprint({ title: __('Error'), message: e.message || __('Save failed'), indicator: 'red' });
        } finally {
            frappe.dom.unfreeze();
        }
    }

    function clean_graph_data() {
        return graph.value.elements.map((el) => {
            const { selected, dragging, resizing, sourceNode, targetNode, ...obj } = el;
            return obj;
        });
    }

    function delete_node(nodeId) {
        if (nodeId === 'start') {
            frappe.msgprint(__('Cannot delete start node'));
            return;
        }
        graph.value.elements = graph.value.elements.filter(el =>
            el.id !== nodeId && el.source !== nodeId && el.target !== nodeId
        );
        if (graph.value.selected?.id === nodeId) graph.value.selected = null;
        mark_dirty();
    }

    // Sort nodes based on flow traversal
    function getTopologicalSort(nodes, edges) {
        // Create adjacency list
        const adj = {};
        const visited = new Set();
        const result = [];

        nodes.forEach(n => adj[n.id] = []);
        edges.forEach(e => {
            if (adj[e.source]) adj[e.source].push(e.target);
        });

        // Find start node's next steps to begin traversal
        const startEdges = graph.value.elements.filter(el => el.source === 'start');
        const queue = startEdges.map(e => e.target).filter(id => nodes.find(n => n.id === id));

        // BFS-like traversal to capture flow order
        // This is a simple heuristic, real topological sort requires full DAG check
        const processed = new Set();

        // First add nodes reachable from start
        queue.forEach(id => {
            if (id && !processed.has(id)) {
                processed.add(id);
                result.push(nodes.find(n => n.id === id));
            }
        });

        // Continue with their children
        let ptr = 0;
        while (ptr < result.length) {
            const current = result[ptr++];
            const children = adj[current.id] || [];
            children.forEach(childId => {
                const childNode = nodes.find(n => n.id === childId);
                if (childNode && !processed.has(childId)) {
                    processed.add(childId);
                    result.push(childNode);
                }
            });
        }

        // Add any disconnected nodes at the end
        nodes.forEach(n => {
            if (!processed.has(n.id)) {
                result.push(n);
            }
        });

        return result;
    }

    return {
        rule_name, rule_doc, graph, process_methods, is_dirty,
        fetch, get_process_method_schema, save_changes, mark_dirty, mark_position_change,
        clear_dirty, delete_node,
        // Undo/Redo
        undo, redo, can_undo, can_redo, commit_history
    };
});
