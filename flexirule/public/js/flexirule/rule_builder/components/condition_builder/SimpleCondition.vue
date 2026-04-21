<script setup>
/**
 * SimpleCondition - Leaf condition editor (left op right)
 * Uses backend-driven operator configuration
 */
import { useStore } from "../../store";
import ControlFactory from "../../controls/ControlFactory.vue";
import MappingWrapper from "../MappingWrapper.vue";
import SelectControl from "../../controls/SelectControl.vue";
import FieldPickerControl from "../../controls/FieldPickerControl.vue";
import { inject, ref, computed, watch } from "vue";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["remove"]);

// Injected operator config from ConditionBuilder
const operatorConfig = inject(
	"operatorConfig",
	ref({ fieldtype_operators: {}, operator_labels: {} })
);

// Dynamic Link State
const dynamicLinkDocType = ref("");

// Find the selected field metadata
const selectedField = computed(() => {
	const ref = props.node.left?.ref;
	if (!ref) return null;
	return props.docFields.find((f) => f.value === ref);
});

const doctypeContextRefs = ["doctype", "rule.document_type", "caller.document_type"];
const isDoctypeContextField = computed(() =>
	doctypeContextRefs.includes(selectedField.value?.value)
);

// Available operators based on field type - backend-driven
const operators = computed(() => {
	const config = operatorConfig.value;
	const ft = selectedField.value?.fieldtype || "Data";
	const fieldOps = selectedField.value?.operators;

	// Get valid operators for this fieldtype
	const validOps =
		Array.isArray(fieldOps) && fieldOps.length
			? fieldOps
			: config.fieldtype_operators?.[ft] ||
			  config.fieldtype_operators?.["_default"] || ["==", "!=", "is_set", "is_not_set"];
	const labels = config.operator_labels || {};

	return validOps.map((op) => ({
		value: op,
		label: __(labels[op] || op),
	}));
});

// Computed Schema for Value Input
const valueFieldSchema = computed(() => {
	if (!selectedField.value) return { fieldtype: "Data" };

	// Helper operators
	if (props.node.op === "has_field") {
		return {
			fieldtype: "Data",
			label: __("DocField"),
			placeholder: __("e.g. customer"),
		};
	}

	let schema = { ...selectedField.value };

	// Use DocType picker for context doctype filters
	if (isDoctypeContextField.value) {
		if (["in", "not in"].includes(props.node.op)) {
			schema = {
				...schema,
				fieldtype: "MultiSelectList",
				options: [],
				get_data: async (txt) => {
					const rows = await frappe.db.get_link_options("DocType", txt || "");
					return (rows || []).map((row) => ({
						value: row.value || row,
						description: row.description || "",
					}));
				},
				placeholder: __("Select DocTypes"),
			};
		} else {
			schema = {
				...schema,
				fieldtype: "Link",
				options: "DocType",
				placeholder: __("Select DocType"),
			};
		}
	}

	// 1. DocStatus Handling
	if (schema.value === "doc.docstatus" || schema.fieldname === "docstatus") {
		schema.fieldtype = "Select";
		schema.options = [
			{ label: __("Draft"), value: 0 },
			{ label: __("Submitted"), value: 1 },
			{ label: __("Cancelled"), value: 2 },
		];
	}

	// 2. Multi-Select Handling for IN/NOT IN
	if (["in", "not in"].includes(props.node.op) && !isDoctypeContextField.value) {
		const originalFieldtype = schema.fieldtype;
		const originalOptions = schema.options;
		schema.fieldtype = "MultiSelect";
		// Check if we need to adjust options for MultiSelect docstatus
		if (schema.fieldname === "docstatus") {
			// For MultiSelect, provide simple options because standard control handles strings best
			schema.options = ["0", "1", "2"];
		} else if (originalFieldtype === "Select" && typeof originalOptions === "string") {
			schema.options = originalOptions
				.split("\n")
				.map((opt) => opt.trim())
				.filter(Boolean);
		}
	}

	// 3. Dynamic Link Handling (Step 2: The actual link picker)
	if (schema.fieldtype === "Dynamic Link") {
		if (dynamicLinkDocType.value) {
			schema.fieldtype = "Link";
			schema.options = dynamicLinkDocType.value;
		} else {
			// If no doctype selected, show Data or ReadOnly
			schema.fieldtype = "Data";
			schema.read_only = 1;
			schema.placeholder = __("Select DocType first");
		}
	}

	return schema;
});

