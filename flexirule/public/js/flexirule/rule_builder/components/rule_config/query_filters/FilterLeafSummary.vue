<template>
	<div class="filter-leaf-summary" :class="{ 'is-invalid': !isValid }">
		<template v-if="!isValid">
			<span class="summary-badge summary-badge--invalid">
				<i class="fa fa-exclamation-circle" aria-hidden="true"></i>
				<span>{{ invalidReason }}</span>
			</span>
		</template>
		<template v-else>
			<span class="summary-field">{{ fieldLabel }}</span>
			<span class="summary-operator">{{ operatorLabel }}</span>
			<span v-if="hasValue" class="summary-value">{{ valueLabel }}</span>
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { getFieldType } from "./filter_operators.mjs";
import { isFilterLeafValid } from "./query_filter_validation.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	doctype: { type: String, required: true },
	variableOptions: { type: Array, default: null },
});

const labels = {
	"=": __("equals"),
	"!=": __("does not equal"),
	like: __("contains"),
	"not like": __("does not contain"),
	in: __("is one of"),
	"not in": __("is not one of"),
	">": __("is greater than"),
	"<": __("is less than"),
	">=": __("is greater than or equal to"),
	"<=": __("is less than or equal to"),
	is: __("is"),
	Between: __("is between"),
	Timespan: __("is in timespan"),
	"starts with": __("starts with"),
	"ends with": __("ends with"),
	"descendants of": __("is descendant of"),
	"descendants of (inclusive)": __("is descendant of (inclusive)"),
	"not descendants of": __("is not descendant of"),
	"ancestors of": __("is ancestor of"),
	"not ancestors of": __("is not ancestor of"),
};

function humanize(raw) {
	if (!raw) return "";
	return String(raw)
		.replace(/_/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase());
}

const fieldDef = computed(() => {
	const fieldname = props.node?.field;
	if (!fieldname) return null;
	if (fieldname === "name") return { fieldname, fieldtype: "Data", label: __("Name") };
	if (["owner", "modified_by"].includes(fieldname))
		return { fieldname, fieldtype: "Link", options: "User", label: humanize(fieldname) };
	if (["creation", "modified"].includes(fieldname))
		return { fieldname, fieldtype: "Datetime", label: humanize(fieldname) };
	if (fieldname === "docstatus") return { fieldname, fieldtype: "Int", label: __("Docstatus") };

	const parts = fieldname.split(".");
	if (parts.length > 1) {
		const formattedParts = parts.map(humanize);
		return { fieldname, fieldtype: "Data", label: formattedParts.join(" · ") };
	}

	const raw = String(fieldname).replace(/^doc\./, "");
	if (typeof frappe !== "undefined" && frappe.meta?.has_field?.(props.doctype, raw)) {
		const df = frappe.meta.get_docfield(props.doctype, raw);
		if (df) return { ...df, label: __(df.label || raw) };
	}
	return { fieldname, fieldtype: "Data", label: humanize(raw) };
});

const fieldLabel = computed(() => {
	if (!props.node?.field) return "";
	return fieldDef.value?.label || humanize(props.node.field);
});

const operatorLabel = computed(() => {
	const op = props.node?.operator;
	if (!op) return "";
	const fieldtype = getFieldType(fieldDef.value);
	if (["Date", "Datetime"].includes(fieldtype)) {
		const dateLabels = {
			"<": __("is before"),
			">": __("is after"),
			"<=": __("is on or before"),
			">=": __("is on or after"),
		};
		if (dateLabels[op]) return dateLabels[op];
	}
	return labels[op] || op;
});

function formatSingleValue(val) {
	if (val === null || val === undefined || val === "") return "";
	if (typeof val === "object" && val.mode) {
		if (val.mode === "static") {
			return formatSingleValue(val.value);
		}
		if (val.mode === "variable") {
			const varName = val.value || val.variable || "";
			return __("Variable ({0})", [varName]);
		}
		if (val.mode === "resolver" || val.resolver_type) {
			const name = val.resolver_type || val.mode || "Resolver";
			return humanize(name);
		}
		return humanize(val.mode);
	}
	if (Array.isArray(val)) {
		return val.map(formatSingleValue).filter(Boolean).join(", ");
	}
	return String(val);
}

const hasValue = computed(() => {
	const op = props.node?.operator;
	if (!op) return false;
	if (String(op).toLowerCase() === "is") return true;
	return true;
});

const valueLabel = computed(() => {
	const op = props.node?.operator;
	const value = props.node?.value;

	if (String(op).toLowerCase() === "is") {
		const raw = typeof value === "object" && value?.mode === "static" ? value.value : value;
		if (typeof raw === "string" && ["set", "not set"].includes(raw.trim().toLowerCase())) {
			return raw.trim().toLowerCase() === "set" ? __("Set") : __("Not Set");
		}
		return formatSingleValue(value) || __("Set");
	}

	if (op === "Between") {
		const arr = Array.isArray(value) ? value : [];
		const start = formatSingleValue(arr[0]);
		const end = formatSingleValue(arr[1]);
		if (start && end) return __("{0} and {1}", [start, end]);
		return start || end || "";
	}

	return formatSingleValue(value);
});

const isValid = computed(() => isFilterLeafValid(props.node));

const invalidReason = computed(() => {
	if (!props.node?.field) return __("Incomplete filter: select a field");
	if (!props.node?.operator) return __("Incomplete filter: select an operator");
	return __("Incomplete filter: enter a value");
});
</script>

<style scoped>
.filter-leaf-summary {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-1, 6px);
	padding: var(--fxr-space-1, 4px) var(--fxr-space-2, 8px);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-bg-card, #fff);
	border: 1px solid var(--fxr-border-subtle, #e5e7eb);
	font-size: var(--fxr-text-sm, 12px);
	line-height: 1.4;
	color: var(--fxr-text, #111827);
	min-width: 0;
	box-sizing: border-box;
}

.summary-field {
	font-weight: var(--fxr-weight-semibold, 600);
	color: var(--fxr-text-strong, #111827);
}

.summary-operator {
	color: var(--fxr-text-muted, #6b7280);
	font-style: normal;
}

.summary-value {
	font-weight: var(--fxr-weight-medium, 500);
	color: var(--fxr-text, #111827);
	background: var(--fxr-surface-soft, #f3f4f6);
	padding: 1px 6px;
	border-radius: var(--fxr-radius-sm, 4px);
}

.summary-badge--invalid {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-1, 4px);
	color: var(--fxr-text-danger, #dc2626);
	font-weight: var(--fxr-weight-medium, 500);
}
</style>
