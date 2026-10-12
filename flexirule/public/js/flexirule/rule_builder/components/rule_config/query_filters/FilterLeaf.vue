<template>
	<div v-if="!doctype" class="text-muted small p-2">
		{{ __("Select a DocType to configure filters.") }}
	</div>
	<div v-else class="filter-row">
		<div class="filter-row-main">
			<div class="filter-col field-col">
				<ComboBoxControl
					:df="{ label: __('Field'), fieldtype: 'FieldPicker', reqd: 1 }"
					:options="navigableFields.currentFields.value"
					:doctype="doctype"
					:modelValue="leaf.field || ''"
					:read_only="readOnly"
					:showValidation="validationVisible"
					:trigger="'button'"
					:navigable="true"
					:navStack="navigableFields.navStack.value"
					@navigate="navigableFields.handleNavigate"
					@back="navigableFields.handleBack"
					@update:modelValue="updateField"
				/>
			</div>
			<div class="filter-col operator-col">
				<select
					class="form-control input-xs"
					:class="{ 'is-invalid': validationVisible && operatorInvalid }"
					:value="leaf.operator"
					:disabled="readOnly || !leaf.field"
					:aria-invalid="validationVisible && operatorInvalid"
					@change="updateOperator"
				>
					<option v-for="op in operators" :key="op" :value="op">
						{{ operatorLabel(op) }}
					</option>
				</select>
			</div>
			<div class="filter-col value-col">
				<template v-if="leaf.operator === 'Between'">
					<div class="dual-value-wrapper">
						<FlexValueControl
							v-for="index in 2"
							:key="index"
							:modelValue="
								Array.isArray(leaf.value) ? leaf.value[index - 1] : emptyValue
							"
							:context="{
								df: controlSchema,
								operator: leaf.operator,
								referenceDoctype: doctype,
							}"
							:engine="store"
							:doc="store?.rule_doc"
							:variableOptions="effectiveVariableOptions"
							:disabled="readOnly"
							:showValidation="validationVisible && (valueInvalid || isMissingBetweenValue(index - 1))"
							@update:modelValue="(value) => updateBetween(index - 1, value)"
						/>
					</div>
				</template>
				<FlexValueControl
					v-else
					:modelValue="leaf.value"
					:context="{
						df: controlSchema,
						operator: leaf.operator,
						referenceDoctype: doctype,
					}"
					:engine="store"
					:doc="store?.rule_doc"
					:variableOptions="effectiveVariableOptions"
					:disabled="readOnly"
					:readOnly="readOnly"
					:showValidation="validationVisible && valueInvalid"
					@update:modelValue="updateValue"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import FlexValueControl from "../../../controls/FlexValueControl.vue";
import { useStore } from "../../../stores";
import { useNavigableFields } from "../../../composables/useNavigableFields";

