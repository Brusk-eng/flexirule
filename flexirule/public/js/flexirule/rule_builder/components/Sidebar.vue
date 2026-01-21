<template>
	<div class="rule-sidebar">
		<div class="sidebar-v2-preview" v-if="selectedNode && selectedNode.type !== 'start'">
			<button class="btn btn-xs btn-primary-light w-100" @click="showV2Modal = true">
				<i class="fa fa-flask"></i> {{ __("Try V2 Configuration (Preview)") }}
			</button>
		</div>

		<div class="sidebar-header">
			<h4>{{ sidebar_title }}</h4>
			<button class="btn-close" @click="$emit('close')">×</button>
		</div>

		<div class="sidebar-content" v-if="selectedNode">
			<!-- Start Node: Keep existing behavior -->
			<template v-if="selectedNode.type === 'start'">
				<StartNodeProperties
					:nodeData="selectedNode.data"
					@update:field="update_start_field"
					@open:conditions="showConditionModal = true"
				/>
			</template>

			<!-- Action Nodes: DocField-driven rendering -->
			<template v-else>
				<ActionFieldProperties
					:nodeData="selectedNode.data"
					@update:field="update_action_field"
					@open:conditions="showConditionModal = true"
					@open:config="open_config_dialog"
				/>

				<!-- Delete Button -->
				<hr />
				<button class="btn btn-sm btn-danger w-100" @click="delete_node">
					<i class="fa fa-trash"></i> {{ __("Delete") }}
				</button>
			</template>
		</div>

		<!-- Condition Builder Modal -->
		<Teleport to="body">
			<div v-if="showConditionModal" class="condition-modal-overlay">
				<div class="condition-modal-content">
					<div class="modal-header">
						<h4>{{ __("Condition Builder") }}</h4>
						<button class="btn-close" @click="showConditionModal = false">×</button>
					</div>
					<div class="modal-body">
						<div class="mb-3 d-flex justify-content-end">
							<label class="d-flex align-items-center gap-2" style="cursor: pointer">
								<input type="checkbox" v-model="showOldDoc" />
								<span class="small">{{ __("Show Old Document Fields") }}</span>
							</label>
						</div>
						<ConditionBuilder
							:modelValue="currentConditions"
							:docFields="docFields"
							@update:modelValue="update_conditions"
						/>
					</div>
					<div class="modal-footer">
						<button class="btn btn-primary" @click="save_conditions">
							{{ __("Apply Conditions") }}
						</button>
					</div>
				</div>
			</div>
		</Teleport>

		<!-- V2 Configuration Modal -->
		<RuleConfigModal
			v-if="showV2Modal"
			v-model="showV2Modal"
			:node="selectedNode"
			@save="store.mark_dirty()"
		/>
	</div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from "vue";
import { useStore } from "../store";
import ActionFieldProperties from "./ActionFieldProperties.vue";
import StartNodeProperties from "./StartNodeProperties.vue";
import ConditionBuilder from "./condition_builder/ConditionBuilder.vue";
import RuleConfigModal from "./rule_config/RuleConfigModal.vue";
import { validateConditions } from "./condition_builder/condition_validator.js";

// Ensure ProcessConfigurator is loaded
import "../../core/ProcessConfigurator.js";

const emit = defineEmits(["close"]);
const store = useStore();

// Selected node from store - find the original reference for reactivity
const selectedNode = computed(() => {
	const id = store.selected_id;
	if (!id) return null;
	return (store.nodes || []).find((el) => el.id === id);
});

// Sidebar title
const sidebar_title = computed(() => {
	if (!selectedNode.value) return __("Properties");
	return selectedNode.value.data?.action_label || selectedNode.value.label || __("Properties");
});

// ============================================================
// FIELD UPDATE HANDLERS
// ============================================================

function update_start_field(fieldname, value) {
	if (!selectedNode.value?.data) return;
	selectedNode.value.data[fieldname] = value;
	store.mark_dirty();
}

