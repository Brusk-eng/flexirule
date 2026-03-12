<template>
	<div class="action-settings-card section-card">
		<h6 class="text-muted mb-3">{{ __("Action Settings") }}</h6>
		<div class="action-settings-grid">
			<div class="grid-item span-2" v-if="showDoctype">
				<ControlFactory
					:df="with_read_only(referenceDoctypeField)"
					:modelValue="node.data?.reference_doctype"
					@update:modelValue="(val) => update_action_field('reference_doctype', val)"
				/>
			</div>
			<div class="grid-item span-2" v-if="showDocname">
				<ControlFactory
					:df="with_read_only(referenceDocnameField)"
					:modelValue="node.data?.reference_docname"
					@update:modelValue="(val) => update_action_field('reference_docname', val)"
				/>
			</div>
			<div class="grid-item">
				<ControlFactory
					:df="with_read_only(inputSourceField)"
					:modelValue="node.data?.input_source"
					@update:modelValue="(val) => update_action_field('input_source', val)"
				/>
			</div>
			<div class="grid-item">
				<ControlFactory
					:df="with_read_only(mutationModeField)"
					:modelValue="node.data?.mutation_mode"
					@update:modelValue="(val) => update_action_field('mutation_mode', val)"
				/>
			</div>
			<div class="grid-item span-2">
				<ControlFactory
					:df="with_read_only(returnTypeField)"
					:modelValue="node.data?.return_type"
					@update:modelValue="(val) => update_action_field('return_type', val)"
				/>
			</div>
			<div class="grid-item span-2">
				<ControlFactory
					:df="with_read_only(returnVariableField)"
					:modelValue="node.data?.return_variable"
					@update:modelValue="(val) => update_action_field('return_variable', val)"
				/>
			</div>
			<div
				class="grid-item span-2"
				v-if="node.data?.return_type && node.data?.return_type !== 'Boolean'"
			>
				<ControlFactory
					:df="with_read_only(resolvedSchemaField)"
					:modelValue="serializeSchema(node.data?.resolved_output_schema)"
					@update:modelValue="(val) => update_action_field('resolved_output_schema', val)"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import ControlFactory from "../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
	showDoctype: { type: Boolean, default: true },
	showDocname: { type: Boolean, default: false },
});

const emit = defineEmits(["update:field"]);

function with_read_only(field) {
	return { ...field, read_only: props.readOnly };
}

function update_action_field(fieldname, value) {
	emit("update:field", { fieldname, value });
}

const referenceDoctypeField = {
	fieldname: "reference_doctype",
	fieldtype: "Link",
	label: __("Reference DocType"),
	options: "DocType",
	reqd: 1,
};

const referenceDocnameField = {
	fieldname: "reference_docname",
	fieldtype: "Data",
	label: __("Reference Document"),
	description: __("Optional static document name."),
};

const inputSourceField = {
	fieldname: "input_source",
	fieldtype: "Select",
	label: __("Input Source"),
	options: "Context Doc\nContext Variable\nBoth",
};

const mutationModeField = {
	fieldname: "mutation_mode",
	fieldtype: "Select",
	label: __("Mutation Mode"),
	options:
		"Set Doc Field\nUpdate Doc Field\nSet Context Variable\nUpdate Context Variable\nAppend to Context Variable\nBatch Database Set",
};

const returnTypeField = {
	fieldname: "return_type",
	fieldtype: "Select",
	label: __("Return Type"),
	options: "\nBoolean\nDict\nList\nList of Dict\nDoc as Dict",
};

const returnVariableField = computed(() => ({
	fieldname: "return_variable",
	fieldtype: "Data",
	label: __("Return Variable Name"),
	description:
		props.node.data?.return_type === "Boolean"
			? __("Value will be assigned directly to this variable.")
			: __("Result will be stored in this variable name."),
}));

const resolvedSchemaField = {
	fieldname: "resolved_output_schema",
	fieldtype: "Code",
	label: __("Resolved Output Schema"),
	options: "JSON",
	description: __(
		'Return keys schema: [{"fieldname": "...", "fieldtype": "...", "label": "..."}]'
	),
};

function serializeSchema(val) {
	if (!val) return "[]";
	if (typeof val === "string") return val;
	try {
		return JSON.stringify(val, null, 2);
	} catch (e) {
		return "[]";
	}
}
</script>

<style scoped>
.action-settings-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

.grid-item.span-2 {
	grid-column: 1 / -1;
}

.section-card {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 16px;
	background: var(--bg-light, #fff);
	margin-bottom: 16px;
}
</style>