const props = defineProps({
	modelValue: { type: Object, required: true },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: Boolean,
	variableOptions: { type: Array, default: null },
	showValidation: Boolean,
});
const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const injectedVariableOptions = inject("variableOptions", ref([]));
const effectiveVariableOptions = computed(
	() => props.variableOptions ?? injectedVariableOptions.value
);
const leaf = computed(() => props.modelValue || {});
const emptyValue = { mode: "static", value: "" };
const hasInteracted = ref(false);
const validationVisible = computed(() => props.showValidation || hasInteracted.value);
// Portable Query Builder operators shared by Frappe 15 and 16.
// REGEX is omitted: those release branches still render PyPika's unsupported "REGEX" SQL token.
const BASE = ["=", "!=", "like", "not like", "in", "not in", ">", "<", ">=", "<=", "is"];
const EXT = ["Between", "Timespan", "starts with", "ends with"];
const NESTED = [
	"descendants of",
	"descendants of (inclusive)",
	"not descendants of",
	"ancestors of",
	"not ancestors of",
];
// Field-type restrictions are the intersection of the Frappe 15 and 16
// standard filter UIs. This avoids offering an operator that disappears or is
// invalid on one supported major version.
const INVALID = {
	Date: ["like", "not like"],
	Datetime: ["like", "not like", "in", "not in", "=", "!="],
	Data: ["Between", "Timespan"],
	Time: ["Between", "Timespan"],
	Select: ["like", "not like", "Between", "Timespan", ">", "<", ">=", "<="],
	Link: ["Between", "Timespan", ">", "<", ">=", "<="],
	Currency: ["Between", "Timespan"],
	Color: ["Between", "Timespan", ">", "<", ">=", "<="],
	Float: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Int: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Percent: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Rating: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Code: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"HTML Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Markdown Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Text Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Small Text": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Long Text": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Text: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Password: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
};
const labels = {
	"=": __("Equals"),
	"!=": __("Not Equals"),
	like: __("Like"),
	"not like": __("Not Like"),
	in: __("In"),
	"not in": __("Not In"),
	">": __("Greater Than"),
	"<": __("Less Than"),
	">=": __("Greater Than Or Equal To"),
	"<=": __("Less Than Or Equal To"),
	is: __("Is"),
	Between: __("Between"),
	Timespan: __("Timespan"),
	"starts with": __("Starts With"),
	"ends with": __("Ends With"),
	"descendants of": __("Descendants Of"),
	"descendants of (inclusive)": __("Descendants Of (inclusive)"),
	"not descendants of": __("Not Descendants Of"),
	"ancestors of": __("Ancestors Of"),
	"not ancestors of": __("Not Ancestors Of"),
};
function supportsNestedSetOperators(def) {
	const treeDoctypes = frappe.boot?.nested_set_doctypes || [];
	if (def?.fieldtype === "Link" && treeDoctypes.includes(def.options)) return true;
	// A Tree DocType's own name field can also use hierarchy operators.
	return def?.fieldname === "name" && treeDoctypes.includes(props.doctype);
}
function getFieldTypeOperators(def) {
	const invalid = INVALID[def?.original_type] || INVALID[def?.fieldtype] || [];
	return [...BASE, ...EXT].filter((operator) => {
		if (invalid.includes(operator)) return false;
		// Starts With and Ends With are aliases for LIKE, so they inherit its
		// field-type restriction instead of accidentally bypassing the blacklist.
		return !(["starts with", "ends with"].includes(operator) && invalid.includes("like"));
	});
}
const field = computed(() => getFieldDef(leaf.value.field));
const operators = computed(() => {
	const result = getFieldTypeOperators(field.value);
	if (supportsNestedSetOperators(field.value))
		result.push(...NESTED.filter((op) => !result.includes(op)));
	if (field.value?.fieldtype === "Check") return result.filter((op) => op === "=");
	return result.length ? result : ["="];
});
const operatorInvalid = computed(
	() => !leaf.value.operator || !operators.value.includes(leaf.value.operator)
);
function isConfigured(value) {
	if (Array.isArray(value)) return value.length > 0 && value.every(isConfigured);
	if (value && typeof value === "object") {
		if (Object.prototype.hasOwnProperty.call(value, "mode")) {
			if (value.mode === "static") return !isEmpty(value.value);
			return value.value !== undefined && value.value !== null && String(value.value).trim() !== "";
		}
		return Object.keys(value).length > 0;
	}
	return !isEmpty(value) && !(typeof value === "string" && value.trim() === "");
}
function isValidIsValue(value) {
	if (value && typeof value === "object" && value.mode && value.mode !== "static") {
		return isConfigured(value);
	}
	const raw = value && typeof value === "object" && value.mode === "static" ? value.value : value;
	return ["set", "not set"].includes(String(raw ?? "").trim().toLowerCase());
}
const valueInvalid = computed(() => {
	if (!leaf.value.field) return false;
	if (operatorInvalid.value) return true;
	if (leaf.value.operator === "Between") {
		return !Array.isArray(leaf.value.value) || leaf.value.value.length < 2 || !isConfigured(leaf.value.value[0]) || !isConfigured(leaf.value.value[1]);
	}
	if (String(leaf.value.operator).toLowerCase() === "is") return !isValidIsValue(leaf.value.value);
	return !isConfigured(leaf.value.value);
});
function isMissingBetweenValue(index) {
	return !Array.isArray(leaf.value.value) || !isConfigured(leaf.value.value[index]);
}
const operatorLabel = (op) => {
	if (field.value?.fieldtype === "Date" || field.value?.fieldtype === "Datetime")
		return (
			{
				"<": __("Before"),
				">": __("After"),
				"<=": __("On or Before"),
				">=": __("On or After"),
			}[op] ||
			labels[op] ||
			op
		);
	return labels[op] || op;
};
const navigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => leaf.value.field || ""
);
const updateValue = (value) => {
	hasInteracted.value = true;
	emit("update:modelValue", { ...leaf.value, value });
};
function updateField(value) {
	hasInteracted.value = true;
	const next = { ...leaf.value, field: value };
	const def = getFieldDef(value);
	const allowed = getOperators(def);
	if (!allowed.includes(next.operator)) next.operator = allowed[0] || "=";
	if (String(leaf.value.field || "") !== String(value || "")) {
		next.value = next.operator === "Between"
			? [{ ...emptyValue }, { ...emptyValue }]
			: { ...emptyValue };
	}
	emit("update:modelValue", next);
	navigableFields.resetStack();
}
function getOperators(def) {
	const result = getFieldTypeOperators(def);
	if (supportsNestedSetOperators(def))
		result.push(...NESTED.filter((op) => !result.includes(op)));
	if (def?.fieldtype === "Check") return result.filter((op) => op === "=");
	return result.length ? result : ["="];
}
function updateOperator(event) {
	hasInteracted.value = true;
	const operator = event.target.value;
	let value = leaf.value.value;
	if (operator === "Between" && !Array.isArray(value))
		value = [{ ...emptyValue }, { ...emptyValue }];
	if (leaf.value.operator === "Between" && operator !== "Between" && Array.isArray(value))
		value = value[0] || { ...emptyValue };
	emit("update:modelValue", { ...leaf.value, operator, value });
}
function updateBetween(index, value) {
	hasInteracted.value = true;
	const values = Array.isArray(leaf.value.value)
		? [...leaf.value.value]
		: [{ ...emptyValue }, { ...emptyValue }];
	values[index] = value;
	emit("update:modelValue", { ...leaf.value, value: values });
}
function getFieldDef(fieldname) {
	if (!fieldname) return null;
	if (fieldname === "name")
		return { fieldname, value: fieldname, fieldtype: "Data", label: "Name" };
	if (["owner", "modified_by"].includes(fieldname))
		return {
			fieldname,
			value: fieldname,
			fieldtype: "Link",
			options: "User",
			label: fieldname,
		};
	if (["creation", "modified"].includes(fieldname))
		return { fieldname, value: fieldname, fieldtype: "Datetime", label: fieldname };
	if (fieldname === "docstatus")
		return { fieldname, value: fieldname, fieldtype: "Int", label: "Docstatus" };
	const raw = String(fieldname).replace(/^doc\./, "");
	if (frappe.meta?.has_field?.(props.doctype, raw)) {
		const df = frappe.meta.get_docfield(props.doctype, raw);
		return df ? { ...df, value: fieldname } : null;
	}
	return navigableFields.currentFields.value.find((item) => item.value === fieldname) || null;
}
const controlSchema = computed(() => {
	let schema = field.value
		? frappe.utils.deep_clone(field.value)
		: { fieldtype: "Data", fieldname: "value" };
	schema.label = "";
	schema.reqd = String(leaf.value.operator).toLowerCase() === "is" ? 0 : 1;
	schema.read_only = props.readOnly;
	schema.fieldname = String(leaf.value.field || "value").replace(/^doc\./, "");
	if (frappe.ui?.filter_utils?.set_fieldtype)
		frappe.ui.filter_utils.set_fieldtype(schema, null, leaf.value.operator);
	if (
		leaf.value.operator === "Between" &&
		["Date", "Datetime", "Time"].includes(field.value?.fieldtype)
	)
		schema.fieldtype = field.value.fieldtype;
	if (["in", "not in"].includes(String(leaf.value.operator).toLowerCase())) {
		if (field.value?.fieldtype === "Link") {
			schema.fieldtype = "MultiSelectList";
			schema.options = field.value.options;
			schema.get_data = async (txt) =>
				store.search_link_options({
					doctype: field.value.options,
					txt: txt || "",
					page_length: 40,
				});
		} else if (field.value?.fieldtype === "Select") {
			schema.fieldtype = "MultiSelectList";
			schema.options =
				typeof field.value.options === "string"
					? field.value.options.split("\n").filter(Boolean)
					: field.value.options || [];
		} else {
			schema.fieldtype = "Data";
			schema.placeholder = __("Comma-separated values");
		}
	}
	return schema;
});
function isEmpty(value) {
	return value === undefined || value === null || value === "";
}
async function validate() {
	const errors = [];
	if (!leaf.value.field) errors.push(__("Filter field is required."));
	if (!leaf.value.operator || operatorInvalid.value) {
		errors.push(__("Choose a supported operator for the selected field."));
	} else if (leaf.value.operator === "Between") {
		if (!Array.isArray(leaf.value.value) || leaf.value.value.length < 2 || !isConfigured(leaf.value.value[0]) || !isConfigured(leaf.value.value[1])) {
			errors.push(__("Both values are required for Between."));
		}
	} else if (String(leaf.value.operator).toLowerCase() === "is") {
		if (!isValidIsValue(leaf.value.value)) errors.push(__("Choose Set or Not Set."));
	} else if (!isConfigured(leaf.value.value)) {
		errors.push(__("Filter value is required."));
	}
	return { valid: errors.length === 0, errors };
}
defineExpose({ validate });
</script>

<style scoped>
.filter-row {
	width: 100%;
	background: var(--fxr-bg-input);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	padding: 4px var(--spacing-md);
}
.filter-row-main {
	display: flex;
	gap: var(--spacing-md);
	align-items: center;
	width: 100%;
}
.field-col {
	flex: 0 0 220px;
	min-width: 120px;
}
.operator-col {
	flex: 0 0 130px;
}
.value-col {
	flex: 1;
	min-width: 0;
}
.dual-value-wrapper {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-3);
	width: 100%;
}
.dual-value-wrapper > * {
	flex: 1;
	min-width: 0;
}
.filter-row :deep(.form-control) {
	height: var(--fxr-input-height) !important;
	padding: var(--fxr-input-padding-y) var(--fxr-input-padding-x) !important;
	font-size: var(--fxr-input-font-size) !important;
	border-radius: var(--fxr-radius-md) !important;
}
@media (max-width: 920px) {
	.filter-row-main {
		flex-wrap: wrap;
	}
	.field-col,
	.operator-col {
		flex: 1 1 200px;
	}
	.value-col {
		flex: 1 1 100%;
	}
}
</style>
