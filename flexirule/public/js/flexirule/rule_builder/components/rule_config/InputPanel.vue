<template>
	<div class="input-panel" :class="mode">
		<div class="panel-header" v-if="mode === 'config'">
			<h4>{{ __("Setup & Input") }}</h4>
			<p class="text-muted small">{{ __("Define reference and operation") }}</p>
		</div>

		<div class="panel-sections">
			<!-- Configuration Section (Only for 'config' mode) -->
			<div v-if="mode === 'config'" class="panel-section setup-section">
				<div class="setup-controls">
					<ControlFactory
						v-if="showOperation"
						:df="dynamicOperationField"
						:modelValue="node.data?.operation"
						:read_only="readOnly"
						@update:modelValue="updateField('operation', $event)"
					/>

					<!-- Core Identity Fields -->
					<ControlFactory
						v-if="showReferenceDoctype"
						:df="referenceDoctypeField"
						:modelValue="node.data?.reference_doctype"
						:read_only="readOnly"
						@update:modelValue="updateField('reference_doctype', $event)"
					/>

					<ControlFactory
						v-if="showProcessName"
						:df="processNameField"
						:modelValue="node.data?.process_name"
						:read_only="readOnly"
						@update:modelValue="updateField('process_name', $event)"
					/>

					<ControlFactory
						v-if="showRuleField"
						:df="ruleField"
						:modelValue="node.data?.rule"
						:read_only="readOnly"
						@update:modelValue="updateField('rule', $event)"
					/>

					<!-- Secondary Setup -->
					<ControlFactory
						v-if="showReferenceDocname"
						:df="referenceDocnameField"
						:modelValue="node.data?.reference_docname"
						:read_only="readOnly"
						@update:modelValue="updateField('reference_docname', $event)"
					/>

					<ControlFactory
						v-if="showInputSource"
						:df="inputSourceField"
						:modelValue="node.data?.input_source"
						:read_only="readOnly"
						@update:modelValue="updateField('input_source', $event)"
					/>
				</div>
			</div>

			<!-- Available Variables (Always shown in 'variables' mode, optional in 'config') -->
			<div class="panel-section variables-section">
				<div class="section-header">
					<h5 class="section-title">
						{{
							mode === "variables"
								? __("Available Variables")
								: __("Context Variables")
						}}
					</h5>
					<button class="btn btn-xs btn-link" @click="refreshVariables">
						<i class="fa fa-refresh"></i>
					</button>
				</div>
				<div class="variable-search mb-2">
					<div class="input-group input-group-sm">
						<div class="input-group-prepend">
							<span class="input-group-text"><i class="fa fa-search"></i></span>
						</div>
						<input
							type="text"
							class="form-control"
							v-model="searchQuery"
							:placeholder="__('Search variables...')"
						/>
					</div>
				</div>

				<div class="variable-list v2-scrollbar">
					<div v-if="loading" class="text-center p-3">
						<div class="spinner-border spinner-border-sm text-muted"></div>
					</div>
					<template v-else>
						<div
							v-for="v in filteredVariables"
							:key="v.value"
							class="variable-item"
							:title="v.label"
							draggable="true"
							@dragstart="onDragStart($event, v)"
						>
							<span class="variable-label">{{ v.label }}</span>
							<span class="variable-type">{{ v.type || "Data" }}</span>
						</div>
						<div v-if="filteredVariables.length === 0" class="empty-state">
							{{
								searchQuery
									? __("No matching variables")
									: __("No scope variables available")
							}}
						</div>
					</template>
				</div>
			</div>

			<!-- DocType Fields (Only in 'config' mode when a DocType is selected) -->
			<div
				v-if="mode === 'config' && node.data?.reference_doctype"
				class="panel-section doctype-fields-section"
			>
				<h5 class="section-title">
					{{ __("{0} Fields").replace("{0}", node.data.reference_doctype) }}
				</h5>
				<div class="variable-list v2-scrollbar mt-2">
					<div v-if="loadingFields" class="text-center p-2">
						<div class="spinner-border spinner-border-sm text-muted"></div>
					</div>
					<template v-else>
						<div
							v-for="f in doctypeFields"
							:key="f.fieldname"
							class="variable-item field-item"
							:title="f.label"
							draggable="true"
							@dragstart="onDragStart($event, f, true)"
						>
							<span class="variable-label">{{ f.label }}</span>
							<span class="variable-type">{{ f.fieldtype }}</span>
						</div>
					</template>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "../../store";
