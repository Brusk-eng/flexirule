<template>
	<div class="aggregate-config">
		<div class="config-section">
			<h5>{{ __("Aggregate Records") }}</h5>
			<p class="text-muted small">{{ __("Configure aggregation parameters.") }}</p>
		</div>

		<div class="config-section">
			<ControlFactory
				:df="modeField"
				:modelValue="mode"
				:hideDescription="true"
				@update:modelValue="updateMode"
			/>
		</div>

		<div class="config-section">
			<h6 class="text-muted">{{ __("Action Settings") }}</h6>
			<ControlFactory
				:df="withReadOnly(referenceDoctypeField)"
				:modelValue="props.node?.data?.reference_doctype"
				@update:modelValue="(val) => updateActionField('reference_doctype', val)"
			/>
			<ControlFactory
				:df="withReadOnly(inputSourceField)"
				:modelValue="props.node?.data?.input_source"
				@update:modelValue="(val) => updateActionField('input_source', val)"
			/>
			<ControlFactory
				:df="withReadOnly(mutationModeField)"
				:modelValue="props.node?.data?.mutation_mode"
				@update:modelValue="(val) => updateActionField('mutation_mode', val)"
			/>
		</div>

		<div v-if="!mode" class="alert alert-warning mt-3">
			{{ __("Select an aggregation operation.") }}
		</div>

		<div v-else class="config-section">
			<div class="sub-section">
				<h6>{{ __("Filters") }}</h6>
				<div class="table-rows">
					<div v-for="(row, idx) in filterRows" :key="idx" class="row-item">
						<FieldPickerControl
							:df="{ label: '' }"
							:fields="doctypeFields"
							:documentType="referenceDoctype"
							:modelValue="row.field"
							:read_only="readOnly"
							@update:modelValue="(val) => (row.field = val)"
						/>
						<select
							class="form-control input-xs"
							v-model="row.operator"
							:disabled="readOnly"
							@change="syncConfig"
						>
							<option v-for="op in operators" :key="op" :value="op">
								{{ op }}
							</option>
						</select>
						<div class="value-cell">
							<template v-if="row.value_type === 'Variable'">
								<AutocompleteControl
									:df="{ fieldtype: 'Autocomplete', label: '' }"
									:options="variableOptions"
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
									@change="syncConfig"
								/>
							</template>
							<template v-else>
								<ControlFactory
									:df="valueFieldDf(row)"
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
							@change="syncConfig"
						>
							<option v-for="vt in valueTypes" :key="vt" :value="vt">
								{{ __(vt) }}
							</option>
						</select>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link text-danger"
							@click="removeFilter(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addFilter">
						<i class="fa fa-plus"></i> {{ __("Add Filter") }}
					</button>
				</div>
			</div>

			<div class="sub-section">
				<template v-if="['sum', 'avg', 'min', 'max'].includes(mode)">
					<FieldPickerControl
						:df="fieldField"
						:fields="doctypeFields"
						:documentType="referenceDoctype"
						:modelValue="config.field"
						:read_only="readOnly"
						@update:modelValue="(val) => updateConfigKey('field', val)"
					/>
				</template>
				<template v-else-if="mode === 'group_by'">
					<FieldPickerControl
						:df="groupByField"
						:fields="doctypeFields"
						:documentType="referenceDoctype"
						:modelValue="config.group_by_field"
						:read_only="readOnly"
						@update:modelValue="(val) => updateConfigKey('group_by_field', val)"
					/>
					<ControlFactory
						:df="withReadOnly(aggFunctionField)"
						:modelValue="config.agg_function"
						@update:modelValue="(val) => updateConfigKey('agg_function', val)"
					/>
					<FieldPickerControl
						:df="aggFieldField"
						:fields="doctypeFields"
						:documentType="referenceDoctype"
						:modelValue="config.agg_field"
						:read_only="readOnly"
						@update:modelValue="(val) => updateConfigKey('agg_field', val)"
					/>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { reactive, ref, computed, watch } from "vue";
import { useStore } from "../../../store";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();
const config = reactive({});
const filterRows = ref([]);
const doctypeFields = ref([]);
const variableOptions = ref([]);

const mode = computed(() => props.node?.data?.operation || "");
const referenceDoctype = computed(() => props.node?.data?.reference_doctype || "");

const operators = ["=", "!=", ">", ">=", "<", "<=", "in", "not in"];
const valueTypes = ["Value", "Number", "Boolean", "Variable", "Expression"];

const modeField = computed(() => ({
	fieldname: "operation",
	fieldtype: "Select",
	label: __("Operation"),
	options: "sum\navg\ncount\nmin\nmax\ngroup_by",
	read_only: props.readOnly,
}));