// Wrapped Value for Link/Dynamic Link Tuple handling
const wrappedValue = computed({
	get() {
		const val = props.node.right.value;
		const ft = selectedField.value?.fieldtype;
		const op = props.node.op;

		// If not a Link/Dynamic Link, return raw value
		if ((ft !== "Link" && ft !== "Dynamic Link") || isDoctypeContextField.value) return val;

		// If value is empty, return empty
		if (!val) return op === "in" || op === "not in" ? [] : "";

		// If it's a tuple [DocType, Value], return Value
		if (Array.isArray(val) && val.length === 2 && typeof val[0] === "string") {
			return val[1];
		}

		// Legacy/Fallback: return raw value
		return val;
	},
	set(newVal) {
		const ft = selectedField.value?.fieldtype;

		if ((ft !== "Link" && ft !== "Dynamic Link") || isDoctypeContextField.value) {
			props.node.right.value = newVal;
			return;
		}

		// Determine DocType
		let docType = "";
		if (ft === "Link") {
			docType = selectedField.value.options;
		} else if (ft === "Dynamic Link") {
			docType = dynamicLinkDocType.value;
		}

		if (!docType) {
			// Should not happen if UI is correct, but falback
			props.node.right.value = newVal;
			return;
		}

		// Wrap it: [DocType, Value]
		props.node.right.value = [docType, newVal];
	},
});

// Watch for changes in existing node value to init dynamicLinkDocType if needed
watch(
	() => props.node,
	(newNode) => {
		// Attempt to extract existing Dynamic Link DocType from saved tuple
		if (selectedField.value?.fieldtype === "Dynamic Link" && !dynamicLinkDocType.value) {
			const val = newNode.right?.value;
			if (Array.isArray(val) && val.length === 2 && typeof val[0] === "string") {
				dynamicLinkDocType.value = val[0];
			}
		}
	},
	{ immediate: true, deep: true }
);

function setMapping(ref) {
	props.node.right.ref = ref;
	props.node.right.value = "";
}

function clearMapping() {
	props.node.right.ref = "";
}
</script>

<template>
	<div class="simple-condition">
		<div class="condition-main-row">
			<!-- Field -->
			<div class="condition-col field-col">
				<div class="field-picker-container">
					<FieldPickerControl
						:df="{ label: '', read_only: readOnly }"
						v-model="node.left.ref"
						:fields="docFields"
						:disabled="readOnly"
						class="w-100 m-0"
					/>
				</div>
			</div>

			<!-- Operator -->
			<div class="condition-col operator-col">
				<select v-model="node.op" class="form-control input-xs" :disabled="readOnly">
					<option v-for="op in operators" :key="op.value" :value="op.value">
						{{ op.label }}
					</option>
				</select>
			</div>

			<!-- Value -->
			<div
				class="condition-col value-col"
				v-if="!['is_set', 'is_not_set', 'is_submittable'].includes(node.op)"
			>
				<div v-if="selectedField?.fieldtype === 'Dynamic Link'" class="mb-2">
					<ControlFactory
						:df="{
							fieldtype: 'Link',
							options: 'DocType',
							placeholder: __('Select DocType'),
							read_only: readOnly,
						}"
						v-model="dynamicLinkDocType"
						:hideLabel="true"
					/>
				</div>

				<MappingWrapper
					:label="''"
					:mappingValue="node.right.ref"
					:docFields="docFields"
					:readOnly="readOnly"
					@update:mappingValue="setMapping"
					@clearStatic="clearMapping"
				>
					<ControlFactory
						:df="{ ...valueFieldSchema, label: '' }"
						v-model="wrappedValue"
						:read_only="readOnly"
						:hideLabel="true"
					/>
				</MappingWrapper>
			</div>
			<div v-else class="condition-col value-col empty"></div>

			<!-- Remove -->
			<div class="condition-col action-col" v-if="!readOnly">
				<button class="btn btn-xs btn-link text-danger" @click="emit('remove')">
					<i class="fa fa-trash"></i>
				</button>
			</div>
		</div>
	</div>
</template>

<style scoped>
.simple-condition {
	background: #f8f9fa;
	border: 1px solid #e9ecef;
	border-radius: 4px;
	padding: 6px;
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.simple-condition:hover {
	border-color: #cbd5e1;
}

.condition-main-row {
	display: grid;
	grid-template-columns: 1.5fr 0.8fr 2fr auto;
	gap: 8px;
	align-items: center;
}

.condition-col {
	min-width: 0;
}

.field-picker-container {
	position: relative;
	display: flex;
	align-items: center;
	width: 100%;
}

:deep(.field-picker-control) {
	margin-bottom: 0 !important;
}

:deep(.control.frappe-control) {
	margin-bottom: 0 !important;
}

.condition-main-row :deep(.form-control) {
	height: 28px;
	font-size: 12px;
	padding: 4px 8px;
}

/* Responsive adjustments */
@media (max-width: 992px) {
	.condition-main-row {
		display: flex;
		flex-direction: column;
		gap: 8px;
		align-items: stretch;
	}
	.condition-col {
		width: 100%;
	}
	.action-col {
		align-self: flex-end;
	}
}
</style>