import { getContract } from "../../../core/contracts.js";
import ControlFactory from "../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
	mode: { type: String, default: "config" }, // 'config' or 'variables'
});

const store = useStore();
const variables = ref([]);
const doctypeFields = ref([]);
const loading = ref(false);
const loadingFields = ref(false);
const searchQuery = ref("");

const contract = computed(() => {
	const type = props.node?.data?.action_type || props.node?.type;
	return type ? getContract(type) : null;
});

const showReferenceDoctype = computed(() => {
	if (!contract.value) return false;
	const fields = contract.value.required_fields || [];
	return (
		fields.includes("reference_doctype") ||
		["Process", "Set Value"].includes(props.node.data?.action_type)
	);
});

const showProcessName = computed(() => {
	return props.node.data?.action_type === "Process";
});

const showRuleField = computed(() => {
	return props.node.data?.action_type === "Sub-Rule";
});

const showOperation = computed(() => {
	if (!contract.value) return false;
	return (
		contract.value?.operation_options ||
		["Notify", "Process", "Query Records", "Create Docs", "Document Action"].includes(
			props.node.data?.action_type
		)
	);
});

const showReferenceDocname = computed(() => {
	const type = props.node.data?.action_type;
	const op = props.node.data?.operation;

	if (type === "Query Records") {
		return ["Query Doc", "Query Report"].includes(op);
	}
	if (type === "Document Action" || type === "Create Docs") {
		return ["Update Existing", "Delete Record"].includes(op);
	}
	if (type === "Process" && op?.includes("Doc")) return true;

	return false;
});

const showInputSource = computed(() => {
	if (!contract.value) return false;
	return ["Query Records", "Create Docs", "Document Action"].includes(
		props.node.data?.action_type
	);
});

const forcedReferenceDoctype = computed(() => {
	if (!["Document Action", "Create Docs"].includes(props.node.data?.action_type)) return null;
	if (props.node.data?.operation === "Add Comment") return "Comment";
	if (props.node.data?.operation === "Create ToDo") return "ToDo";
	return null;
});

// -- Field Definitions --
const referenceDoctypeField = computed(() => {
	let description = __("Target DocType for this action.");
	if (
		["Document Action", "Create Docs"].includes(props.node.data?.action_type) &&
		forcedReferenceDoctype.value
	) {
		description = __("{0} mode always targets the {1} DocType.")
			.replace("{0}", props.node.data.operation)
			.replace("{1}", forcedReferenceDoctype.value);
	}

	return {
		fieldname: "reference_doctype",
		fieldtype: "Link",
		label: __("Reference DocType"),
		options: "DocType",
		reqd: 1,
		read_only: Boolean(forcedReferenceDoctype.value),
		description,
	};
});

const processNameField = {
	fieldname: "process_name",
	fieldtype: "Link",
	label: __("Process"),
	options: "Process",
	reqd: 1,
};

const ruleField = {
	fieldname: "rule",
	fieldtype: "Link",
	label: __("Sub-Rule"),
	options: "Rule",
	reqd: 1,
};

