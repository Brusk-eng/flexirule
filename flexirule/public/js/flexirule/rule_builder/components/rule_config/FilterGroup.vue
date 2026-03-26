<template>
	<div class="filter-group-wrapper">
		<div
			v-if="!doctype && !allowAnyDoctype"
			class="text-muted small p-2 text-center border-dashed rounded"
		>
			{{ __("Select a DocType to configure filters.") }}
		</div>
		<div v-else class="filter-list">
			<div v-for="(row, idx) in filters" :key="idx" class="filter-row">
				<div class="filter-row-main">
					<!-- Doctype Picker (if allowAnyDoctype) -->
					<div v-if="allowAnyDoctype" class="filter-col doctype-col">
						<LinkControl
							:df="{ label: '', fieldtype: 'Link', options: 'DocType' }"
							:modelValue="row.doctype || doctype"
							:hideLabel="true"
							:read_only="readOnly"
							@update:modelValue="(val) => updateRow(idx, { doctype: val })"
						/>
					</div>

					<!-- Field Picker -->
					<div class="filter-col field-col">
						<div class="field-picker-container">
							<FieldPickerControl
								:df="{ label: '' }"
								:fields="getFieldsForDoctype(row.doctype || doctype)"
								:documentType="row.doctype || doctype"
								:modelValue="row.field"
								:read_only="readOnly"
								:class="{
									'border-warning':
										row.field &&
										!isFieldValid(row.field, row.doctype || doctype),
								}"
								@update:modelValue="(val) => updateRow(idx, { field: val })"
							/>
							<i
								v-if="row.field && !isFieldValid(row.field, row.doctype || doctype)"
								class="fa fa-warning text-warning field-warning-icon"
								:title="__('Field not found in DocType')"
							></i>
						</div>
					</div>

					<!-- Operator -->
					<div class="filter-col operator-col">
						<select
							class="form-control input-xs"
							:value="row.operator"
							:disabled="readOnly"
							@change="(e) => updateRow(idx, { operator: e.target.value })"
						>
							<option
								v-for="op in getOperatorsForField(
									getFieldDef(row.field, row.doctype)
								)"
								:key="op"
								:value="op"
							>
								{{ operatorLabelMap[op] || op }}
							</option>
						</select>
					</div>

					<!-- Value / Expression -->
					<div class="filter-col value-col">
						<div class="value-input-group">
							<template v-if="row.value_type === 'Expression'">
								<div class="expression-wrapper">
									<span class="expr-bracket">{</span>
									<AutocompleteControl
										:df="{ fieldtype: 'Autocomplete', label: '' }"
										:modelValue="stripBracket(row.value)"
										:get_options="getVariableOptions"
										:hideLabel="true"
										:read_only="readOnly"
										@update:modelValue="
											(val) => updateRow(idx, { value: `{${val}}` })
										"
									/>
									<span class="expr-bracket">}</span>
								</div>
							</template>
							<template v-else-if="row.value_type === 'Variable'">
								<AutocompleteControl
									:df="{ fieldtype: 'Autocomplete', label: '' }"
									:modelValue="stripBracket(row.value)"
									:get_options="getVariableOptions"
									:hideLabel="true"
									:read_only="readOnly"
									@update:modelValue="
										(val) => updateRow(idx, { value: `{${val}}` })
									"
								/>
							</template>
							<template v-else>
								<select
									v-if="row.operator === 'is'"
									class="form-control input-xs"
									:value="row.value"
									:disabled="readOnly"
									@change="
										(e) =>
											updateRow(idx, {
												value: e.target.value,
												value_type: 'Value',
											})
									"
								>
									<option value="set">{{ __("Set") }}</option>
									<option value="not set">{{ __("Not Set") }}</option>
								</select>
								<select
									v-else-if="row.operator === 'Timespan'"
									class="form-control input-xs"
									:value="row.value"
									:disabled="readOnly"
									@change="
										(e) =>
											updateRow(idx, {
												value: e.target.value,
												value_type: 'Value',
											})
									"
								>
									<option
										v-for="opt in timespanOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
								<select
									v-else-if="isBooleanValue(row)"
									class="form-control input-xs"
									:value="row.value"
									:disabled="readOnly"
									@change="
										(e) =>
											updateRow(idx, {
												value: e.target.value,
												value_type: 'Boolean',
											})
									"
								>
									<option value="1">{{ __("Yes") }}</option>
									<option value="0">{{ __("No") }}</option>
								</select>
								<input
									v-else
									type="text"
									class="form-control input-xs"
									:value="row.value"
									:placeholder="__('Value')"
									:disabled="readOnly"
									@input="(e) => updateRow(idx, { value: e.target.value })"
								/>
							</template>
						</div>
					</div>

					<!-- Value Type Toggle -->
					<div class="filter-col type-col">
						<select
							class="form-control input-xs type-select"
							:value="row.value_type"
							:disabled="readOnly"
							@change="(e) => toggleValueType(idx, e.target.value)"
						>
							<option v-for="vt in valueTypes" :key="vt" :value="vt">
								{{ __(vt) }}
							</option>
						</select>
					</div>

					<!-- Delete -->
					<div v-if="!readOnly" class="filter-col action-col">
						<button class="btn btn-xs btn-link text-danger" @click="removeFilter(idx)">
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>

			<div v-if="!readOnly" class="filter-actions mt-2">
				<button class="btn btn-xs btn-link p-0 text-primary" @click="addFilter">
					<i class="fa fa-plus mr-1"></i> {{ __("Add Filter") }}
				</button>
				<button
					v-if="filters.length > 0"
					class="btn btn-xs btn-link p-0 text-muted ml-3"
					@click="clearFilters"
				>
					{{ __("Clear All") }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import FieldPickerControl from "../../controls/FieldPickerControl.vue";
import AutocompleteControl from "../../controls/AutocompleteControl.vue";
import LinkControl from "../../controls/LinkControl.vue";
import { useStore } from "../../store";

const props = defineProps({
	modelValue: {
		type: Array,
		default: () => [],
	},
	doctype: {
		type: String,
		required: true,
	},
	nodeId: {
		type: String,
		default: null,
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
	allowAnyDoctype: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();

const filters = ref([]);
const valueTypes = ["Value", "Number", "Boolean", "Variable", "Expression"];

const timespanOptions = [
	{ label: __("Last 7 Days"), value: "last 7 days" },
	{ label: __("Last 30 Days"), value: "last 30 days" },
	{ label: __("Last Month"), value: "last month" },
	{ label: __("Last Quarter"), value: "last quarter" },
	{ label: __("Last Year"), value: "last year" },
	{ label: __("Yesterday"), value: "yesterday" },
	{ label: __("Today"), value: "today" },
	{ label: __("Tomorrow"), value: "tomorrow" },
	{ label: __("This Week"), value: "this week" },
	{ label: __("This Month"), value: "this month" },
	{ label: __("This Quarter"), value: "this quarter" },
	{ label: __("This Year"), value: "this year" },
];

const ALL_CONDITIONS = [
	["=", __("Equals")],
	["!=", __("Not Equals")],
	["like", __("Like")],
	["not like", __("Not Like")],
	["in", __("In")],
	["not in", __("Not In")],
	["is", __("Is")],
	[">", __("Greater Than")],
	["<", __("Less Than")],
	[">=", __("Greater Than Or Equal To")],
	["<=", __("Less Than Or Equal To")],
	["Between", __("Between")],
	["Timespan", __("Timespan")],
	["starts with", __("Starts With")],
	["ends with", __("Ends With")],
];

const operatorLabelMap = Object.fromEntries(ALL_CONDITIONS.map(([op, label]) => [op, label]));

const INVALID_CONDITION_MAP = {
	Date: ["like", "not like", "starts with", "ends with"],
	Datetime: ["like", "not like", "in", "not in", "=", "!=", "starts with", "ends with"],
	Data: ["Between", "Timespan"],
	Time: ["Between", "Timespan", "starts with", "ends with"],
	Select: ["like", "not like", "Between", "Timespan", "starts with", "ends with"],
	Link: ["Between", "Timespan", ">", "<", ">=", "<=", "starts with", "ends with"],
	Currency: ["Between", "Timespan", "starts with", "ends with"],
	Color: ["Between", "Timespan", "starts with", "ends with"],
	Check: ALL_CONDITIONS.map((c) => c[0]).filter((c) => c !== "="),
	Rating: ["like", "not like", "Between", "in", "not in", "Timespan", "starts with", "ends with"],
	Float: ["like", "not like", "Between", "in", "not in", "Timespan", "starts with", "ends with"],
	Int: ["like", "not like", "Between", "in", "not in", "Timespan", "starts with", "ends with"],
};

// Initialize local state from modelValue
const syncFromProps = () => {
	if (!props.modelValue || !Array.isArray(props.modelValue)) {
		filters.value = [];
		return;
	}

	// Normalize if coming from frappe format [dt, field, op, val]
	filters.value = props.modelValue.map((f) => {
		let row = {};
		if (Array.isArray(f)) {
			row = {
				doctype: f[0],
				field: f[1],
				operator: f[2],
				value: f[3],
				value_type: guessValueType(f[3]),
			};
		} else {
			row = {
				doctype: f.doctype || props.doctype,
				field: f.field || f.fieldname,
				operator: f.operator || f.op || "=",
				value: f.value,
				value_type: f.value_type || guessValueType(f.value),
			};
		}
		// Ensure operator is valid for field
		const field = getFieldDef(row.field, row.doctype);
		const allowed = getOperatorsForField(field);
		if (!allowed.includes(row.operator)) {
			row.operator = allowed[0] || "=";
		}
		return row;
	});
};

const emitUpdate = () => {
	const serialized = filters.value
		.filter((r) => r.field)
		.map((r) => ({
			doctype: r.doctype || props.doctype,
			field: r.field,
			operator: r.operator || "=",
			value: r.value,
			value_type: r.value_type || "Value",
		}));
	emit("update:modelValue", serialized);
};

const guessValueType = (val) => {
	if (typeof val === "number") return "Number";
	if (typeof val === "boolean") return "Boolean";
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
		return "Expression";
	}
	return "Value";
};

const stripBracket = (val) => {
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
		return val.slice(1, -1);
	}
	return val;
};

const getFieldsForDoctype = (dt) => {
	if (!dt) return [];
	if (props.fields && props.fields.length > 0) return props.fields;
	return store.get_fields_for_doctype(dt);
};

const getFieldDef = (fieldname, dt) => {
	if (!fieldname) return null;
	const fields = getFieldsForDoctype(dt || props.doctype);
	return fields.find((f) => f.value === fieldname) || null;
};

const getOperatorsForField = (field) => {
	if (!field) return ALL_CONDITIONS.map((c) => c[0]);
	const ft = field.fieldtype;
	const invalid = INVALID_CONDITION_MAP[ft] || [];
	return ALL_CONDITIONS.filter((c) => !invalid.includes(c[0])).map((c) => c[0]);
};

const isBooleanValue = (row) => {
	if (row.value_type === "Boolean") return true;
	const field = getFieldDef(row.field, row.doctype);
	return field && field.fieldtype === "Check";
};

const getVariableOptions = async () => {
	if (!props.nodeId) return [];
	return await store.getAvailableVariables(props.nodeId);
};

const addFilter = () => {
	filters.value.push({
		doctype: props.doctype,
		field: "",
		operator: "=",
		value: "",
		value_type: "Value",
	});
	emitUpdate();
};

const removeFilter = (idx) => {
	filters.value.splice(idx, 1);
	emitUpdate();
};

const clearFilters = () => {
	filters.value = [];
	emitUpdate();
};

const updateRow = (idx, data) => {
	const row = filters.value[idx];
	const merged = { ...row, ...data };

	// If field changed, update operator and reset value if needed
	if (data.field && data.field !== row.field) {
		const field = getFieldDef(data.field, merged.doctype);
		const operators = getOperatorsForField(field);
		if (!operators.includes(merged.operator)) {
			merged.operator = operators[0] || "=";
		}
		// Reset value if switching between types that might conflict
	}

	filters.value[idx] = merged;
	emitUpdate();
};

const toggleValueType = (idx, type) => {
	const row = filters.value[idx];
	row.value_type = type;

	if (type === "Expression" || type === "Variable") {
		if (!row.value || !row.value.startsWith("{")) {
			row.value = `{${row.value || ""}}`;
		}
	} else if (row.value && row.value.startsWith("{")) {
		row.value = stripBracket(row.value);
	}

	emitUpdate();
};

const isFieldValid = (fieldname, dt) => {
	const fields = getFieldsForDoctype(dt || props.doctype);
	if (!fields || !fields.length) return true;
	if (!fieldname) return true;
	if (typeof fieldname === "string" && fieldname.startsWith("{")) return true;
	return fields.some((f) => f.value === fieldname);
};

watch(() => props.modelValue, syncFromProps, { deep: true });
watch(
	() => props.doctype,
	() => {
		// Optional: Clear filters if doctype changes and not allowing any doctype
		// if (!props.allowAnyDoctype) clearFilters();
	}
);

onMounted(syncFromProps);
</script>

<style scoped>
.filter-group-wrapper {
	width: 100%;
}

.filter-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.filter-row {
	display: flex;
	flex-direction: column;
	background: #f8f9fa;
	border: 1px solid #e9ecef;
	border-radius: 4px;
	padding: 6px;
}

.filter-row-main {
	display: grid;
	grid-template-columns: 1.5fr 0.8fr 2fr 0.8fr auto;
	gap: 8px;
	align-items: center;
}

/* Specific columns */
.doctype-col {
	grid-column: span 1;
}
.field-col {
	min-width: 120px;
}
.operator-col {
	min-width: 80px;
}
.value-col {
	min-width: 150px;
}
.type-col {
	min-width: 90px;
}

.field-picker-container {
	position: relative;
	display: flex;
	align-items: center;
	width: 100%;
}

.field-warning-icon {
	position: absolute;
	right: 18px;
	z-index: 5;
	pointer-events: all;
	cursor: help;
}

:deep(.border-warning .form-control) {
	border-color: var(--orange-500, #ff9800) !important;
	background-color: #fff8f1 !important;
}

.value-input-group {
	display: flex;
	width: 100%;
}

.expression-wrapper {
	display: flex;
	align-items: center;
	background: #fff8e1;
	border: 1px solid #ffe082;
	border-radius: 4px;
	padding: 0 4px;
	width: 100%;
}

.expr-bracket {
	color: #ffa000;
	font-weight: bold;
	padding: 0 4px;
}

.type-select {
	font-size: 10px;
	height: 24px;
	padding: 2px 4px;
	background: #f1f3f5;
}

.border-dashed {
	border: 1px dashed #dee2e6;
}

:deep(.field-picker-control) {
	margin-bottom: 0 !important;
}

:deep(.control.frappe-control) {
	margin-bottom: 0 !important;
}

.filter-row-main :deep(.form-control) {
	height: 28px;
	padding: 2px 8px;
	font-size: 12px;
}
</style>