const referenceDoctypeField = {
	fieldname: "reference_doctype",
	fieldtype: "Link",
	label: __("Reference DocType"),
	options: "DocType",
	reqd: 1,
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

const fieldMap = computed(() => {
	const map = {};
	doctypeFields.value.forEach((f) => {
		map[f.value] = f;
	});
	return map;
});

const variableSet = computed(() => {
	return new Set((variableOptions.value || []).map((v) => v.value));
});

function withReadOnly(field) {
	return { ...field, read_only: props.readOnly };
}

function updateMode(value) {
	if (!props.node?.data) return;
	props.node.data.operation = value;
	store.mark_dirty();
}

function updateActionField(fieldname, value) {
	if (!props.node?.data) return;
	props.node.data[fieldname] = value;
	store.mark_dirty();
}

function updateConfigKey(key, value) {
	config[key] = value;
	syncConfig();
}

function addFilter() {
	filterRows.value.push({ field: "", operator: "=", value: "", value_type: "Value" });
}

function removeFilter(idx) {
	filterRows.value.splice(idx, 1);
	syncConfig();
}

function parseValueType(val) {
	if (typeof val === "number") return "Number";
	if (typeof val === "boolean") return "Boolean";
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
		const inner = val.slice(1, -1);
		if (variableSet.value.has(inner)) return "Variable";
		return "Expression";
	}
	return "Value";
}

function stripExpression(val) {
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
		return val.slice(1, -1);
	}
	return val;
}

function encodeValue(row) {
	let val = row.value;
	if (row.value_type === "Number") {
		const num = Number(val);
		if (!Number.isNaN(num)) return num;
		return val;
	}
	if (row.value_type === "Boolean") {
		if (val === true || val === "true" || val === 1 || val === "1") return true;
		if (val === false || val === "false" || val === 0 || val === "0") return false;
		return Boolean(val);
	}
	if (row.value_type === "Expression") {
		return `{${val}}`;
	}
	if (row.value_type === "Variable") {
		return `{${val}}`;
	}
	return val;
}

function valueFieldDf(row) {
	let fieldtype = "Data";
	let options = null;
	if (row.value_type === "Number") fieldtype = "Float";
	else if (row.value_type === "Boolean") fieldtype = "Check";
	else if (row.field && fieldMap.value[row.field]) {
		fieldtype = fieldMap.value[row.field].fieldtype || "Data";
		options = fieldMap.value[row.field].options || null;
	}
	return {
		fieldname: "value",
		fieldtype,
		options,
		read_only: props.readOnly,
	};
}

async function refreshVariables() {
	if (!props.node?.id) {
		variableOptions.value = [];
		return;
	}
	try {
		variableOptions.value = await store.getAvailableVariables(props.node.id);
	} catch (e) {
		variableOptions.value = [];
	}
}

async function loadDoctypeFields(doctype) {
	if (!doctype) {
		doctypeFields.value = [];
		return;
	}
	try {
		doctypeFields.value = await flexirule.utils.get_doctype_fields(doctype);
	} catch (e) {
		doctypeFields.value = [];
	}
}

function buildFilters() {
	const filters = {};
	filterRows.value.forEach((row) => {
		if (!row.field) return;
		let val = encodeValue(row);
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

function syncConfig() {
	const newConfig = {};
	Object.keys(config).forEach((k) => {
		const val = config[k];
		if (val !== undefined && val !== null && val !== "") newConfig[k] = val;
	});

	const filters = buildFilters();
	if (Object.keys(filters).length) newConfig.filters = filters;

	assignConfig(newConfig);
}

function assignConfig(newConfig) {
	if (!props.node?.data) return;
	let current = props.node.data.config || {};
	if (typeof current === "string") {
		try {
			current = JSON.parse(current);
		} catch (e) {
			current = {};
		}
	}
	const currentStr = JSON.stringify(current || {});
	const nextStr = JSON.stringify(newConfig || {});
	if (currentStr !== nextStr) {
		props.node.data.config = newConfig;
		store.mark_dirty();
	}
}

function loadConfig(val) {
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
	filterRows.value = Object.entries(filters).map(([field, val]) => {
		let operator = "=";
		let value = val;
		if (Array.isArray(val) && val.length === 2) {
			operator = val[0];
			value = val[1];
		}
		const value_type = parseValueType(value);
		return {
			field,
			operator,
			value: stripExpression(value),
			value_type,
		};
	});
	normalizeVariableRows();
}

function normalizeVariableRows() {
	if (!filterRows.value.length || !variableSet.value.size) return;
	filterRows.value.forEach((row) => {
		if (row.value_type === "Expression" && variableSet.value.has(row.value)) {
			row.value_type = "Variable";
		}
	});
}

watch(
	() => props.node?.data?.config,
	(val) => loadConfig(val),
	{ immediate: true }
);

watch(
	() => referenceDoctype.value,
	(val) => loadDoctypeFields(val),
	{ immediate: true }
);

watch(
	() => props.node?.id,
	async () => {
		await refreshVariables();
		normalizeVariableRows();
	},
	{ immediate: true }
);

watch(
	() => [filterRows.value, config],
	() => {
		syncConfig();
	},
	{ deep: true }
);

function validate() {
	return { valid: true };
}

defineExpose({ validate });
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

.row-item .field-picker-control {
	margin-bottom: 0;
}

.value-cell :deep(.control-factory) {
	width: 100%;
}
</style>