const referenceDocnameField = computed(() => {
	const actionType = props.node?.data?.action_type;
	const operation = props.node?.data?.operation;
	const refDocType = props.node?.data?.reference_doctype;

	// Special case: Query Report
	if (actionType === "Query Records" && operation === "Query Report") {
		return {
			fieldname: "reference_docname",
			fieldtype: "Link",
			label: __("Report Name"),
			options: "Report",
			reqd: 1,
			description: __("Select the report to run."),
		};
	}

	// Dynamic Link for Query Doc or Document Actions
	const isLinkNeeded =
		(actionType === "Query Records" && operation === "Query Doc") ||
		(["Document Action", "Create Docs"].includes(actionType) &&
			["Update Existing", "Delete Record"].includes(operation));

	if (isLinkNeeded && refDocType && refDocType !== "Report") {
		return {
			fieldname: "reference_docname",
			fieldtype: "Link",
			label: __("Reference Name"),
			options: refDocType,
			reqd: 1,
			description: __("Select the {0} record.").replace("{0}", refDocType),
		};
	}

	return {
		fieldname: "reference_docname",
		fieldtype: "Data",
		label: __("Reference Name"),
		description: __("The document name, ID, or an expression."),
	};
});

const inputSourceField = {
	fieldname: "input_source",
	fieldtype: "Select",
	label: __("Input Source"),
	options: "Context Doc\nContext Variable\nBoth",
};

const dynamicOperationField = computed(() => {
	const label = contract.value?.operation_label || __("Operation / Mode");
	const options = contract.value?.operation_options;

	return {
		fieldname: "operation",
		fieldtype: options ? "Select" : "Autocomplete",
		label: label,
		options: options ? options.join("\n") : "",
		reqd: 1,
		get_options: async () => {
			if (props.node.data?.action_type === "Process" && props.node.data?.process_name) {
				const ops = await store.get_process_operations(props.node.data.process_name);
				return ops.map((o) => ({ label: o.label || o.func_name, value: o.func_name }));
			}
			if (options) {
				return options.map((opt) => ({ label: __(opt), value: opt }));
			}
			return [];
		},
	};
});

const filteredVariables = computed(() => {
	if (!searchQuery.value) return variables.value;
	const q = searchQuery.value.toLowerCase();
	return variables.value.filter(
		(v) => v.label.toLowerCase().includes(q) || v.value.toLowerCase().includes(q)
	);
});

function onDragStart(event, item, isField = false) {
	if (event.dataTransfer) {
		const text = isField ? `{{ doc.${item.fieldname} }}` : `{{ ${item.value} }}`;
		event.dataTransfer.setData("text/plain", text);
		event.dataTransfer.setData(
			"application/x-flexirule-variable",
			isField ? `doc.${item.fieldname}` : item.value
		);
		event.dataTransfer.effectAllowed = "copy";
	}
}

