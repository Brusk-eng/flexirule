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
				<h6>{{ __("Filters") }}</h6>
				<div class="table-rows">
					<div v-for="(row, idx) in filter_rows" :key="idx" class="row-item">
						<FieldPickerControl
							:df="{ label: '' }"
							:fields="doctype_fields"
							:documentType="reference_doctype"
							:modelValue="row.field"
							:read_only="readOnly"
							@update:modelValue="(val) => (row.field = val)"
						/>
						<select
							class="form-control input-xs"
							v-model="row.operator"
							:disabled="readOnly"
							@change="sync_local_config"
						>
							<option v-for="op in operators" :key="op" :value="op">
								{{ op }}
							</option>
						</select>
						<div class="value-cell">
							<template v-if="row.value_type === 'Variable'">
								<AutocompleteControl
									:df="{ fieldtype: 'Autocomplete', label: '' }"
									:options="variable_options"
									:modelValue="row.value"
									:read_only="readOnly"
									:hideLabel="true"
									@update:modelValue="(val) => (row.value = val)"
								/>
							</template>
							<template v-else-if="row.value_type === 'Expression'">
								<input
									class="form-control input-xs"
									v-model="row.value"
									:placeholder="__('Expression')"
									:disabled="readOnly"
									@change="sync_local_config"
								/>
							</template>
							<template v-else>
								<ControlFactory
									:df="value_field_df(row)"
									:modelValue="row.value"
									:hideLabel="true"
									:hideDescription="true"
									@update:modelValue="(val) => (row.value = val)"
								/>
							</template>
						</div>
						<select
							class="form-control input-xs"
							v-model="row.value_type"
							:disabled="readOnly"
							@change="sync_local_config"
						>
							<option v-for="vt in value_types" :key="vt" :value="vt">
								{{ __(vt) }}
							</option>
						</select>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link text-danger"
							@click="remove_filter(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="add_filter">
						<i class="fa fa-plus"></i> {{ __("Add Filter") }}
					</button>
				</div>
			</div>

			<div class="sub-section section-subcard">
				<template v-if="['sum', 'avg', 'min', 'max'].includes(mode)">
					<FieldPickerControl
						:df="fieldField"
						:fields="doctype_fields"
						:documentType="reference_doctype"
						:modelValue="config.field"
						:read_only="readOnly"
						@update:modelValue="(val) => update_config_key('field', val)"
					/>
				</template>
				<template v-else-if="mode === 'group_by'">
					<FieldPickerControl
						:df="groupByField"
						:fields="doctype_fields"
						:documentType="reference_doctype"
						:modelValue="config.group_by_field"
						:read_only="readOnly"
						@update:modelValue="(val) => update_config_key('group_by_field', val)"
					/>
					<ControlFactory
						:df="with_read_only(aggFunctionField)"
						:modelValue="config.agg_function"
						@update:modelValue="(val) => update_config_key('agg_function', val)"
					/>
					<FieldPickerControl
						:df="aggFieldField"
						:fields="doctype_fields"
						:documentType="reference_doctype"
						:modelValue="config.agg_field"
						:read_only="readOnly"
						@update:modelValue="(val) => update_config_key('agg_field', val)"
					/>
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

function add_filter() {
	filter_rows.value.push({ field: "", operator: "=", value: "", value_type: "Value" });
}

function remove_filter(idx) {
	filter_rows.value.splice(idx, 1);
	sync_local_config();
}

function value_field_df(row) {
	let fieldtype = "Data";
	let options = null;
	if (row.value_type === "Number") fieldtype = "Float";
	else if (row.value_type === "Boolean") fieldtype = "Check";
	else if (row.field && field_map.value[row.field]) {
		fieldtype = field_map.value[row.field].fieldtype || "Data";
		options = field_map.value[row.field].options || null;
	}
	return {
		fieldname: "value",
		fieldtype,
		options,
		read_only: props.readOnly,
	};
}

function build_filters() {
	const filters = {};
	filter_rows.value.forEach((row) => {
		if (!row.field) return;
		let val = encode_value(row);
		if (["in", "not in"].includes(row.operator) && typeof val === "string") {
			val = val
				.split(",")
				.map((v) => v.trim())
				.filter((v) => v);
		}
		if (row.operator && row.operator !== "=") {
			filters[row.field] = [row.operator, val];
		} else {
			filters[row.field] = val;
		}
	});
	return filters;
}

function sync_local_config() {
	const new_config = {};
	Object.keys(config).forEach((k) => {
		const val = config[k];
		if (val !== undefined && val !== null && val !== "") new_config[k] = val;
	});

	const filters = build_filters();
	if (Object.keys(filters).length) new_config.filters = filters;

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

	const filters = parsed.filters || {};
	filter_rows.value = Object.entries(filters).map(([field, val]) => {
		let operator = "=";
		let value = val;
		if (Array.isArray(val) && val.length === 2 && operators.includes(val[0])) {
			operator = val[0];
			value = val[1];
		}
		return {
			field,
			operator,
			value: strip_expression(value),
			value_type: parse_value_type(value, variable_set.value),
		};
	});
}

watch(
	() => props.node?.data?.config,
	(val) => load_local_config(val),
	{ immediate: true }
);

watch(
	() => [filter_rows.value, config],
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

.table-rows {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.row-item {
	display: grid;
	grid-template-columns: 1.6fr 0.8fr 1.6fr 0.8fr auto;
	gap: 6px;
	align-items: center;
}

.value-cell :deep(.control-factory) {
	width: 100%;
}
</style>
