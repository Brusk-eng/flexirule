import { defineStore } from "pinia";

export const useStore = defineStore("rule-builder-store", () => {
	let rule_name = ref(null);
	let rule_doc = ref(null);
	let nodes = ref([]);
	let edges = ref([]);
	let selected_id = ref(null);
	let show_config_modal = ref(false);
	let config_modal_mode = ref("setup"); // "setup" or "logic"
	let processes = ref([]); // File-backed processes
	let available_rules = ref([]);
	let is_dirty = ref(false);
	let initial_state = ref(null);
	let trigger_event_options = ref([]);
	let doc_meta = ref({});
	let fetch_counter = ref(0);
	let meta_loading = computed(() => fetch_counter.value > 0);

	let test_execution_path = ref([]);
	let test_context = ref({});

	const doc_fields = computed(() => {
		const doctype = rule_doc.value?.document_type;
		if (!doctype || !doc_meta.value[doctype]) return [];
		return doc_meta.value[doctype];
	});

	// Raw Frappe meta object for hooks
	const raw_meta = computed(() => {
		const doctype = rule_doc.value?.document_type;
		if (!doctype) return null;
		return frappe.get_meta(doctype);
	});

	const is_read_only = computed(() => {
		return rule_doc.value?.is_active === 1;
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
			const excludedTypes = [
				"Section Break",
				"Column Break",
				"Tab Break",
				"HTML",
				"Button",
				"Image",
				"Fold",
				"Heading",
				"Spacer",
			];

			// 1. Add Main Table Fields (doc.*)
			meta.fields.forEach((f) => {
				if (!excludedTypes.includes(f.fieldtype)) {
					fields.push({
						label: `doc.${f.fieldname} (${f.label})`,
						value: `doc.${f.fieldname}`,
						fieldname: f.fieldname,
						fieldtype: f.fieldtype,
						options: f.options,
						is_main: true,
					});
				}
			});

			// Standard Fields
			const stdFields = [
				{ label: "Name (name)", fieldname: "name", fieldtype: "Data" },
				{ label: "Owner (owner)", fieldname: "owner", fieldtype: "Data" },
				{ label: "Creation (creation)", fieldname: "creation", fieldtype: "Datetime" },
				{ label: "Modified (modified)", fieldname: "modified", fieldtype: "Datetime" },
				{ label: "Modified By (modified_by)", fieldname: "modified_by", fieldtype: "Data" },
				{ label: "DocStatus (docstatus)", fieldname: "docstatus", fieldtype: "Int" },
			];
			stdFields.forEach((f) => {
				fields.push({
					label: `doc.${f.fieldname} (${f.label})`,
					value: `doc.${f.fieldname}`,
					fieldname: f.fieldname,
					fieldtype: f.fieldtype,
					is_std: true,
				});
			});

			// Use spread for deep reactivity
			doc_meta.value = { ...doc_meta.value, [doctype]: fields };

			// 2. Pre-fetch Child Tables metadata
			const tableFields = meta.fields.filter((f) => f.fieldtype === "Table" && f.options);
			for (const tf of tableFields) {
				await fetch_metadata(tf.options);
			}
		} catch (e) {
			// Silent fail - metadata fetch errors are non-critical
		} finally {
			fetch_counter.value--;
		}
	}

	function get_fields_for_doctype(doctype, alias = "doc") {
		if (!doctype) return [];
		if (!doc_meta.value[doctype]) {
			return [];
		}

		return doc_meta.value[doctype].map((f) => ({
			...f,
			label: `${alias}.${f.fieldname} (${
				f.label.split("(")[1] ? f.label.split("(")[1].replace(")", "") : f.label
			})`,
			value: `${alias}.${f.fieldname}`,
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
			args: { doctype: "Rule", name: rule_name.value },
		});

		if (result.message) {
			frappe.model.sync(result.message);
			rule_doc.value = frappe.get_doc("Rule", rule_name.value);
		}

		if (rule_doc.value?.document_type) {
			await fetch_metadata(rule_doc.value.document_type);
		}

		// Load only relevant process adapters in parallel
		const relevantProcesses = new Set();
		if (rule_doc.value?.actions) {
			rule_doc.value.actions.forEach((a) => {
				if (a.process_name) relevantProcesses.add(a.process_name);
			});
		}
		if (relevantProcesses.size > 0) {
			await Promise.all(
				[...relevantProcesses].map((p) => flexirule.utils.load_process_adapter(p))
			);
		}

		if (!trigger_event_options.value.length) {
			await frappe.model.with_doctype("Rule");
			const meta = frappe.get_meta("Rule");
			if (meta && meta.fields) {
				const trigger_field = meta.fields.find((f) => f.fieldname === "trigger_event");
				if (trigger_field && trigger_field.options) {
					trigger_event_options.value = trigger_field.options.split("\n");
				}
			}
		}

		if (!rule_doc.value) {
			frappe.show_alert({ message: __("Rule not found"), indicator: "orange" });
			return;
		}

		await fetch_processes();

		const visual_data = flexirule.utils.safe_json_parse(rule_doc.value.visual_data, null);

		if (visual_data && visual_data.length > 0) {
			nodes.value = visual_data.filter((el) => el.position);
			edges.value = visual_data.filter((el) => el.source);

			// Recovery: Ensure start node exists
			const hasStart = nodes.value.some(
				(n) => n.id === "start" || n.id === "root" || n.type === "start"
			);
			if (!hasStart) {
				console.warn(
					"RuleBuilder: Start node missing in visual_data. Reconstructing from actions."
				);
				sync_actions_to_graph();
			}
		} else if (rule_doc.value.actions && rule_doc.value.actions.length > 0) {
			sync_actions_to_graph();
		} else {
			nodes.value = [
				{
					id: "start",
					type: "start",
					position: { x: 100, y: 100 },
					label: "Start",
					data: {
						document_type: rule_doc.value.document_type,
						trigger_event: rule_doc.value.trigger_event,
						trigger_condition: rule_doc.value.trigger_condition,
						is_enabled: 1,
					},
				},
			];
			edges.value = [];
		}

		setup_breadcrumbs();
		initial_state.value = JSON.stringify(getStateSnapshot());
		is_dirty.value = false;
		commit_history();
	}

	// --- Cascade Disable Logic ---
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

		// BFS to find all reachable ENABLED nodes
		while (queue.length > 0) {
			const currentId = queue.shift();
			// If already visited, skip
			if (visited.has(currentId)) continue;

			// If explicitly disabled (and not start), it blocks path
			const node = nodeMap.get(currentId);
			if (currentId !== "start" && node?.data?.is_enabled === 0) {
				continue; // Don't traverse children
			}

			visited.add(currentId);

			const children = adj.get(currentId) || [];
			children.forEach((childId) => {
				if (!visited.has(childId)) queue.push(childId);
			});
		}

		// All nodes NOT in visited are effectively disabled
		nodes.value.forEach((n) => {
			if (!visited.has(n.id)) disabledSet.add(n.id);
		});

		return disabledSet;
	});

	function getEffectivelyDisabledIds() {
		return effectiveDisabledIds.value;
	}
	// -----------------------------

	function commit_history() {
		const state = JSON.stringify({ nodes: nodes.value, edges: edges.value });
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
			const state = JSON.parse(history.value[history_index.value]);
			nodes.value = state.nodes;
			edges.value = state.edges;
			is_dirty.value = true;
		}
	}

	function redo() {
		if (history_index.value < history.value.length - 1) {
			history_index.value++;
			const state = JSON.parse(history.value[history_index.value]);
			nodes.value = state.nodes;
			edges.value = state.edges;
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
            <li><a href="/app/rule/${rule_name.value}">${__(
			rule_doc.value?.rule_name || rule_name.value
		)}</a></li>
            <li class="disabled"><a href="#">${__("Builder")}</a></li>
        `;
		frappe.breadcrumbs.clear();
		frappe.breadcrumbs.$breadcrumbs.append(breadcrumbs);
	}

	function getStateSnapshot() {
		const nodesSnapshot = nodes.value.map((el) => ({
			id: el.id,
			type: el.type,
			label: el.label,
			data: el.data,
			position: { x: Math.round(el.position.x), y: Math.round(el.position.y) },
		}));
		const edgesSnapshot = edges.value.map((el) => ({
			id: el.id,
			source: el.source,
			target: el.target,
			sourceHandle: el.sourceHandle,
		}));
		return [...nodesSnapshot, ...edgesSnapshot].sort((a, b) => a.id.localeCompare(b.id));
	}

	function checkDirty() {
		if (!initial_state.value) return false;
		return JSON.stringify(getStateSnapshot()) !== initial_state.value;
	}

	function sync_actions_to_graph() {
		const actionNodes = [];
		const actionEdges = [];

		// Check if we have an existing root/entry action
		const rootAction = rule_doc.value.actions.find(
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
					document_type: rule_doc.value.document_type,
					trigger_event: rule_doc.value.trigger_event,
					trigger_condition_expression: rule_doc.value.trigger_condition_expression,
					trigger_condition: rule_doc.value.trigger_condition,
					is_enabled: 1,
				},
			});
		}

		rule_doc.value.actions.forEach((action, index) => {
			const nodeId = action.action_id || `action-${index}`;
			const actionTypeRaw = (action.action_type || "Process").trim();
			let type = actionTypeRaw.toLowerCase();

			const isRoot =
				actionTypeRaw === "Entry Action" || nodeId === "start" || nodeId === "root";

			if (isRoot) {
				type = "start";
			} else if (type === "sub-rule") {
				type = "sub-rule";
			} else if (type === "query records") {
				type = "query";
			} else if (type === "aggregate records") {
				type = "aggregate";
			} else if (type === "create docs") {
				type = "createdoc";
			}

			const nodeLabel = isRoot ? "Start" : action.action_label || `Action ${index + 1}`;
			// Safe JSON parse helper
			const safeParse = (val) => flexirule.utils.safe_json_parse(val);

			const configData = safeParse(action.config || action.method_config);

			const nodeData = {
				action_id: nodeId,
				action_type: action.action_type,
				action_label: action.action_label,
				process_name: action.process_name,
				operation: action.operation,
				config: configData,
				target_field: action.target_field,
				value_template: action.value_template,
				error_template: action.error_template,
				notification_template: action.notification_template,
				notification_type: action.notification_type,
				condition_expression: action.condition_expression,
				condition_json: safeParse(action.condition_json),
				is_enabled: action.is_enabled,
				on_error: action.on_error,
				timeout: action.timeout,
				priority: action.priority,
				retry_count: action.retry_count,
				return_variable: action.return_variable,
				is_async: action.is_async,
				name: action.name,
				input_mapping: safeParse(action.input_mapping),
				output_mapping: safeParse(action.output_mapping),
				rule:
					action.rule ||
					(action.action_type === "Sub-Rule" ? getSubRuleName(configData) : null),
				skip_conditions: action.skip_conditions !== undefined ? action.skip_conditions : 1,
				skip_permissions: action.skip_permissions || 0,
				next_step_if_true: action.next_step_if_true,
				next_step_if_false: action.next_step_if_false,
				// New RC fields
				input_source: action.input_source,
				reference_doctype: action.reference_doctype,
				reference_docname: action.reference_docname,
				mutation_mode: action.mutation_mode,
				return_type: action.return_type,
				resolved_output_schema: safeParse(action.resolved_output_schema),
			};

			if (isRoot) {
				nodeData.document_type = rule_doc.value.document_type;
				nodeData.trigger_event = rule_doc.value.trigger_event;
				nodeData.trigger_condition = rule_doc.value.trigger_condition;
				nodeData.trigger_condition_expression = rule_doc.value.trigger_condition_expression;
				nodeData.priority = rule_doc.value.priority;
				nodeData.execution_mode = rule_doc.value.execution_mode;
				nodeData.max_execution_time = rule_doc.value.max_execution_time;
				nodeData.debug_mode = rule_doc.value.debug_mode;
				nodeData.skip_for_roles = (rule_doc.value.skip_for_roles || [])
					.map((row) => row.role)
					.filter(Boolean);
				nodeData.permissions = (rule_doc.value.permissions || []).map((row) => ({
					role: row.role,
					can_execute: row.can_execute || 0,
					can_edit: row.can_edit || 0,
					can_view: row.can_view || 0,
					can_disable: row.can_disable || 0,
				}));
				nodeData.description = rule_doc.value.description;
				nodeData.is_sub_rule = rule_doc.value.is_sub_rule || 0;
				nodeData.version = rule_doc.value.version;
				nodeData.status = rule_doc.value.status;
				nodeData.previous_rule = rule_doc.value.previous_rule;
				nodeData.is_active = rule_doc.value.is_active;
			}

			actionNodes.push({
				id: nodeId,
				type: type,
				position: {
					x: action.position_x || (isRoot ? 50 : 300),
					y: action.position_y || (isRoot ? 250 : 150 + index * 120),
				},
				label: nodeLabel,
				data: nodeData,
			});
		});

		// Edges
		rule_doc.value.actions.forEach((action, index) => {
			const nodeId = action.action_id || `action-${index}`;
			if (action.next_step_if_true) {
				actionEdges.push({
					id: `e-${nodeId}-${action.next_step_if_true}-true`,
					source: nodeId,
					target: action.next_step_if_true,
					sourceHandle:
						action.action_type === "Condition" || action.action_type === "Loop"
							? "true"
							: "default",
					animated: action.action_type === "Entry Action",
				});
			}
			if (action.next_step_if_false) {
				actionEdges.push({
					id: `e-${nodeId}-${action.next_step_if_false}-false`,
					source: nodeId,
					target: action.next_step_if_false,
					sourceHandle: "false",
				});
			}
		});

		nodes.value = actionNodes;
		edges.value = actionEdges;
	}

	function getSubRuleName(configStr) {
		try {
			return JSON.parse(configStr).rule;
		} catch {
			return null;
		}
	}

	// ============================================================
	// FILE-BACKED PROCESSES
	// ============================================================

	async function fetch_processes() {
		try {
			const response = await frappe.call({
				method: "flexirule.ruleflow.doctype.process.process.get_process_list",
			});
			processes.value = response.message || [];
			// Removed eager loading of all adapters
		} catch (e) {
			processes.value = [];
		}
	}

	async function get_process_operations(process_name) {
		const process = processes.value.find((p) => p.name === process_name);
		const db_ops = process?.operations || [];

		// Get raw operations
		const raw_ops = await flexirule.utils.get_process_operations(process_name, db_ops);

		// Apply eligibility filtering based on current rule context
		const document_type = rule_doc.value?.document_type;
		const doctype_meta = document_type ? frappe.get_meta(document_type) : null;

		return flexirule.utils.filter_eligible_operations(raw_ops, {
			document_type,
			has_doc: true, // Rule Builder always operates in doc context
			doctype_meta: doctype_meta
				? {
						issingle: doctype_meta.issingle,
						istable: doctype_meta.istable,
						is_submittable: doctype_meta.is_submittable,
						track_changes: doctype_meta.track_changes,
						// Add more meta properties as needed
				  }
				: null,
		});
	}

	async function get_operation_config_fields(process_name, operation_name, frm) {
		return await flexirule.utils.get_operation_config_fields(process_name, operation_name, frm);
	}

	async function fetch_available_rules(doctype) {
		if (!doctype) return;
		try {
			const rules = await frappe.db.get_list("Rule", {
				fields: ["name", "rule_name", "trigger_event", "is_active"],
				filters: {
					document_type: doctype,
					name: ["!=", rule_name.value || ""],
				},
				limit: 0,
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
			// 1. Validate mandatory fields
			await frappe.model.with_doctype("Rule Action");
			const action_meta = frappe.get_meta("Rule Action");
			const errors = [];

			// Helper to evaluate dependency
			const eval_depends = (expr, doc) => {
				if (!expr) return true;
				if (typeof expr === "boolean") return expr;
				if (expr.startsWith("eval:")) {
					try {
						return frappe.utils.eval(expr.substr(5), { doc, parent: rule_doc.value });
					} catch (e) {
						return true;
					}
				}
				return !!doc[expr];
			};

			nodes.value.forEach((node) => {
				// Skip Start node validation against Rule Action (it uses Rule fields)
				if (node.type === "start") return;

				// Prevent saving if node is not yet configured (Selector type)
				if (node.type === "selector") {
					errors.push(
						`${label}: ${__("Please configure this action type before saving")}`
					);
					return;
				}

				const doc = node.data;
				const label = node.data.action_label || node.label || node.id;

				action_meta.fields.forEach((df) => {
					// Check if field is applicable (depends_on)
					if (df.depends_on && !eval_depends(df.depends_on, doc)) return;

					// Check mandatory
					const is_mandatory =
						df.reqd ||
						(df.mandatory_depends_on && eval_depends(df.mandatory_depends_on, doc));

					if (is_mandatory) {
						const val = doc[df.fieldname];
						if (val === null || val === undefined || val === "") {
							errors.push(`${label}: ${df.label} is required`);
						}
					}
				});
			});

			if (errors.length > 0) {
				const message = errors.map((e) => `<li>${e}</li>`).join("");
				frappe.msgprint({
					title: __("Validation Error"),
					message: `<ul class="text-left">${message}</ul>`,
					indicator: "red",
				});
				return;
			}

			// 2. Contract Validation: Variable Dependencies and Flow Constraints
			// Build operation metadata from loaded processes
			const op_metadata =
				flexirule.validation?.build_operation_metadata?.(processes.value) || {};

			// Prepare actions in topological order for validation
			const sortedNodesForValidation = getTopologicalSort(nodes.value, edges.value);
			const actionsForValidation = sortedNodesForValidation.map((node) => ({
				action_id: node.data?.action_id || node.id,
				action_type:
					node.type === "start" ? "Entry Action" : node.data?.action_type || "Process",
				action_label: node.data?.action_label || node.label || node.id,
				process_name: node.data?.process_name,
				operation: node.data?.operation,
				is_enabled: node.data?.is_enabled !== undefined ? node.data.is_enabled : 1,
				return_variable: node.data?.return_variable,
				return_type: node.data?.return_type,
				resolved_output_schema: node.data?.resolved_output_schema,
				mutation_mode: node.data?.mutation_mode,
				condition_json: node.data?.condition_json,
				condition_expression: node.data?.condition_expression,
				rule: node.data?.rule,
				config: node.data?.config,
				input_variables: node.data?.input_variables,
				name: node.data?.name,
			}));

			// Validate variable dependencies
			if (flexirule.validation?.validate_variable_dependencies) {
				const varResult = flexirule.validation.validate_variable_dependencies(
					actionsForValidation,
					op_metadata
				);
				if (!varResult.valid) {
					const message = varResult.errors.map((e) => `<li>${e}</li>`).join("");
					frappe.msgprint({
						title: __("Variable Dependency Error"),
						message: `<ul class="text-left">${message}</ul>`,
						indicator: "red",
					});
					return;
				}
				// Show warnings if any
				if (varResult.warnings.length > 0) {
					console.warn("Variable validation warnings:", varResult.warnings);
				}
			}

			// Validate flow constraints (is_terminal, writes_to)
			if (flexirule.validation?.validate_flow_constraints) {
				const edgesForValidation = edges.value.map((e) => ({
					source: e.source,
					target: e.target,
				}));
				const flowResult = flexirule.validation.validate_flow_constraints(
					actionsForValidation,
					op_metadata,
					edgesForValidation
				);
				if (!flowResult.valid) {
					const message = flowResult.errors.map((e) => `<li>${e}</li>`).join("");
					frappe.msgprint({
						title: __("Flow Constraint Error"),
						message: `<ul class="text-left">${message}</ul>`,
						indicator: "red",
					});
					return;
				}
				// Show warnings for side-effects
				if (flowResult.warnings.length > 0) {
					// For now just skip logging, could show as toast or info dialog
				}
			}

			// Validate action type-specific constraints (Sub-Rule, Condition, Loop, Switch, return_variable)
			if (flexirule.validation?.validate_action_types) {
				const typeResult = flexirule.validation.validate_action_types(
					actionsForValidation,
					op_metadata,
					rule_name.value
				);
				if (!typeResult.valid) {
					const message = typeResult.errors.map((e) => `<li>${e}</li>`).join("");
					frappe.msgprint({
						title: __("Action Configuration Error"),
						message: `<ul class="text-left">${message}</ul>`,
						indicator: "red",
					});
					return;
				}
				if (typeResult.warnings.length > 0) {
					console.warn("Action type warnings:", typeResult.warnings);
				}
			}

			// 3. Prepare doc for save
			const fresh = await frappe.call({
				method: "frappe.client.get",
				args: { doctype: "Rule", name: rule_name.value },
			});

			const currentIsActive = rule_doc.value.is_active;
			frappe.model.sync(fresh.message);
			let doc = frappe.get_doc("Rule", rule_name.value);
			doc.is_active = currentIsActive;
			doc.visual_data = JSON.stringify(clean_graph_data());

			const startNode = nodes.value.find((el) => el.type === "start");
			doc.trigger_condition_expression =
				startNode?.data?.trigger_condition_expression || null;
			doc.trigger_condition = startNode?.data?.trigger_condition || null;
			if (startNode?.data) {
				doc.priority = startNode.data.priority ?? doc.priority;
				doc.execution_mode = startNode.data.execution_mode || doc.execution_mode;
				doc.max_execution_time =
					startNode.data.max_execution_time !== undefined
						? startNode.data.max_execution_time
						: doc.max_execution_time;
				doc.debug_mode = startNode.data.debug_mode ? 1 : 0;
				doc.description = startNode.data.description;
				doc.is_sub_rule = startNode.data.is_sub_rule ? 1 : 0;
				const skip_roles = Array.isArray(startNode.data.skip_for_roles)
					? startNode.data.skip_for_roles
					: [];
				doc.skip_for_roles = skip_roles.filter(Boolean).map((role) => ({ role: role }));
				const perms = Array.isArray(startNode.data.permissions)
					? startNode.data.permissions
					: [];
				doc.permissions = perms
					.filter((row) => row && row.role)
					.map((row) => ({
						role: row.role,
						can_execute: row.can_execute ? 1 : 0,
						can_edit: row.can_edit ? 1 : 0,
						can_view: row.can_view ? 1 : 0,
						can_disable: row.can_disable ? 1 : 0,
					}));
			}

			// Sort nodes but ensure Entry Action is processed
			const edgesList = edges.value;

			// Re-use topological sort
			const orderedNodes = getTopologicalSort(nodes.value, edgesList);

			doc.actions = orderedNodes.map((node, idx) => {
				const outgoing = edgesList.filter((e) => e.source === node.id);
				// Loop/Condition use 'default'/'true' for True path
				const true_edge = outgoing.find(
					(e) => e.sourceHandle === "true" || e.sourceHandle === "default"
				);
				const false_edge = outgoing.find((e) => e.sourceHandle === "false");
				const incoming = edgesList.find((e) => e.target === node.id);

				// Determine Entry Action status
				const is_start_node = node.type === "start";
				const action_type = is_start_node
					? "Entry Action"
					: node.data?.action_type === "Sub-rule"
					? "Sub-Rule"
					: node.data?.action_type || "Process";

				// Parent ID logic
				let prev_action_id = null;
				if (!is_start_node && incoming) {
					const parentNode = nodes.value.find((n) => n.id === incoming.source);
					prev_action_id =
						parentNode?.data?.action_id || parentNode?.id || incoming.source;
				}

				return {
					name: node.data?.name,
					idx: idx + 1,
					action_id: node.data?.action_id || node.id,
					action_label: node.data?.action_label || node.label,
					is_entry_action: is_start_node ? 1 : 0,
					prev_action_id: prev_action_id,
					action_type: action_type,
					is_enabled: node.data?.is_enabled !== undefined ? node.data.is_enabled : 1,
					process_name: node.data?.process_name,
					operation: node.data?.operation,
					config:
						node.data?.config && typeof node.data.config !== "string"
							? JSON.stringify(node.data.config)
							: node.data?.config,
					target_field: node.data?.target_field,
					value_template: node.data?.value_template,
					error_template: node.data?.error_template,
					notification_template: node.data?.notification_template,
					notification_type: node.data?.notification_type,
					condition_expression: node.data?.condition_expression,
					condition_json:
						node.data?.condition_json && typeof node.data.condition_json !== "string"
							? JSON.stringify(node.data.condition_json)
							: node.data?.condition_json,
					input_mapping:
						node.data?.input_mapping && typeof node.data.input_mapping !== "string"
							? JSON.stringify(node.data.input_mapping)
							: node.data?.input_mapping,
					output_mapping:
						node.data?.output_mapping && typeof node.data.output_mapping !== "string"
							? JSON.stringify(node.data.output_mapping)
							: node.data?.output_mapping,
					on_error: node.data?.on_error || "Stop",
					timeout: node.data?.timeout || 30,
					priority: node.data?.priority || 0,
					retry_count: node.data?.retry_count || 0,
					return_variable: node.data?.return_variable,
					rule: node.data?.rule,
					is_async: node.data?.is_async || 0,
					skip_conditions:
						node.data?.skip_conditions !== undefined ? node.data.skip_conditions : 1,
					skip_permissions: node.data?.skip_permissions || 0,
					next_step_if_true: true_edge?.target || null,
					next_step_if_false: false_edge?.target || null,
					position_x: Math.round(node.position.x),
					position_y: Math.round(node.position.y),
					// New RC fields
					input_source: node.data?.input_source,
					reference_doctype: node.data?.reference_doctype,
					reference_docname: node.data?.reference_docname,
					mutation_mode: node.data?.mutation_mode,
					return_type: node.data?.return_type,
					resolved_output_schema:
						node.data?.resolved_output_schema &&
						typeof node.data.resolved_output_schema !== "string"
							? JSON.stringify(node.data.resolved_output_schema)
							: node.data?.resolved_output_schema,
				};
			});

			await frappe.call({ method: "frappe.client.save", args: { doc } });
			frappe.toast(__("Saved"));
			await fetch();
			clear_dirty();
		} catch (e) {
			console.error("FlexiRule: Save failed", e);
			const errorMsg =
				e.message || (typeof e === "string" ? e : __("Unknown error occurred during save"));
			frappe.msgprint({
				title: __("Critical Error"),
				message: errorMsg,
				indicator: "red",
			});
		} finally {
			frappe.dom.unfreeze();
		}
	}

	function clean_graph_data() {
		return [...nodes.value, ...edges.value].map((el) => {
			const { selected, dragging, resizing, sourceNode, targetNode, ...obj } = el;
			// Normalize action_type casing
			if (obj.data?.action_type === "Sub-rule") {
				obj.data.action_type = "Sub-Rule";
			}
			return obj;
		});
	}

	function delete_node(nodeId) {
		if (is_read_only.value) {
			frappe.msgprint(__("Cannot edit active rule. Please switch to Draft mode."));
			return;
		}
		const node = nodes.value.find((el) => el.id === nodeId);
		if (
			nodeId === "start" ||
			nodeId === "root" ||
			node?.type === "start" ||
			node?.data?.action_type === "Entry Action"
		) {
			frappe.msgprint(__("Cannot delete start node"));
			return;
		}
		nodes.value = nodes.value.filter((el) => el.id !== nodeId);
		edges.value = edges.value.filter((el) => el.source !== nodeId && el.target !== nodeId);
		if (selected_id.value === nodeId) selected_id.value = null;
		mark_dirty();
	}

	function delete_edge(edgeId) {
		if (is_read_only.value) return;
		const edge = edges.value.find((el) => el.id === edgeId);
		if (!edge) return;

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

		// Remove the edge
		edges.value = edges.value.filter((el) => el.id !== edgeId);
		mark_dirty();
	}

	function getTopologicalSort(nodes, edges) {
		const adj = {};
		const processed = new Set();
		const result = [];
		nodes.forEach((n) => (adj[n.id] = []));
		edges.forEach((e) => {
			if (adj[e.source]) adj[e.source].push(e.target);
		});
		const entryNode = nodes.find(
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
				const childNode = nodes.find((n) => n.id === childId);
				if (childNode && !processed.has(childId)) {
					processed.add(childId);
					result.push(childNode);
				}
			});
		}
		nodes.forEach((n) => {
			if (!processed.has(n.id)) result.push(n);
		});
		return result;
	}

	async function getAvailableVariables(upToNodeId = null) {
		const ruleDoc = rule_doc.value || {};
		const doctype = ruleDoc.document_type;

		// Collect variables from previous nodes
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
				type: "Data", // In the future, we can resolve actual type
			});
		}

		return await flexirule.utils.get_combined_fields(doctype, context_vars, "doc");
	}

	function set_test_result(path, context) {
		test_execution_path.value = path || [];
		test_context.value = context || {};
	}

	function clear_test_result() {
		test_execution_path.value = [];
		test_context.value = {};
	}

	function next_config_node() {
		if (!selected_id.value) return;
		const currentIndex = nodes.value.findIndex((n) => n.id === selected_id.value);
		if (currentIndex === -1) return;

		let nextIndex = (currentIndex + 1) % nodes.value.length;
		selected_id.value = nodes.value[nextIndex].id;
	}

	function prev_config_node() {
		if (!selected_id.value) return;
		const currentIndex = nodes.value.findIndex((n) => n.id === selected_id.value);
		if (currentIndex === -1) return;

		let prevIndex = (currentIndex - 1 + nodes.value.length) % nodes.value.length;
		selected_id.value = nodes.value[prevIndex].id;
	}

	return {
		rule_name,
		rule_doc,
		nodes,
		edges,
		selected_id,
		show_config_modal,
		config_modal_mode,
		next_config_node,
		prev_config_node,
		processes,
		available_rules,
		is_dirty,
		effectiveDisabledIds,
		trigger_event_options,
		doc_fields,
		doc_meta,
		raw_meta,
		meta_loading,
		test_execution_path,
		test_context,
		fetch,
		fetch_metadata,
		get_fields_for_doctype,
		save_changes,
		mark_dirty,
		mark_position_change,
		clear_dirty,
		delete_node,
		delete_edge,
		getEffectivelyDisabledIds,
		fetch_available_rules,
		fetch_processes,
		get_process_operations,
		get_operation_config_fields,
		undo,
		redo,
		can_undo,
		can_redo,
		commit_history,
		getAvailableVariables,
		is_read_only,
		set_test_result,
		clear_test_result,
	};
});
