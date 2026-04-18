/**
 * useGraphStore — Nodes, edges, topology, and graph operations.
 *
 * Follows Frappe builder pattern (workflow_builder: elements + node/edge ops):
 *   - Owns the visual graph state (nodes, edges)
 *   - Provides graph operations: add, delete, touch, topology
 *   - Sync logic: actions ↔ graph, merge visual layout
 *   - No knowledge of Rule document lifecycle (that's useRuleStore)
 *
 * Extracted from store.js lines: 15-16, 261-394, 427-736, 1223-1434
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
	getContract,
	getEffectiveActionPolicy,
	getOperationOptions,
	normalizeActionType,
	ACTION_TYPES_WITH_REFERENCE_CONTEXT,
	ACTION_TYPES_WITH_RETURN_SCHEMA,
} from "../../core/contracts";
import { mapActionTypeToNodeType } from "../composables/useActionTypeMapper";
import { getConditionPayload } from "../utils/condition_payload";
import { generateShortId } from "../../utils/index.js";

export const useGraphStore = defineStore("rule-builder-graph", () => {
	// ── Core graph state ──
	const nodes = ref([]);
	const edges = ref([]);

	// ── Cascade disable computed ──
	// BFS from start node: any node not reachable via enabled path is "effectively disabled"
	const effectiveDisabledIds = computed(() => {
		const disabledSet = new Set();
		const nodeMap = new Map(nodes.value.map((n) => [n.id, n]));
		const adj = new Map();

		edges.value.forEach((e) => {
			if (!adj.has(e.source)) adj.set(e.source, []);
			adj.get(e.source).push(e.target);
		});

		const visited = new Set();
		const queue = ["start"];

		while (queue.length > 0) {
			const currentId = queue.shift();
			if (visited.has(currentId)) continue;

			const node = nodeMap.get(currentId);
			if (currentId !== "start" && node?.data?.is_enabled === 0) {
				continue;
			}

			visited.add(currentId);
			const children = adj.get(currentId) || [];
			children.forEach((childId) => {
				if (!visited.has(childId)) queue.push(childId);
			});
		}

		nodes.value.forEach((n) => {
			if (!visited.has(n.id)) disabledSet.add(n.id);
		});

		return disabledSet;
	});

	function getEffectivelyDisabledIds() {
		return effectiveDisabledIds.value;
	}

	// ── Snapshot for dirty checking + history ──
	function getStateSnapshot() {
		const nodesSnap = nodes.value.map((el) => ({
			id: el.id,
			type: el.type,
			label: el.label,
			data: el.data,
			position: { x: Math.round(el.position.x), y: Math.round(el.position.y) },
		}));
		const edgesSnap = edges.value.map((el) => ({
			id: el.id,
			source: el.source,
			target: el.target,
			sourceHandle: el.sourceHandle,
		}));
		return [...nodesSnap, ...edgesSnap].sort((a, b) => a.id.localeCompare(b.id));
	}

	function getGraphSnapshot() {
		return { nodes: nodes.value, edges: edges.value };
	}

	function applyGraphSnapshot(snapshot) {
		if (snapshot.nodes) nodes.value = snapshot.nodes;
		if (snapshot.edges) edges.value = snapshot.edges;
	}

	// ── Topological sort ──
	function getTopologicalSort(nodeList, edgeList) {
		nodeList = nodeList || nodes.value;
		edgeList = edgeList || edges.value;

		const adj = {};
		const processed = new Set();
		const result = [];
		nodeList.forEach((n) => (adj[n.id] = []));
		edgeList.forEach((e) => {
			if (adj[e.source]) adj[e.source].push(e.target);
		});

		const entryNode = nodeList.find(
			(n) => n.id === "start" || n.type === "start" || n.data?.action_type === "Entry Action"
		);
		if (entryNode && !processed.has(entryNode.id)) {
			processed.add(entryNode.id);
			result.push(entryNode);
		}

		let ptr = 0;
		while (ptr < result.length) {
			const current = result[ptr++];
			const children = adj[current.id] || [];
			children.forEach((childId) => {
				const childNode = nodeList.find((n) => n.id === childId);
				if (childNode && !processed.has(childId)) {
					processed.add(childId);
					result.push(childNode);
				}
			});
		}

		// Add any orphaned nodes not reached by BFS
		nodeList.forEach((n) => {
			if (!processed.has(n.id)) result.push(n);
		});

		return result;
	}

	// ── Available variables (upstream context) ──
	async function getAvailableVariables(upToNodeId = null, ruleDoc = null) {
		const doctype = ruleDoc?.document_type;
		const context_vars = [];
		const sortedNodes = getTopologicalSort(nodes.value, edges.value);

		let limitIndex = sortedNodes.length;
		if (upToNodeId) {
			const idx = sortedNodes.findIndex((n) => n.id === upToNodeId);
			if (idx !== -1) limitIndex = idx;
		}

		for (let i = 0; i < limitIndex; i++) {
			const node = sortedNodes[i];
			const data = node.data || {};
			if (!data.return_variable) continue;

			context_vars.push({
				label: data.return_variable,
				value: data.return_variable,
				type: mapReturnTypeToFieldType(data.return_type),
			});

			if (
				data.resolved_output_schema &&
				!["Yes / No", "List of Values", "List of Records"].includes(data.return_type)
			) {
				let schema = data.resolved_output_schema;
				if (typeof schema === "string") {
					try {
						schema = JSON.parse(schema);
					} catch (e) {
						schema = [];
					}
				}
				if (Array.isArray(schema)) {
					schema.forEach((field) => {
						if (field.fieldname) {
							context_vars.push({
								label: `${data.return_variable}.${field.fieldname} (${
									field.label || field.fieldname
								})`,
								value: `${data.return_variable}.${field.fieldname}`,
								type: field.fieldtype || "Data",
							});
						}
					});
				}
			}
		}

		return await flexirule.utils.get_combined_fields(doctype, context_vars, "doc");
	}

	function mapReturnTypeToFieldType(returnType) {
		switch (returnType) {
			case "Yes / No":
				return "Check";
			case "List of Values":
			case "List of Records":
				return "Table";
			case "Single Record":
			case "Full Document":
				return "Data";
			default:
				return returnType || "Data";
		}
	}

	// ── Node operations ──
	function get_default_node_data(type, label = "") {
		const id = generateShortId();
		const actionType = normalizeActionType(flexirule.utils.to_title_case(type));
		const baseData = {
			action_id: id,
			action_type: actionType,
			action_label: label || `New ${actionType}`,
			is_enabled: 1,
			is_async: 0,
			skip_conditions: 1,
			mutation_mode: null,
		};

		// Type-specific defaults
		if (type === "condition") {
			baseData.action_type = "Condition";
			baseData.compiled_expression = "";
			baseData.config = { op: "and", conditions: [] };
			baseData.condition_json = null;
		} else if (type === "wait") {
			baseData.action_type = "Wait";
			baseData.config = { wait_type: "Duration", value: 1, unit: "Minutes" };
		} else if (type === "set value") {
			baseData.action_type = "Set Value";
			baseData.config = { static_values: {} };
		} else if (type === "stop") {
			baseData.action_type = "Stop";
			baseData.operation = "Success";
		} else if (type === "sub-rule") {
			baseData.action_type = "Sub-Rule";
		} else if (type === "query" || type === "query records") {
			baseData.action_type = "Query Records";
			baseData.operation = "Query List";
			baseData.return_variable = "query_result";
		}

		return baseData;
	}

	function delete_node(nodeId, isReadOnly = false) {
		if (isReadOnly) {
			frappe.msgprint(__("Cannot edit active rule. Please switch to Draft mode."));
			return false;
		}

		const node = nodes.value.find((el) => el.id === nodeId);
		if (
			nodeId === "start" ||
			nodeId === "root" ||
			node?.type === "start" ||
			node?.data?.action_type === "Entry Action"
		) {
			frappe.msgprint(__("Cannot delete start node"));
			return false;
		}

		nodes.value = nodes.value.filter((el) => el.id !== nodeId);
		edges.value = edges.value.filter((el) => el.source !== nodeId && el.target !== nodeId);
		return true;
	}

	function delete_edge(edgeId, isReadOnly = false) {
		if (isReadOnly) return false;
		const edge = edges.value.find((el) => el.id === edgeId);
		if (!edge) return false;

		// Clear the next_step reference in the source node's data
		const sourceNode = nodes.value.find((el) => el.id === edge.source);
		if (sourceNode && sourceNode.data) {
			const handle = edge.sourceHandle || "default";
			if (handle === "false") {
				if (sourceNode.data.next_step_if_false === edge.target) {
					sourceNode.data.next_step_if_false = null;
				}
			} else if (handle === "true" || handle === "default") {
				if (sourceNode.data.next_step_if_true === edge.target) {
					sourceNode.data.next_step_if_true = null;
				}
			}
		}

		edges.value = edges.value.filter((el) => el.id !== edgeId);
		return true;
	}

	function insert_node_on_edge(edgeId, nodeType = "selector", options = {}) {
		const edge = edges.value.find((e) => e.id === edgeId);
		if (!edge) return;

		const sourceId = edge.source;
		const targetId = edge.target;
		const sourceHandle = edge.sourceHandle || "default";

		// 1. Create new node
		const newNodeId = generateShortId();
		const nodeData = get_default_node_data(nodeType, options.label);

		// Apply options (operation, process_name)
		if (options.operation) nodeData.operation = options.operation;
		if (options.process_name) nodeData.process_name = options.process_name;

		const newNode = {
			id: newNodeId,
			type: mapActionTypeToNodeType(nodeData.action_type),
			position: { x: 0, y: 0 }, // Will be fixed by auto-layout
			label: nodeData.action_label,
			data: {
				...nodeData,
				action_id: newNodeId,
				next_step_if_true: targetId,
			},
		};

		// 2. Remove old edge
		delete_edge(edgeId);

		// 3. Update source node pointer to new node
		const sourceNode = nodes.value.find((n) => n.id === sourceId);
		if (sourceNode && sourceNode.data) {
			if (sourceHandle === "false") {
				sourceNode.data.next_step_if_false = newNodeId;
			} else {
				sourceNode.data.next_step_if_true = newNodeId;
			}
		}

		// 4. Add new node
		nodes.value = [...nodes.value, newNode];

		// 5. Create new edges
		const edge1Id = `e-${sourceId}-${newNodeId}-${sourceHandle}`;
		const edge2Id = `e-${newNodeId}-${targetId}-default`;

		edges.value = [
			...edges.value,
			{
				id: edge1Id,
				source: sourceId,
				target: newNodeId,
				sourceHandle: sourceHandle,
				type: "add",
			},
			{
				id: edge2Id,
				source: newNodeId,
				target: targetId,
				sourceHandle: "default",
				type: "add",
			},
		];

		return newNodeId;
	}

	function touch_node(nodeId) {
		if (!nodeId) return;
		const idx = nodes.value.findIndex((n) => n.id === nodeId);
		if (idx === -1) return;

		const current = nodes.value[idx];
		// Replace to trigger Vue reactivity
		nodes.value[idx] = {
			...current,
			data: { ...(current.data || {}) },
		};
	}

	// ── Data cleaning ──
	function clean_graph_data() {
		return [...nodes.value, ...edges.value].map((el) => {
			const { selected, dragging, resizing, sourceNode, targetNode, ...obj } = el;
			if (obj.data?.action_type) {
				obj.data.action_type = normalizeActionType(obj.data.action_type);
			}
			return obj;
		});
	}

	function clean_action_config(config) {
		if (!config || typeof config !== "object") return config;
		const clean = Array.isArray(config) ? [...config] : { ...config };

		// Clean filters
		if (Array.isArray(clean.filters)) {
			clean.filters = clean.filters.filter((f) => f.field || f.fieldname);
		}

		// Clean field lists
		if (Array.isArray(clean.fields)) {
			clean.fields = clean.fields.filter((f) => f && f.trim?.() !== "");
		}

		// Clean field_mappings
		if (Array.isArray(clean.field_mappings)) {
			clean.field_mappings = clean.field_mappings.filter((m) => m.source && m.target);
		}

		// Clean static_values
		if (clean.static_values && typeof clean.static_values === "object") {
			const cleaned_static = {};
			Object.entries(clean.static_values).forEach(([k, v]) => {
				if (k && k.trim() !== "") cleaned_static[k] = v;
			});
			clean.static_values = cleaned_static;
		}

		if (
			clean.input_mapping &&
			typeof clean.input_mapping === "object" &&
			!Array.isArray(clean.input_mapping) &&
			!Object.keys(clean.input_mapping).length
		) {
			delete clean.input_mapping;
		}

		if (
			clean.output_mapping &&
			typeof clean.output_mapping === "object" &&
			!Array.isArray(clean.output_mapping) &&
			!Object.keys(clean.output_mapping).length
		) {
			delete clean.output_mapping;
		}

		if (
			typeof clean.permission_audit_reason === "string" &&
			!clean.permission_audit_reason.trim()
		) {
			delete clean.permission_audit_reason;
		}

		return clean;
	}

	// ── Normalization ──
	function normalize_action_data(actionType, data = {}) {
		if (!actionType || !data) return data;

		// Bridging machine node types to canonical contract keys
		actionType = normalizeActionType(actionType);

		const normalized = { ...data, action_type: actionType };
		const contract = getContract(actionType);
		const operationOptions = getOperationOptions(actionType, {
			processName: normalized.process_name,
		}).map((opt) => opt.value);

		if (
			normalized.operation &&
			operationOptions.length &&
			!operationOptions.includes(normalized.operation)
		) {
			normalized.operation = null;
		}

		const policy = getEffectiveActionPolicy(actionType, {
			operation: normalized.operation,
			processName: normalized.process_name,
		});
		const allowedMutations = policy.allowed_mutations || contract.allowed_mutations || [];
		const allowedReturnTypes =
			policy.allowed_return_types || contract.allowed_return_types || [];

		if (
			normalized.mutation_mode &&
			(!allowedMutations.length || !allowedMutations.includes(normalized.mutation_mode))
		) {
			normalized.mutation_mode = null;
		}

		if (!ACTION_TYPES_WITH_REFERENCE_CONTEXT.has(actionType)) {
			normalized.input_source = null;
			normalized.reference_doctype = null;
			normalized.reference_docname = null;
		}

		if (!ACTION_TYPES_WITH_RETURN_SCHEMA.has(actionType)) {
			normalized.return_type = null;
			normalized.resolved_output_schema = null;
		} else {
			if (
				normalized.return_type &&
				allowedReturnTypes.length &&
				!allowedReturnTypes.includes(normalized.return_type)
			) {
				normalized.return_type = null;
			}
			if (!normalized.return_type && policy.default_return_type) {
				normalized.return_type = policy.default_return_type;
			}
		}

		if (actionType !== "Process") normalized.process_name = null;
		if (actionType !== "Sub-Rule") normalized.rule = null;
		if (actionType !== "Condition") {
			normalized.compiled_expression = null;
			normalized.condition_json = null;
			normalized.next_step_if_false = null;
		} else {
			normalized.condition_json = null;
		}
		if (contract.terminal) {
			normalized.next_step_if_true = null;
			normalized.next_step_if_false = null;
		}
		if (actionType === "Stop" && normalized.operation !== "Error") {
			normalized.value_template = null;
		}

		// Ensure Set Value always maintains its template
		if (actionType === "Set Value" && !normalized.value_template && normalized.config) {
			try {
				let cfg = normalized.config;
				if (typeof cfg === "string") cfg = JSON.parse(cfg);
				const text_ui = cfg.text_generator_ui;
				if (text_ui?.segments) {
					// Fallback re-compile if somehow lost
					normalized.value_template = (text_ui.segments || [])
						.map((s) => s.content || s.text || "")
						.join("");
				}
			} catch (e) {
				// ignore parse error
			}
		}

		return normalized;
	}

	function normalize_graph_nodes() {
		nodes.value = nodes.value.map((node) => {
			if (node.type === "start" || !node.data?.action_type) return node;
			return {
				...node,
				data: normalize_action_data(node.data.action_type, node.data),
			};
		});
	}

	// ── Sync: Rule Actions → Graph Nodes/Edges ──

	function getSubRuleName(configStr) {
		try {
			const parsed = typeof configStr === "string" ? JSON.parse(configStr) : configStr;
			return parsed?.sub_rule_name || parsed?.rule || null;
		} catch {
			return null;
		}
	}

	/**
	 * Build graph nodes and edges from a Rule document's actions array.
	 * This is the central sync function — mirrors Frappe's get_workflow_elements().
	 *
	 * @param {Object} ruleDoc - The rule document
	 * @param {Array} customActions — optional override for actions list
	 */
	function sync_actions_to_graph(ruleDoc, customActions = null) {
		const actionNodes = [];
		const actionEdges = [];

		const actionsList = customActions || ruleDoc.actions || [];
		const visualData = flexirule.utils.safe_json_parse(ruleDoc.visual_data, {});
		const visualNodes = new Map((visualData.nodes || []).map((n) => [n.id, n]));

		// Ensure we have a root/entry action node
		const rootAction = actionsList.find(
			(a) => a.action_type === "Entry Action" || a.action_id === "root"
		);

		if (!rootAction) {
			actionNodes.push({
				id: "start",
				type: "start",
				position: { x: 50, y: 250 },
				label: "Start",
				data: {
					action_id: "start",
					action_type: "Entry Action",
					document_type: ruleDoc.document_type,
					trigger_event: ruleDoc.trigger_event,
					compiled_expression: ruleDoc.compiled_expression,
					trigger_condition: ruleDoc.trigger_condition,
					is_enabled: 1,
				},
			});
		}

		for (const [index, action] of actionsList.entries()) {
			const nodeId = action.action_id || `act_${index}`;
			const originalActionType = (action.action_type || "Process").trim();
			const actionTypeRaw = normalizeActionType(originalActionType);
			let type = mapActionTypeToNodeType(actionTypeRaw);

			if (originalActionType === "Raise Error" && !action.operation) {
				action.operation = "Error";
			}

			const isRoot =
				actionTypeRaw === "Entry Action" || nodeId === "start" || nodeId === "root";

			if (isRoot) type = "start";

			const nodeLabel = isRoot ? "Start" : action.action_label || `Action ${index + 1}`;
			const safeParse = (val, defaultVal = null) => {
				if (val && typeof val === "object") return val;
				return flexirule.utils.safe_json_parse(val, defaultVal);
			};

			const configData = safeParse(action.config, {}) || {};
			const conditionPayload =
				actionTypeRaw === "Condition"
					? getConditionPayload({
							config: configData,
							condition_json: action.condition_json,
					  })
					: null;
			const effectiveConfig =
				actionTypeRaw === "Condition"
					? conditionPayload || configData || { op: "and", conditions: [] }
					: configData;

			const nodeData = {
				action_id: nodeId,
				action_type: actionTypeRaw,
				action_label: action.action_label,
				process_name: action.process_name,
				operation: action.operation,
				config: effectiveConfig,
				target_field: action.target_field,
				value_template: action.value_template,
				compiled_expression: action.compiled_expression,
				condition_json: null,
				is_enabled: action.is_enabled,
				on_error: action.on_error,
				timeout: action.timeout,
				priority: action.priority,
				retry_count: action.retry_count,
				return_variable: action.return_variable,
				is_async: action.is_async,
				name: action.name,
				rule:
					action.rule ||
					(actionTypeRaw === "Sub-Rule" ? getSubRuleName(effectiveConfig) : null),
				skip_conditions: action.skip_conditions !== undefined ? action.skip_conditions : 1,
				skip_permissions: action.skip_permissions || 0,
				next_step_if_true: action.next_step_if_true,
				next_step_if_false: action.next_step_if_false,
				input_source: action.input_source,
				reference_doctype: action.reference_doctype,
				reference_docname: action.reference_docname,
				mutation_mode: action.mutation_mode,
				return_type: action.return_type,
				resolved_output_schema: safeParse(action.resolved_output_schema),
				input_mapping: effectiveConfig.input_mapping || null,
				output_mapping: effectiveConfig.output_mapping || null,
			};

			if (isRoot) {
				nodeData.document_type = ruleDoc.document_type;
				nodeData.trigger_event = ruleDoc.trigger_event;
				nodeData.trigger_condition = ruleDoc.trigger_condition;
				nodeData.compiled_expression = ruleDoc.compiled_expression;
				nodeData.priority = ruleDoc.priority;
				nodeData.execution_mode = ruleDoc.execution_mode;
				nodeData.max_execution_time = ruleDoc.max_execution_time;
				nodeData.debug_mode = ruleDoc.debug_mode;
				nodeData.skip_for_roles = (ruleDoc.skip_for_roles || [])
					.map((row) => row.role)
					.filter(Boolean);
				nodeData.permissions = (ruleDoc.permissions || []).map((row) => ({
					role: row.role,
					can_execute: row.can_execute || 0,
				}));
				nodeData.description = ruleDoc.description;
				nodeData.exposed_as_subrule =
					ruleDoc.exposed_as_subrule ?? ruleDoc.is_sub_rule ?? 0;
				nodeData.version = ruleDoc.version;
				nodeData.status = ruleDoc.status;
				nodeData.previous_rule = ruleDoc.previous_rule;
				nodeData.is_active = ruleDoc.is_active;
			}

			actionNodes.push({
				id: nodeId,
				type: type,
				position: {
					x: isRoot ? 50 : 300,
					y: isRoot ? 250 : 150 + index * 120,
				},
				label: nodeLabel,
				data: nodeData,
				className: "",
				style: {},
			});
		}

		// Build edges from next_step references
		const sourceActions = customActions || actionsList;
		sourceActions.forEach((action, index) => {
			const nodeId = action.action_id || `act_${index}`;
			if (action.next_step_if_true) {
				actionEdges.push({
					id: `e-${nodeId}-${action.next_step_if_true}-true`,
					source: nodeId,
					target: action.next_step_if_true,
					sourceHandle:
						action.action_type === "Condition" || action.action_type === "Loop"
							? "true"
							: "default",
					type: "add",
					animated: action.action_type === "Entry Action",
				});
			}
			if (action.next_step_if_false) {
				actionEdges.push({
					id: `e-${nodeId}-${action.next_step_if_false}-false`,
					source: nodeId,
					target: action.next_step_if_false,
					sourceHandle: "false",
					type: "add",
				});
			}
		});

		nodes.value = [...actionNodes];
		edges.value = [...actionEdges];
	}

	/**
	 * Merge saved visual positions onto current graph nodes.
	 * Only merges positions + meta — never overwrites data.
	 *
	 * @param {Array} visual_data - The parsed visual_data JSON
	 */
	function merge_visual_layout(visual_data) {
		const visualNodes = new Map(
			(visual_data || []).filter((el) => el.position).map((node) => [node.id, node])
		);
		const visualEdges = new Map(
			(visual_data || [])
				.filter((el) => el.source)
				.map((edge) => [
					`${edge.source}:${edge.target}:${edge.sourceHandle || "default"}`,
					edge,
				])
		);

		// 1. Merge node positions
		const seenNodeIds = new Set();
		const mergedNodes = nodes.value.map((node) => {
			seenNodeIds.add(node.id);
			const visualNode = visualNodes.get(node.id);
			if (!visualNode) return node;

			const {
				position,
				type: _visualType,
				label: _visualLabel,
				id: _visualId,
				data: _visualData,
				...visualNodeMeta
			} = visualNode;

			return {
				...node,
				...visualNodeMeta,
				position: position || node.position,
				data: { ...(node.data || {}) },
				type: node.type,
				label: node.label,
			};
		});

		// 2. Add orphaned visual nodes not in actions
		visualNodes.forEach((vNode, id) => {
			if (!seenNodeIds.has(id)) {
				mergedNodes.push({
					...vNode,
					data: { ...(vNode.data || {}) },
				});
				seenNodeIds.add(id);
			}
		});

		nodes.value = [...mergedNodes];

		// 3. Merge edge metadata
		const seenEdgeKeys = new Set();
		const mergedEdges = edges.value.map((edge) => {
			const key = `${edge.source}:${edge.target}:${edge.sourceHandle || "default"}`;
			seenEdgeKeys.add(key);
			const visualEdge = visualEdges.get(key);
			if (!visualEdge) return edge;

			const {
				id: _vId,
				source: _vSource,
				target: _vTarget,
				sourceHandle: _vSourceHandle,
				data: _vData,
				...visualEdgeMeta
			} = visualEdge;

			return { ...edge, ...visualEdgeMeta, type: "add" };
		});

		// Add orphaned edges with valid endpoints
		visualEdges.forEach((vEdge, key) => {
			if (!seenEdgeKeys.has(key)) {
				if (seenNodeIds.has(vEdge.source) && seenNodeIds.has(vEdge.target)) {
					mergedEdges.push({ ...vEdge, type: "add" });
					seenEdgeKeys.add(key);
				}
			}
		});

		edges.value = [...mergedEdges];
	}

	/**
	 * Initialize a default Trigger → End graph when a Rule has no actions.
	 *
	 * @param {Object} ruleDoc - Rule document
	 */
	function initialize_default_graph(ruleDoc) {
		nodes.value = [
			{
				id: "root",
				type: "start",
				position: { x: 250, y: 50 },
				label: "Start",
				data: {
					action_id: "root",
					action_type: "Entry Action",
					document_type: ruleDoc.document_type,
					trigger_event: ruleDoc.trigger_event,
					trigger_condition: ruleDoc.trigger_condition,
					is_enabled: 1,
				},
			},
			{
				id: "node_end",
				type: "stop",
				position: { x: 250, y: 200 },
				label: "End",
				data: {
					action_id: "node_end",
					action_type: "Stop",
					is_enabled: 1,
					operation: "Success",
				},
			},
		];
		edges.value = [
			{
				id: "edge_root_node_end",
				source: "root",
				target: "node_end",
				sourceHandle: "true",
				type: "add",
				animated: true,
			},
		];
	}

	/**
	 * Paste nodes and edges from clipboard into the current graph.
	 * Remaps IDs to prevent collisions and preserves internal connections.
	 */
	function pasteNodes(pastedNodes, pastedEdges, position = { x: 0, y: 0 }) {
		if (!pastedNodes || !pastedNodes.length) return [];

		const idMap = {};
		const newNodes = [];
		const newEdges = [];

		// 1. Calculate bounding box of pasted nodes to find offset
		const minX = Math.min(...pastedNodes.map((n) => n.position?.x || 0));
		const minY = Math.min(...pastedNodes.map((n) => n.position?.y || 0));

		// 2. Map IDs and create new nodes
		pastedNodes.forEach((node) => {
			const oldId = node.id;
			const newId = generateShortId();
			idMap[oldId] = newId;

			// Deep clone
			const newNode = JSON.parse(JSON.stringify(node));
			newNode.id = newId;
			if (newNode.data) {
				newNode.data.action_id = newId;
				newNode.data.name = null; // Clear backend name to force new record
				// Ensure mandatory fields are at least present
				if (
					newNode.data.action_type === "Document Action" &&
					!newNode.data.permission_audit_reason
				) {
					newNode.data.permission_audit_reason = "System Rule Execution";
				}
			}

			// Shift position relative to paste point
			newNode.position = {
				x: (node.position?.x || 0) - minX + position.x,
				y: (node.position?.y || 0) - minY + position.y,
			};

			newNodes.push(newNode);
		});

		// 3. Remap next_step pointers in node data
		newNodes.forEach((node) => {
			if (node.data) {
				if (node.data.next_step_if_true && idMap[node.data.next_step_if_true]) {
					node.data.next_step_if_true = idMap[node.data.next_step_if_true];
				} else {
					node.data.next_step_if_true = null;
				}

				if (node.data.next_step_if_false && idMap[node.data.next_step_if_false]) {
					node.data.next_step_if_false = idMap[node.data.next_step_if_false];
				} else {
					node.data.next_step_if_false = null;
				}
			}
		});

		// 4. Create new edges for internal connections
		(pastedEdges || []).forEach((edge) => {
			if (idMap[edge.source] && idMap[edge.target]) {
				const newSourceId = idMap[edge.source];
				const newTargetId = idMap[edge.target];
				const newEdgeId = `e-${newSourceId}-${newTargetId}-${
					edge.sourceHandle || "default"
				}`;
				newEdges.push({
					...edge,
					id: newEdgeId,
					source: newSourceId,
					target: newTargetId,
				});
			}
		});

		// 5. Add to store
		nodes.value = [...nodes.value, ...newNodes];
		edges.value = [...edges.value, ...newEdges];

		return newNodes;
	}

	return {
		// State
		nodes,
		edges,

		// Computed
		effectiveDisabledIds,

		// Snapshot
		getStateSnapshot,
		getGraphSnapshot,
		applyGraphSnapshot,

		// Topology
		getTopologicalSort,
		getAvailableVariables,
		getEffectivelyDisabledIds,

		// Node operations
		get_default_node_data,
		delete_node,
		delete_edge,
		touch_node,
		insert_node_on_edge,
		pasteNodes,

		// Sync
		sync_actions_to_graph,
		merge_visual_layout,
		initialize_default_graph,

		// Normalization + cleaning
		normalize_graph_nodes,
		normalize_action_data,
		clean_graph_data,
		clean_action_config,
	};
});
