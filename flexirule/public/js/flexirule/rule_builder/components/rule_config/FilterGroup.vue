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
							<template v-if="row.operator === 'Between'">
								<div class="dual-value-wrapper">
									<div class="value-input-item">
										<template
											v-if="
												row.value_type === 'Variable' ||
												row.value_type === 'Expression'
											"
										>
											<AutocompleteControl
												:df="{ fieldtype: 'Autocomplete', label: '' }"
												:modelValue="
													stripBracket(getBetweenValue(row.value, 0))
												"
												:get_options="getVariableOptions"
												:hideLabel="true"
												:read_only="readOnly"
												@update:modelValue="
													(val) =>
														setBetweenValue(
															idx,
															0,
															row.value_type === 'Value'
																? val
																: `{${val}}`
														)
												"
											/>
										</template>
										<template v-else>
											<ControlFactory
												:df="getControlFactorySchema(row)"
												:modelValue="getBetweenValue(row.value, 0)"
												:read_only="readOnly"
												:hideLabel="true"
												@update:modelValue="
													(val) => setBetweenValue(idx, 0, val)
												"
											/>
										</template>
									</div>
									<span class="between-sep">{{ __("and") }}</span>
									<div class="value-input-item">
										<template
											v-if="
												row.value_type === 'Variable' ||
												row.value_type === 'Expression'
											"
										>
											<AutocompleteControl
												:df="{ fieldtype: 'Autocomplete', label: '' }"
												:modelValue="
													stripBracket(getBetweenValue(row.value, 1))
												"
												:get_options="getVariableOptions"
												:hideLabel="true"
												:read_only="readOnly"
												@update:modelValue="
													(val) =>
														setBetweenValue(
															idx,
															1,
															row.value_type === 'Value'
																? val
																: `{${val}}`
														)
												"
											/>
										</template>
										<template v-else>
											<ControlFactory
												:df="getControlFactorySchema(row)"
												:modelValue="getBetweenValue(row.value, 1)"
												:read_only="readOnly"
												:hideLabel="true"
												@update:modelValue="
													(val) => setBetweenValue(idx, 1, val)
												"
											/>
										</template>
									</div>
								</div>
							</template>
							<template
								v-else-if="
									row.value_type === 'Expression' || row.value_type === 'Variable'
								"
							>
								<div
									class="expression-wrapper"
									:class="{ 'variable-mode': row.value_type === 'Variable' }"
								>
									<span
										class="expr-bracket"
										v-if="row.value_type === 'Expression'"
										>{</span
									>
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
									<span
										class="expr-bracket"
										v-if="row.value_type === 'Expression'"
										>}</span
									>
								</div>
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
								<div v-else style="width: 100%; min-width: 150px">
									<ControlFactory
										:df="getControlFactorySchema(row)"
										:modelValue="row.value"
										:read_only="readOnly"
										:hideLabel="true"
										@update:modelValue="(val) => updateRow(idx, { value: val })"
									/>
								</div>
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
import ControlFactory from "../../controls/ControlFactory.vue";
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

	// Stability check: If our cleaned local state is already same as incoming prop,
	// do nothing. This preserves local empty rows being edited.
	const clean_local = filters.value
		.filter((f) => f.field || f.fieldname)
		.map((f) => ({
			doctype: f.doctype || props.doctype,
			field: f.field || f.fieldname,
			operator: f.operator || f.op || "=",
			value: f.value,
			value_type: f.value_type || "Value",
		}));

	// deep compare strings
	if (JSON.stringify(clean_local) === JSON.stringify(props.modelValue)) {
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
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) {
		return [];
	}
	return fields.map((f) => {
		// Extract raw label from format "doc.fieldname (Real Label)"
		let realLabel = f.label;
		const match = f.label.match(/\((.*?)\)/);
		if (match && match[1]) {
			realLabel = match[1];
		}

		return {
			...f,
			label: `${realLabel} (${f.fieldname})`,
			value: f.fieldname,
		};
	});
};