async function refreshVariables() {
	if (!props.node?.id) return;
	loading.value = true;
	try {
		variables.value = await store.getAvailableVariables(props.node.id);
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
}

async function loadDoctypeFields() {
	const dt = props.node?.data?.reference_doctype;
	if (!dt) {
		doctypeFields.value = [];
		return;
	}
	loadingFields.value = true;
	try {
		doctypeFields.value = await flexirule.utils.get_doctype_fields(dt);
	} catch (e) {
		doctypeFields.value = [];
	} finally {
		loadingFields.value = false;
	}
}

function updateField(fieldname, value) {
	if (props.node?.data) {
		if (fieldname === "operation") {
			const actionType = props.node.data?.action_type;

			// Handle Document Action / Create Docs special modes
			if (["Document Action", "Create Docs"].includes(actionType)) {
				const isSpecialCreateDocsMode = ["Add Comment", "Create ToDo"].includes(value);
				if (value === "Add Comment") {
					props.node.data.reference_doctype = "Comment";
					props.node.data.reference_docname = null;
				} else if (value === "Create ToDo") {
					props.node.data.reference_doctype = "ToDo";
					props.node.data.reference_docname = null;
				} else if (
					["Comment", "ToDo"].includes(props.node.data.reference_doctype) &&
					["Create New", "Update Existing"].includes(value)
				) {
					props.node.data.reference_doctype = null;
					props.node.data.reference_docname = null;
				}

				if (isSpecialCreateDocsMode) {
					// These modes act on the current context document
					props.node.data.mutation_mode = null;
					props.node.data.return_variable = null;
					props.node.data.return_type = null;
					props.node.data.resolved_output_schema = null;
					props.node.data.output_mapping = null;
				}
			}

			// Handle Query Records -> Query Report special mode
			if (actionType === "Query Records" && value === "Query Report") {
				props.node.data.reference_doctype = "Report";
				props.node.data.reference_docname = null;
			}
		}

		if (
			fieldname === "reference_doctype" &&
			forcedReferenceDoctype.value &&
			value !== forcedReferenceDoctype.value
		) {
			props.node.data.reference_doctype = forcedReferenceDoctype.value;
			store.mark_dirty();
			return;
		}

		props.node.data[fieldname] = value;
		store.mark_dirty();
	}
}

watch(
	() => forcedReferenceDoctype.value,
	(value) => {
		if (!props.node?.data || !value) return;
		if (props.node.data.reference_doctype !== value) {
			props.node.data.reference_doctype = value;
			store.mark_dirty();
		}
	}
);

watch(
	() => props.node?.data?.reference_doctype,
	() => loadDoctypeFields(),
	{ immediate: true }
);

watch(
	() => props.node?.id,
	() => refreshVariables(),
	{ immediate: true }
);

onMounted(() => {
	refreshVariables();
});

defineExpose({
	validate: () => {
		const errors = [];
		if (["Document Action", "Create Docs"].includes(props.node?.data?.action_type)) {
			if (
				props.node.data.operation === "Add Comment" &&
				props.node.data.reference_doctype !== "Comment"
			) {
				errors.push(__("Add Comment mode requires Reference DocType = Comment"));
			}
			if (
				props.node.data.operation === "Create ToDo" &&
				props.node.data.reference_doctype !== "ToDo"
			) {
				errors.push(__("Create ToDo mode requires Reference DocType = ToDo"));
			}
		}
		return { valid: errors.length === 0, errors };
	},
});
</script>

<style scoped>
.input-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: #f8fafc;
}

.panel-header {
	padding: 20px;
	border-bottom: 1px solid var(--border-color);
	background: #fff;
}

.panel-header h4 {
	margin: 0 0 4px 0;
	font-size: 15px;
	font-weight: 600;
}

.panel-sections {
	flex: 1;
	overflow-y: auto;
	padding: 20px;
	display: flex;
	flex-direction: column;
	gap: 24px;
}

.panel-section {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.section-title {
	margin: 0;
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: #64748b;
}

.section-divider {
	height: 1px;
	background: #e2e8f0;
	margin: 4px 0;
}

.variable-list {
	display: flex;
	flex-direction: column;
	gap: 6px;
	max-height: 350px;
	overflow-y: auto;
	padding-right: 4px;
}

.variable-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 12px;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	font-size: 11px;
	cursor: grab;
	transition: all 0.2s;
}

.variable-item:hover {
	border-color: var(--primary);
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	transform: translateX(2px);
}

.variable-label {
	font-weight: 600;
	color: #1e293b;
}

.variable-type {
	font-size: 9px;
	padding: 2px 6px;
	background: #f1f5f9;
	border-radius: 4px;
	color: #64748b;
}

.guide-content {
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 12px;
}

.guide-icon-small {
	width: 24px;
	height: 24px;
	border-radius: 6px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #fff;
	font-size: 12px;
}

.guide-text-small {
	font-size: 12px;
	line-height: 1.5;
	color: #475569;
	margin: 0;
}

.insight-label {
	font-size: 10px;
	font-weight: 700;
	color: var(--primary);
	text-transform: uppercase;
	display: block;
	margin-bottom: 4px;
}

.insight-text {
	font-size: 11px;
	color: #64748b;
	background: #f0f9ff;
	padding: 8px;
	border-radius: 8px;
	border-left: 3px solid var(--primary);
	margin: 0;
}

.v2-scrollbar::-webkit-scrollbar {
	width: 4px;
}
.v2-scrollbar::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 10px;
}

.empty-state {
	padding: 20px;
	text-align: center;
	color: #94a3b8;
	font-size: 11px;
	background: #f8fafc;
	border: 1px dashed #e2e8f0;
	border-radius: 8px;
}
</style>
