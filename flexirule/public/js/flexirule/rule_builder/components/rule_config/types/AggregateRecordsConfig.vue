<template>
	<div class="aggregate-config">
		<div class="config-section section-card">
			<h5>{{ __("Aggregate Records") }}</h5>
			<p class="text-muted small">{{ __("Configure aggregation parameters.") }}</p>
		</div>

		<div class="config-section section-card">
			<ControlFactory
				:df="modeField"
				:modelValue="mode"
				:hideDescription="true"
				@update:modelValue="update_mode"
			/>
		</div>

		<div v-if="!mode" class="alert alert-warning mt-3">
			{{ __("Select an aggregation operation.") }}
		</div>

		<div v-else class="config-section section-card">
			<div class="sub-section section-subcard">
				<ControlFactory
					:df="with_read_only(referenceDoctypeField)"
					:modelValue="props.node?.data?.reference_doctype"
					@update:modelValue="(val) => update_action_field('reference_doctype', val)"
				/>
			</div>

			<div class="sub-section section-subcard">
				<h6>{{ __("Filters") }}</h6>
				<FilterGroup
					:doctype="reference_doctype"
					:modelValue="config.filters"
					:readOnly="readOnly"
					:nodeId="node?.id"
					@update:modelValue="(val) => update_config_key('filters', val)"
				/>
			</div>

			<div class="sub-section section-subcard">
				<template v-if="['sum', 'avg', 'min', 'max'].includes(mode)">
					<div class="field-picker-container">
						<FieldPickerControl
							:df="fieldField"
							:fields="doctype_fields"
							:documentType="reference_doctype"
							:modelValue="config.field"
							:read_only="readOnly"
							:class="{
								'border-warning':
									config.field && !is_field_valid(config.field, doctype_fields),
							}"
							@update:modelValue="(val) => update_config_key('field', val)"
						/>
						<i
							v-if="config.field && !is_field_valid(config.field, doctype_fields)"
							class="fa fa-warning text-warning field-warning-icon"
							:title="__('Field not found in DocType')"
						></i>
					</div>
				</template>
				<template v-else-if="mode === 'group_by'">
					<div class="field-picker-container">
						<FieldPickerControl
							:df="groupByField"
							:fields="doctype_fields"
							:documentType="reference_doctype"
							:modelValue="config.group_by_field"
							:read_only="readOnly"
							:class="{
								'border-warning':
									config.group_by_field &&
									!is_field_valid(config.group_by_field, doctype_fields),
							}"
							@update:modelValue="(val) => update_config_key('group_by_field', val)"
						/>
						<i
							v-if="
								config.group_by_field &&
								!is_field_valid(config.group_by_field, doctype_fields)
							"
							class="fa fa-warning text-warning field-warning-icon"
							:title="__('Field not found in DocType')"
						></i>
					</div>
					<ControlFactory
						:df="with_read_only(aggFunctionField)"
						:modelValue="config.agg_function"
						@update:modelValue="(val) => update_config_key('agg_function', val)"
					/>
					<div class="field-picker-container mt-2">
						<FieldPickerControl
							:df="aggFieldField"
							:fields="doctype_fields"
							:documentType="reference_doctype"
							:modelValue="config.agg_field"
							:read_only="readOnly"
							:class="{
								'border-warning':
									config.agg_field &&
									!is_field_valid(config.agg_field, doctype_fields),
							}"
							@update:modelValue="(val) => update_config_key('agg_field', val)"
						/>
						<i
							v-if="
								config.agg_field &&
								!is_field_valid(config.agg_field, doctype_fields)
							"
							class="fa fa-warning text-warning field-warning-icon"
							:title="__('Field not found in DocType')"
						></i>
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { reactive, ref, computed, watch } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import AutocompleteControl from "../../../controls/AutocompleteControl.vue";
import FieldPickerControl from "../../../controls/FieldPickerControl.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const {
	store,
	config,
	doctype_fields,
	variable_options,
	mode,
	reference_doctype,
	with_read_only,
	strip_expression,
	encode_value,
	parse_value_type,
	sync_config,
	is_field_valid,
	update_action_field,
} = useActionConfig(props);

const filter_rows = ref([]);

const operators = ["=", "!=", ">", ">=", "<", "<=", "in", "not in"];
const value_types = ["Value", "Number", "Boolean", "Variable", "Expression"];

const modeField = computed(() => ({
	fieldname: "operation",
	fieldtype: "Select",
	label: __("Operation"),
	options: "sum\navg\ncount\nmin\nmax\ngroup_by",
	read_only: props.readOnly,
}));

const referenceDoctypeField = computed(() => ({
	fieldname: "reference_doctype",
	fieldtype: "Link",
	label: __("Reference DocType"),
	options: "DocType",
	default: store.rule_doc?.document_type,
	read_only: props.readOnly,
}));

const fieldField = {
	fieldname: "field",
	fieldtype: "Data",
	label: __("Field to Aggregate"),
};

const groupByField = {
	fieldname: "group_by_field",
	fieldtype: "Data",
	label: __("Group By Field"),
};

const aggFunctionField = {
	fieldname: "agg_function",
	fieldtype: "Select",
	label: __("Aggregate Function"),
	options: "count\nsum\navg\nmin\nmax",
};

const aggFieldField = {
	fieldname: "agg_field",
	fieldtype: "Data",
	label: __("Aggregate Field"),
};

const field_map = computed(() => {
	const map = {};
	doctype_fields.value.forEach((f) => {
		map[f.value] = f;
	});
	return map;
});

const variable_set = computed(() => {
	return new Set((variable_options.value || []).map((v) => v.value));
});

function update_mode(value) {
	if (!props.node?.data) return;
	props.node.data.operation = value;
	store.mark_dirty();
}

function update_config_key(key, value) {
	config[key] = value;
	sync_local_config();
}

function sync_local_config() {
	const new_config = {};
	Object.keys(config).forEach((k) => {
		const val = config[k];
		if (val !== undefined && val !== null && val !== "") new_config[k] = val;
	});

	sync_config(new_config);
}

function load_local_config(val) {
	let parsed = {};
	if (typeof val === "string") {
		try {
			parsed = JSON.parse(val);
		} catch (e) {
			parsed = {};
		}
	} else if (val && typeof val === "object") {
		parsed = val;
	}

	Object.keys(config).forEach((k) => delete config[k]);
	Object.assign(config, parsed);

	if (!config.filters) config.filters = [];
}

watch(
	() => props.node?.data?.config,
	(val) => load_local_config(val),
	{ immediate: true }
);

watch(
	() => reference_doctype.value,
	async (val) => {
		if (val) {
			await loadDocMeta(val);
			await load_doctype_fields(val);
			sync_local_config();
		}
	}
);

watch(
	() => config,
	() => {
		sync_local_config();
	},
	{ deep: true }
);

defineExpose({
	validate: () => ({ valid: true }),
});
</script>

<style scoped>
.aggregate-config {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.config-section {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.section-card {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 12px;
	background: var(--bg-light, #fff);
}

.section-subcard {
	border: 1px dashed var(--border-color);
	border-radius: 6px;
	padding: 10px;
}

.sub-section {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.field-picker-container {
	position: relative;
	flex: 1;
	display: flex;
	align-items: center;
}

.field-warning-icon {
	position: absolute;
	right: 10px;
	z-index: 5;
	pointer-events: all;
	cursor: help;
}

:deep(.border-warning .form-control) {
	border-color: var(--orange-500, #ff9800) !important;
	background-color: #fff8f1 !important;
}
</style>