function update_action_field(fieldname, value) {
	if (!selectedNode.value?.data) return;

	// Special handling for certain fields
	if (fieldname === "action_label") {
		selectedNode.value.label = value;
	}

	// Handle next_step fields - update edges
	if (fieldname === "next_step_if_true" || fieldname === "next_step_if_false") {
		update_edge(fieldname, value);
	}

	// Handle process_name change - reset operation
	if (fieldname === "process_name" && selectedNode.value.data.process_name !== value) {
		selectedNode.value.data.operation = null;
		selectedNode.value.data.config = null;
	}

	// Handle operation change - reset config
	if (fieldname === "operation" && selectedNode.value.data.operation !== value) {
		selectedNode.value.data.config = null;
	}

	// Handle action_type change - update node type
	if (fieldname === "action_type" && selectedNode.value.data.action_type !== value) {
		selectedNode.value.type = value.toLowerCase();
	}

	selectedNode.value.data[fieldname] = value;
	store.mark_dirty();
}

function update_edge(field, newTarget) {
	const nodeId = selectedNode.value.id;
	const handleType =
		field === "next_step_if_true"
			? selectedNode.value.data?.action_type === "Condition"
				? "true"
				: "default"
			: "false";

	// Remove existing edge
	store.edges = store.edges.filter(
		(el) => !(el.source === nodeId && el.sourceHandle === handleType)
	);

	// Add new edge if target specified
	if (newTarget) {
		store.edges.push({
			id: `e-${nodeId}-${newTarget}-${handleType}`,
			source: nodeId,
			target: newTarget,
			sourceHandle: handleType,
		});
	}
}

function delete_node() {
	if (selectedNode.value) {
		store.delete_node(selectedNode.value.id);
		emit("close");
	}
}

// ============================================================
// CONFIG DIALOG
// ============================================================

async function open_config_dialog() {
	const processName = selectedNode.value?.data?.process_name;
	const operationName = selectedNode.value?.data?.operation;

	if (!processName || !operationName) {
		frappe.msgprint(__("Please select a Process and Operation first"));
		return;
	}

	// Use ConfigurableAction (Bridge handles V1 vs V2)
	const action = flexirule.integration.create_configurable_action({
		process_name: processName,
		operation_name: operationName,
		node_data: selectedNode.value?.data,
		document_type: store.rule_doc?.document_type,
		doc_meta: store.raw_meta,
		get_variable_options: async () => {
			return store.getAvailableVariables(selectedNode.value?.id);
		},
	});

	await action.show_dialog({
		on_save: () => {
			store.mark_dirty();
			frappe.show_alert({ message: __("Configuration saved"), indicator: "green" });
		},
	});
}

// ============================================================
// CONDITION BUILDER
// ============================================================

const showV2Modal = ref(false);
const showConditionModal = ref(false);
const currentConditions = ref({});
const showOldDoc = ref(false);

/**
 * Strips ephemeral 'id' fields from the condition tree before saving.
 */
function dehydrate_conditions(tree) {
	if (!tree || typeof tree !== "object") return tree;
	const clean = Array.isArray(tree) ? [...tree] : { ...tree };

	if (clean.id) delete clean.id;

	if (clean.conditions && Array.isArray(clean.conditions)) {
		clean.conditions = clean.conditions.map((c) => dehydrate_conditions(c));
	}

	if (clean.where) {
		clean.where = dehydrate_conditions(clean.where);
	}

	return clean;
}

/**
 * Injects ephemeral 'id' fields into the condition tree for Vue reactivity.
 */
function hydrate_conditions(tree) {
	if (!tree || typeof tree !== "object") return tree;
	const hydrated = Array.isArray(tree) ? [...tree] : { ...tree };

	if (!hydrated.id) {
		hydrated.id = frappe.utils.get_random(12);
	}

	if (hydrated.conditions && Array.isArray(hydrated.conditions)) {
		hydrated.conditions = hydrated.conditions.map((c) => hydrate_conditions(c));
	}

	if (hydrated.where) {
		hydrated.where = hydrate_conditions(hydrated.where);
	}

	return hydrated;
}

