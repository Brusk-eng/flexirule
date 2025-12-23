import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const useStore = defineStore("rule-builder-store", () => {
    let rule_name = ref(null);
    let rule_doc = ref(null);
    let graph = ref({ elements: [], selected: null });
    let process_methods = ref([]);
    let available_rules = ref([]);
    let is_dirty = ref(false);
    let initial_state = ref(null);
    let trigger_event_options = ref([]);
    let doc_meta = ref({}); // { doctype: [fields] }
    let fetch_counter = ref(0);
    let meta_loading = computed(() => fetch_counter.value > 0);

    const doc_fields = computed(() => {
        const doctype = rule_doc.value?.document_type;
        if (!doctype || !doc_meta.value[doctype]) return [];
        return doc_meta.value[doctype];
    });

    async function fetch_metadata(doctype) {
        if (!doctype || doc_meta.value[doctype]) return;
        fetch_counter.value++;
        try {
            // Promise wrapper because frappe.model.with_doctype uses a callback
            await new Promise((resolve) => {
                frappe.model.with_doctype(doctype, resolve);
            });

            const meta = frappe.get_meta(doctype);
            if (!meta) {
                return;
            }

            const fields = [];
            const excludedTypes = ['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button', 'Image', 'Fold', 'Heading', 'Spacer'];

            // 1. Add Main Table Fields (doc.*)
            meta.fields.forEach(f => {
                if (!excludedTypes.includes(f.fieldtype)) {
                    fields.push({
                        label: `doc.${f.fieldname} (${f.label})`,
                        value: `doc.${f.fieldname}`,
                        fieldname: f.fieldname,
                        fieldtype: f.fieldtype,
                        options: f.options,
                        is_main: true
                    });
                }
            });

            // Standard Fields
            const stdFields = [
                { label: 'Name (name)', fieldname: 'name', fieldtype: 'Data' },
                { label: 'Owner (owner)', fieldname: 'owner', fieldtype: 'Data' },
                { label: 'Creation (creation)', fieldname: 'creation', fieldtype: 'Datetime' },
                { label: 'Modified (modified)', fieldname: 'modified', fieldtype: 'Datetime' },
                { label: 'Modified By (modified_by)', fieldname: 'modified_by', fieldtype: 'Data' },
                { label: 'DocStatus (docstatus)', fieldname: 'docstatus', fieldtype: 'Int' }
            ];
            stdFields.forEach(f => {
                fields.push({
                    label: `doc.${f.fieldname} (${f.label})`,
                    value: `doc.${f.fieldname}`,
                    fieldname: f.fieldname,
                    fieldtype: f.fieldtype,
                    is_std: true
                });
            });

            // Use spread for deep reactivity
            doc_meta.value = { ...doc_meta.value, [doctype]: fields };

            // 2. Pre-fetch Child Tables metadata
            const tableFields = meta.fields.filter(f => f.fieldtype === 'Table' && f.options);
            for (const tf of tableFields) {
                await fetch_metadata(tf.options);
            }

        } catch (e) {
            // Silent fail - metadata fetch errors are non-critical
        } finally {
            fetch_counter.value--;
        }
    }

    function get_fields_for_doctype(doctype, alias = 'doc') {
        if (!doctype) return [];
        if (!doc_meta.value[doctype]) {
            return [];
        }

        return doc_meta.value[doctype].map(f => ({
            ...f,
            label: `${alias}.${f.fieldname} (${f.label.split('(')[1] ? f.label.split('(')[1].replace(')', '') : f.label})`,
            value: `${alias}.${f.fieldname}`
        }));
    }

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

        if (rule_doc.value?.document_type) {
            await fetch_metadata(rule_doc.value.document_type);
        }

        if (!trigger_event_options.value.length) {
            await frappe.model.with_doctype("Rule");
            const meta = frappe.get_meta("Rule");
            if (meta && meta.fields) {
                const trigger_field = meta.fields.find(f => f.fieldname === "trigger_event");
                if (trigger_field && trigger_field.options) {
                    trigger_event_options.value = trigger_field.options.split("\n");
                }
            }
        }

        if (!rule_doc.value) {
            frappe.show_alert({ message: __("Rule not found"), indicator: "orange" });
            return;
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
                    trigger_event: rule_doc.value.trigger_event,
                    trigger_condition: rule_doc.value.trigger_condition,
                    is_enabled: 1
                }
            }];
        }

        setup_breadcrumbs();
        initial_state.value = JSON.stringify(getStateSnapshot());
        is_dirty.value = false;
        commit_history();
    }

    // --- Cascade Disable Logic ---
    const effectiveDisabledIds = computed(() => {
        const disabledSet = new Set();
        const nodes = graph.value.elements.filter(el => el.position);
        const edges = graph.value.elements.filter(el => el.source);

        const nodeMap = new Map(nodes.map(n => [n.id, n]));
        const adj = new Map();

        edges.forEach(e => {
            if (!adj.has(e.source)) adj.set(e.source, []);
            adj.get(e.source).push(e.target);
        });

        const visited = new Set();
        const queue = ['start'];

        // BFS to find all reachable ENABLED nodes
        while (queue.length > 0) {
            const currentId = queue.shift();
            // If already visited, skip
            if (visited.has(currentId)) continue;

            // If explicitly disabled (and not start), it blocks path
            const node = nodeMap.get(currentId);
            if (currentId !== 'start' && node?.data?.is_enabled === 0) {
                continue; // Don't traverse children
            }

            visited.add(currentId);

            const children = adj.get(currentId) || [];
            children.forEach(childId => {
                if (!visited.has(childId)) queue.push(childId);
            });
        }

        // All nodes NOT in visited are effectively disabled
        nodes.forEach(n => {
            if (!visited.has(n.id)) disabledSet.add(n.id);
        });

        return disabledSet;
    });

    function getEffectivelyDisabledIds() {
        return effectiveDisabledIds.value;
    }
    // -----------------------------

    function commit_history() {
        const state = JSON.stringify(graph.value.elements);
        if (history_index.value < history.value.length - 1) {
            history.value = history.value.slice(0, history_index.value + 1);
        }
        if (history.value.length > 0 && history.value[history.value.length - 1] === state) return;
        history.value.push(state);
        if (history.value.length > MAX_HISTORY) history.value.shift();
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

    function can_undo() { return history_index.value > 0; }
    function can_redo() { return history_index.value < history.value.length - 1; }

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
        // ... (Existing sync logic skipped for brevity, keeping it simple as fetch calls this)
        // Re-implementing basic Sync for robustness in this script
        nodes.push({
            id: 'start', type: 'start', position: { x: 100, y: 100 }, label: 'Start',
            data: {
                document_type: rule_doc.value.document_type,
                trigger_event: rule_doc.value.trigger_event,
                trigger_condition_expression: rule_doc.value.trigger_condition_expression,
                trigger_condition: rule_doc.value.trigger_condition,
                is_enabled: 1
            }
        });

        rule_doc.value.actions.forEach((action, index) => {
            const nodeId = action.action_id || `action-${index}`;
            // Support both 'config' (new) and 'method_config' (legacy) fields
            const configData = action.config || action.method_config;
            nodes.push({
                id: nodeId,
                type: (action.action_type || 'Process').toLowerCase(),
                position: { x: action.position_x || 300, y: action.position_y || (150 + index * 120) },
                label: action.action_label || `Action ${index + 1}`,
                data: {
                    action_id: nodeId, action_type: action.action_type, action_label: action.action_label,
                    process_method: action.process_method, config: configData,
                    condition_expression: action.condition_expression,
                    condition_json: action.condition_json,
                    is_enabled: action.is_enabled,
                    on_error: action.on_error, next_step_if_true: action.next_step_if_true,
                    next_step_if_false: action.next_step_if_false,
                    timeout: action.timeout, priority: action.priority,
                    retry_count: action.retry_count, return_variable: action.return_variable,
                    is_async: action.is_async, name: action.name,
                    input_mapping: action.input_mapping,
                    output_mapping: action.output_mapping,
                    rule: action.rule || (action.action_type === 'Sub-Rule' ? getSubRuleName(configData) : null),
                    // Sub-Rule bypass fields
                    skip_conditions: action.skip_conditions !== undefined ? action.skip_conditions : 1,
                    skip_permissions: action.skip_permissions || 0
                }
            });
        });

        rule_doc.value.actions.forEach((action, index) => {
            const nodeId = action.action_id || `action-${index}`;
            if (action.next_step_if_true) {
                edges.push({
                    id: `e-${nodeId}-${action.next_step_if_true}-true`,
                    source: nodeId, target: action.next_step_if_true,
                    sourceHandle: (action.action_type === 'Condition' || action.action_type === 'Loop') ? 'default' : 'default'
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

    function getSubRuleName(configStr) {
        try { return JSON.parse(configStr).rule; } catch { return null; }
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

    async function fetch_available_rules(doctype) {
        if (!doctype) return;
        try {
            const rules = await frappe.db.get_list('Rule', {
                fields: ['name', 'rule_name', 'trigger_event', 'is_active'],
                filters: {
                    document_type: doctype,
                    name: ['!=', rule_name.value || '']
                },
                limit: 0
            });
            available_rules.value = rules || [];
        } catch {
            available_rules.value = [];
        }
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

            const currentIsActive = rule_doc.value.is_active;
            frappe.model.sync(fresh.message);
            let doc = frappe.get_doc("Rule", rule_name.value);
            doc.is_active = currentIsActive;
            doc.visual_data = JSON.stringify(clean_graph_data());

            const startNode = graph.value.elements.find(el => el.id === 'start');
            doc.trigger_condition_expression = startNode?.data?.trigger_condition_expression || null;
            doc.trigger_condition = startNode?.data?.trigger_condition || null;

            const nodes = graph.value.elements.filter(el => el.position && el.id !== 'start');
            const edgesList = graph.value.elements.filter(el => el.source);
            const orderedNodes = getTopologicalSort(nodes, edgesList);

            doc.actions = orderedNodes.map((node, idx) => {
                const outgoing = edgesList.filter(e => e.source === node.id);
                // Loop/Condition use 'default'/'true' for True path
                const true_edge = outgoing.find(e => e.sourceHandle === 'true' || e.sourceHandle === 'default');
                const false_edge = outgoing.find(e => e.sourceHandle === 'false');
                const incoming = edgesList.find(e => e.target === node.id);
                const is_entry_action = incoming && incoming.source === 'start' ? 1 : 0;
                let prev_action_id = null;
                if (!is_entry_action && incoming) {
                    const parentNode = nodes.find(n => n.id === incoming.source);
                    prev_action_id = parentNode?.data?.action_id || incoming.source;
                }

                return {
                    name: node.data?.name,
                    idx: idx + 1,
                    action_id: node.data?.action_id || node.id,
                    action_label: node.label,
                    is_entry_action: is_entry_action,
                    prev_action_id: prev_action_id,
                    action_type: node.data?.action_type === 'Sub-rule' ? 'Sub-Rule' : (node.data?.action_type || 'Process'),
                    is_enabled: node.data?.is_enabled !== undefined ? node.data.is_enabled : 1,
                    process_method: node.data?.process_method,
                    config: node.data?.config,  // New field name
                    condition_expression: node.data?.condition_expression,
                    condition_json: node.data?.condition_json,
                    input_mapping: node.data?.input_mapping,
                    output_mapping: node.data?.output_mapping,
                    on_error: node.data?.on_error || 'Stop',
                    timeout: node.data?.timeout || 30,
                    priority: node.data?.priority || 0,
                    retry_count: node.data?.retry_count || 0,
                    return_variable: node.data?.return_variable,
                    rule: node.data?.rule,
                    is_async: node.data?.is_async || 0,
                    // Sub-Rule bypass fields
                    skip_conditions: node.data?.skip_conditions !== undefined ? node.data.skip_conditions : 1,
                    skip_permissions: node.data?.skip_permissions || 0,
                    next_step_if_true: true_edge?.target || null,
                    next_step_if_false: false_edge?.target || null,
                    position_x: Math.round(node.position.x),
                    position_y: Math.round(node.position.y)
                };
            });

            await frappe.call({ method: "frappe.client.save", args: { doc } });
            frappe.toast(__("Saved"));
            await fetch();
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
            // Normalize action_type casing
            if (obj.data?.action_type === 'Sub-rule') {
                obj.data.action_type = 'Sub-Rule';
            }
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

    function delete_edge(edgeId) {
        const edge = graph.value.elements.find(el => el.id === edgeId && el.source);
        if (!edge) return;

        // Clear the next_step reference in the source node's data
        const sourceNode = graph.value.elements.find(el => el.position && el.id === edge.source);
        if (sourceNode && sourceNode.data) {
            if (edge.sourceHandle === 'false') {
                sourceNode.data.next_step_if_false = null;
            } else {
                sourceNode.data.next_step_if_true = null;
            }
        }

        // Remove the edge
        graph.value.elements = graph.value.elements.filter(el => el.id !== edgeId);
        mark_dirty();
    }

    function getTopologicalSort(nodes, edges) {
        // ... (Same topological sort logic)
        const adj = {};
        const visited = new Set();
        const result = [];
        nodes.forEach(n => adj[n.id] = []);
        edges.forEach(e => { if (adj[e.source]) adj[e.source].push(e.target); });
        const startEdges = graph.value.elements.filter(el => el.source === 'start');
        const queue = startEdges.map(e => e.target).filter(id => nodes.find(n => n.id === id));
        const processed = new Set();
        queue.forEach(id => {
            if (id && !processed.has(id)) { processed.add(id); result.push(nodes.find(n => n.id === id)); }
        });
        let ptr = 0;
        while (ptr < result.length) {
            const current = result[ptr++];
            const children = adj[current.id] || [];
            children.forEach(childId => {
                const childNode = nodes.find(n => n.id === childId);
                if (childNode && !processed.has(childId)) { processed.add(childId); result.push(childNode); }
            });
        }
        nodes.forEach(n => { if (!processed.has(n.id)) result.push(n); });
        return result;
    }

    return {
        rule_name, rule_doc, graph, process_methods, available_rules, is_dirty, effectiveDisabledIds,
        trigger_event_options, doc_fields, doc_meta, meta_loading,
        fetch, fetch_metadata, get_fields_for_doctype, get_process_method_schema, save_changes, mark_dirty, mark_position_change,
        clear_dirty, delete_node, delete_edge, getEffectivelyDisabledIds, fetch_available_rules,
        undo, redo, can_undo, can_redo, commit_history
    };
});