const getFieldDef = (fieldname, doctype) => {
	if (!fieldname) return null;
	const dt = doctype || props.doctype;

	// Standard field fallbacks
	if (["name"].includes(fieldname)) {
		return { fieldname, value: fieldname, fieldtype: "Data", label: "Name" };
	}
	if (["owner", "modified_by"].includes(fieldname)) {
		return {
			fieldname,
			value: fieldname,
			fieldtype: "Link",
			options: "User",
			label: fieldname === "owner" ? "Owner" : "Modified By",
		};
	}
	if (["creation", "modified"].includes(fieldname)) {
		return {
			fieldname,
			value: fieldname,
			fieldtype: "Datetime",
			label: fieldname === "creation" ? "Creation" : "Modified",
		};
	}
	if (fieldname === "docstatus") {
		return { fieldname, value: fieldname, fieldtype: "Int", label: "Docstatus" };
	}

	// Try Frappe's native meta cache first
	if (dt && window.frappe && frappe.meta && frappe.meta.has_field(dt, fieldname)) {
		const df = frappe.meta.get_docfield(dt, fieldname);
		if (df) {
			return { ...df, value: df.fieldname }; // ensure value alias is there
		}
	}

	// Fallback to locally extracted list
	const fields = getFieldsForDoctype(dt);
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
	const field = getFieldDef(row.field, row.doctype || props.doctype);
	return field && field.fieldtype === "Check";
};

const getVariableOptions = async () => {
	if (!props.nodeId) return [];
	return await store.getAvailableVariables(props.nodeId);
};

const getControlFactorySchema = (row) => {
	const field = getFieldDef(row.field, row.doctype || props.doctype);
	let schema = field ? frappe.utils.deep_clone(field) : { fieldtype: "Data", fieldname: "value" };
	schema.label = "";
	schema.read_only = props.readOnly;
	schema.fieldname = field ? field.value : "value"; // Ensure valid fieldname for frappe controls

	// Native Frappe Filter Manipulation (perfect parity)
	if (window.frappe && frappe.ui && frappe.ui.filter_utils) {
		frappe.ui.filter_utils.set_fieldtype(schema, null, row.operator);
		// Force restore fieldtype for Between if it's a date/time field,
		// as set_fieldtype might sometimes generalize it to Data for multiple values
		if (row.operator === "Between" && ["Date", "Datetime", "Time"].includes(field?.fieldtype)) {
			schema.fieldtype = field.fieldtype;
		}
	} else {
		// Fallback if filter_utils is somehow missing
		if (schema.fieldname === "docstatus") {
			schema.fieldtype = "Select";
			schema.options = [
				{ value: "0", label: __("Draft") },
				{ value: "1", label: __("Submitted") },
				{ value: "2", label: __("Cancelled") },
			];
		} else if (schema.fieldtype === "Check") {
			schema.fieldtype = "Select";
			schema.options = [
				{ label: __("Yes"), value: "1" },
				{ label: __("No"), value: "0" },
			];
		}
	}

	// FlexiRule Specific overrides for multi-value operators
	if (["in", "not in"].includes(row.operator)) {
		schema.fieldtype = "Data";
		schema.placeholder = __("Comma-separated values");
	} else if (row.operator === "Between") {
		schema.placeholder = __("Value1, Value2");
	}

	return schema;
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
	}

	// Handle operator change to/from Between
	if (data.operator && data.operator !== row.operator) {
		if (data.operator === "Between" && !Array.isArray(merged.value)) {
			merged.value = [merged.value || "", ""];
		} else if (row.operator === "Between" && Array.isArray(merged.value)) {
			merged.value = merged.value[0] || "";
		}
	}

	filters.value[idx] = merged;
	emitUpdate();
};

const getBetweenValue = (value, idx) => {
	if (Array.isArray(value)) return value[idx] || "";
	if (typeof value === "string" && value.includes(",")) {
		return value.split(",")[idx]?.trim() || "";
	}
	return idx === 0 ? value : "";
};

const setBetweenValue = (idx, valIdx, newVal) => {
	const row = filters.value[idx];
	let currentVal = row.value;
	if (!Array.isArray(currentVal)) {
		currentVal = [getBetweenValue(currentVal, 0), getBetweenValue(currentVal, 1)];
	}
	currentVal[valIdx] = newVal;
	updateRow(idx, { value: [...currentVal] });
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

.dual-value-wrapper {
	display: flex;
	align-items: center;
	gap: 6px;
	width: 100%;
}

.value-input-item {
	flex: 1;
	min-width: 0;
}

.between-sep {
	font-size: 11px;
	color: #6c757d;
	font-weight: 500;
}

.expression-wrapper.variable-mode {
	background: #f3f0ff;
	border-color: #d1c4e9;
}

.expression-wrapper.variable-mode .expr-bracket {
	color: #673ab7;
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