const docFields = computed(() => {
	let fields = [...store.doc_fields];

	if (showOldDoc.value) {
		const oldFields = store.doc_fields
			.filter((f) => f.value.startsWith("doc."))
			.map((f) => ({
				...f,
				label: `old_doc.${f.fieldname} (${
					f.label.split("(")[1]?.replace(")", "") || f.label
				})`,
				value: f.value.replace("doc.", "old_doc."),
			}));
		fields = [...fields, ...oldFields];
	}

	return fields.sort((a, b) => a.label.localeCompare(b.label));
});

watch(showConditionModal, (val) => {
	if (val && selectedNode.value?.data) {
		const doctype = selectedNode.value.data.document_type || store.rule_doc?.document_type;
		if (doctype) store.fetch_metadata(doctype);

		let source =
			selectedNode.value.type === "start"
				? selectedNode.value.data.trigger_condition
				: selectedNode.value.data.condition_json;

		let parsed = null;
		if (typeof source === "string" && source.trim()) {
			try {
				parsed = JSON.parse(source);
			} catch (e) {
				parsed = null;
			}
		} else if (typeof source === "object") {
			parsed = source;
		}

		currentConditions.value =
			parsed && (parsed.op || parsed.conditions)
				? hydrate_conditions(parsed)
				: { id: frappe.utils.get_random(12), op: "and", conditions: [] };
	}
});

function update_conditions(val) {
	currentConditions.value = val;
}

function save_conditions() {
	if (!selectedNode.value?.data) return;

	// Validate conditions before saving
	const validation = validateConditions(currentConditions.value, true);
	if (!validation.valid) {
		frappe.msgprint({
			message: validation.message,
			title: __("Validation Error"),
			indicator: "red",
		});
		return;
	}

	// Strip ephemeral IDs before saving
	const cleanConditions = dehydrate_conditions(currentConditions.value);
	const json = JSON.stringify(cleanConditions);

	if (selectedNode.value.type === "start") {
		selectedNode.value.data.trigger_condition = json;
	} else {
		selectedNode.value.data.condition_json = json;
	}

	store.mark_dirty();
	showConditionModal.value = false;
	frappe.show_alert({ message: __("Conditions Updated"), indicator: "green" });
}

// Load Rule Action metadata on mount
onMounted(async () => {
	if (!frappe.get_meta("Rule Action")) {
		await frappe.model.with_doctype("Rule Action");
	}
});
</script>

<style scoped>
.rule-sidebar {
	width: 280px;
	height: 100%;
	display: flex;
	flex-direction: column;
	background: #fff;
}

.sidebar-v2-preview {
	padding: 10px 15px 5px;
	border-bottom: 1px solid var(--border-color);
	background: #f8f9ff;
}

.btn-primary-light {
	background: #eef2ff;
	color: #4f46e5;
	border: 1px solid #e0e7ff;
	font-weight: 600;
	font-size: 11px;
}

.btn-primary-light:hover {
	background: #e0e7ff;
	border-color: #c7d2fe;
}

.sidebar-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 12px 15px;
	border-bottom: 1px solid var(--border-color);
}

.sidebar-header h4 {
	margin: 0;
	font-size: 14px;
	font-weight: 600;
}

.btn-close {
	background: none;
	border: none;
	font-size: 18px;
	cursor: pointer;
	color: var(--text-muted);
	padding: 0;
}

.sidebar-content {
	flex: 1;
	padding: 15px;
	overflow-y: auto;
}

hr {
	margin: 15px 0;
	border: none;
	border-top: 1px solid var(--border-color);
}

.w-100 {
	width: 100%;
}

/* Condition Modal */
.condition-modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background: rgba(0, 0, 0, 0.5);
	z-index: 1050;
	display: flex;
	justify-content: center;
	align-items: flex-start;
	overflow-y: auto;
	padding: 40px 0;
}

.condition-modal-content {
	background: white;
	width: 1200px;
	max-width: 90vw;
	border-radius: 6px;
	box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
	display: flex;
	flex-direction: column;
}

.modal-header {
	padding: 15px;
	border-bottom: 1px solid #eee;
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.modal-body {
	padding: 20px;
}

.modal-footer {
	padding: 15px;
	border-top: 1px solid #eee;
	text-align: right;
	background: #fcfcfc;
}
</style>
