<template>
	<div class="assignment-config">
		<div class="config-section section-card header-compact mb-3">
			<div class="d-flex align-items-center justify-content-between">
				<div class="d-flex flex-column">
					<h5 class="mb-0">{{ __("Batch Assignments") }}</h5>
					<span class="text-muted fxr-text-xs">
						{{ __("Sequential state mutations applied in order") }}
					</span>
				</div>
				<button
					v-if="assignments.length > 1"
					class="fxr-btn fxr-btn--ghost fxr-btn--sm text-danger"
					@click="clearAssignments"
					:disabled="readOnly"
				>
					<i class="fa fa-eraser me-1"></i>
					{{ __("Clear All") }}
				</button>
			</div>
		</div>

		<!-- Horizontal Table Grid Header -->
		<div
			v-if="assignments.length"
			class="assignment-grid-header mb-1 text-muted small fw-semibold"
		>
			<div class="grid-col-target">{{ __("Target Field") }}</div>
			<div class="grid-col-operator">{{ __("Operator") }}</div>
			<div class="grid-col-value">{{ __("Value Expression") }}</div>
			<div class="grid-col-when">{{ __("Run If") }}</div>
			<div class="grid-col-actions"></div>
		</div>

		<div class="assignments-list">
			<div
				v-for="(assignment, index) in assignments"
				:key="index"
				class="assignment-grid-row align-items-center mb-2"
			>
				<!-- Target ComboBox with Type Badge support -->
				<div class="grid-col-target">
					<ComboBoxControl
						:df="{ fieldtype: 'FieldPicker', label: '' }"
						:modelValue="assignment.target"
						:options="targetOptions"
						:read_only="readOnly"
						:hideLabel="true"
						:trigger="'button'"
						:placeholder="__('Target field/variable...')"
						:allowCustomValue="false"
						@update:modelValue="(val) => onTargetChange(index, val)"
					/>
				</div>

				<!-- Operator Selector -->
				<div class="grid-col-operator">
					<ComboBoxControl
						:df="{ fieldtype: 'Select', label: '' }"
						:options="getAvailableOperators(assignment.target)"
						:modelValue="assignment.operator"
						:read_only="readOnly"
						:hideLabel="true"
						:trigger="'button'"
						@update:modelValue="(val) => onOperatorChange(index, val)"
					/>
				</div>

				<!-- Value Expression Editor -->
				<div class="grid-col-value">
					<template v-if="needsValue(assignment.operator)">
						<div class="value-mode-wrap">
							<!-- Mode toggle -->
							<button
								class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost value-mode-toggle"
								:title="
									assignment.value_mode === 'resolver'
										? __('Switch to Template Editor')
										: __('Switch to Formula Resolver')
								"
								:disabled="readOnly"
								@click="toggleValueMode(index)"
							>
								<i
									:class="
										assignment.value_mode === 'resolver'
											? 'fa fa-pencil'
											: 'fa fa-calculator'
									"
								></i>
							</button>
							<!-- Resolver mode -->
							<ValueResolverControl
								v-if="assignment.value_mode === 'resolver'"
								class="flex-1 min-w-0"
								:modelValue="assignment.value_template_ui"
								:doctype="
									getTargetDoctype(assignment.target) ||
									store.rule_doc?.document_type ||
									''
								"
								:readOnly="readOnly"
								@update:modelValue="(val) => updateResolverTemplate(index, val)"
							/>
							<!-- Template (TipTap) mode -->
							<FlexStructuredValueControl
								v-else
								class="flex-1 min-w-0"
								:fieldType="getTargetFieldtype(assignment.target) || 'Data'"
								:modelValue="assignment.value_template_ui"
								:read_only="readOnly"
								:variableOptions="variable_options"
								:allowedModes="supportedTemplateModes"
								:referenceDoctype="getTargetDoctype(assignment.target)"
								:placeholder="__('Type value...')"
								:options="getTargetOptions(assignment.target)"
								@update:modelValue="(val) => updateTemplate(index, val)"
							/>
						</div>
					</template>
					<div v-else class="operator-hint-text text-muted small">
						<i class="fa fa-info-circle me-1"></i>
						{{ operatorNoValueHint(assignment.operator) }}
					</div>
				</div>

				<div class="grid-col-when">
					<div class="when-editor-cell">
						<button
							class="fxr-btn fxr-btn--ghost fxr-btn--sm w-100 text-start"
							:disabled="readOnly"
							@click="openWhenConditionEditor(index)"
						>
							<i class="fa fa-code-fork me-1"></i>
							{{
								hasWhenCondition(assignment)
									? __("Condition Set")
									: __("Always Run")
							}}
						</button>
						<div
							v-if="assignment.when_expression && !assignment.when_condition"
							class="text-muted fxr-text-xs mt-1"
						>
							{{ __("Legacy expression detected") }}
						</div>
					</div>
				</div>

				<!-- Row Actions -->
				<div
					class="grid-col-actions d-flex align-items-center justify-content-end fxr-gap-1"
				>
					<button
						class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost"
						@click="moveAssignment(index, -1)"
						:disabled="readOnly || index === 0"
						:title="__('Move Up')"
						aria-label="Move Up"
					>
						<i class="fa fa-chevron-up"></i>
					</button>
					<button
						class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost"
						@click="moveAssignment(index, 1)"
						:disabled="readOnly || index === assignments.length - 1"
						:title="__('Move Down')"
						aria-label="Move Down"
					>
						<i class="fa fa-chevron-down"></i>
					</button>
					<button
						class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost text-danger"
						@click="removeAssignment(index)"
						:disabled="readOnly"
						:title="__('Remove')"
						aria-label="Remove Assignment"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
			</div>
		</div>

		<div
			v-if="!assignments.length"
			class="empty-state d-flex flex-column align-items-center justify-content-center py-5"
		>
			<div class="empty-state-icon mb-3">
				<i class="fa fa-list-ol fa-3x text-muted opacity-25"></i>
			</div>
			<div class="text-center px-4">
				<h6 class="mb-1 fw-bold text-muted">{{ __("No Assignments Yet") }}</h6>
				<p class="small text-muted mb-0">
					{{ __("Add an assignment to start mutating document fields or variables.") }}
				</p>
			</div>
		</div>

		<button class="add-assignment-btn mt-2" @click="addAssignment" :disabled="readOnly">
			<i class="fa fa-plus"></i>
			<span>{{ __("Add Assignment") }}</span>
		</button>

		<Teleport to="body">
			<div
				v-if="whenEditor.open"
				class="fxr-modal-overlay"
				@click.self="closeWhenConditionEditor"
			>
				<div class="fxr-modal-card">
					<div class="d-flex align-items-center justify-content-between mb-2">
						<h5 class="mb-0">{{ __("Assignment Run Condition") }}</h5>
						<button
							class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost"
							@click="closeWhenConditionEditor"
						>
							<i class="fa fa-times"></i>
						</button>
					</div>
					<div class="condition-builder-wrap">
						<ConditionBuilder
							:modelValue="whenEditor.draft"
							:docFields="whenConditionDocFields"
							:variableOptions="variable_options"
							:readOnly="false"
							@update:modelValue="(val) => (whenEditor.draft = val)"
						/>
					</div>
					<div class="d-flex justify-content-between mt-3">
						<button
							class="fxr-btn fxr-btn--sm fxr-btn--ghost text-danger"
							@click="clearWhenCondition"
						>
							{{ __("Clear Condition") }}
						</button>
						<div class="d-flex fxr-gap-1">
							<button
								class="fxr-btn fxr-btn--sm fxr-btn--secondary"
								@click="closeWhenConditionEditor"
							>
								{{ __("Cancel") }}
							</button>
							<button
								class="fxr-btn fxr-btn--sm fxr-btn--primary"
								@click="saveWhenCondition"
							>
								{{ __("Save Condition") }}
							</button>
						</div>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, watch, ref } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import FlexStructuredValueControl from "../../../controls/FlexStructuredValueControl.vue";
import ValueResolverControl from "../../../controls/ValueResolverControl.vue";
import ConditionBuilder from "../../condition_builder/ConditionBuilder.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";
import { ASSIGNMENT_OPERATOR_METADATA } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { doctype_fields, variable_options, update_action_field, store } = useActionConfig(props);
const supportedTemplateModes = ["formula", "resolver", "link", "dynamic-link"];
const whenEditor = ref({ open: false, index: -1, draft: null });

// ─── Operator Helpers ────────────────────────────────────────────────────────

const OPERATOR_HINTS = {
	set: null,
	clear: "Clears the value without needing an input.",
	increment: "Adds the value to the current numeric total.",
	decrement: "Subtracts the value from the current numeric total.",
	append: "Appends the value to an existing list.",
	merge: "Merges an object into the current dictionary value.",
	toggle: "Flips a boolean field (0 ↔ 1) without needing an input.",
};

function needsValue(operator) {
	return ASSIGNMENT_OPERATOR_METADATA[operator]?.requires_value !== false;
}

function operatorNoValueHint(operator) {
	return OPERATOR_HINTS[operator] || __("No value input required for this operator.");
}

function getOperatorHint(operator) {
	return OPERATOR_HINTS[operator] || null;
}

/**
 * Resolve a Frappe fieldtype for a target path.
 * Reuses existing doctype_fields and variable_options arrays.
 */
function getTargetFieldtype(target) {
	if (!target) return null;
	if (target.startsWith("doc.")) {
		const fieldname = target.slice(4).split(".")[0];
		if (fieldname === "docstatus") return "Select";
		const field = (doctype_fields.value || []).find((f) => f.fieldname === fieldname);
		return field?.fieldtype || null;
	}
	if (target.startsWith("vars.")) {
		const varname = target.slice(5).split(".")[0];
		const variable = (variable_options.value || []).find(
			(v) => v.value === varname || v.fieldname === varname
		);
		return variable?.fieldtype || variable?.type || null;
	}
	return null;
}

function getTargetDoctype(target) {
	if (!target || !target.startsWith("doc.")) return null;
	const fieldname = target.slice(4).split(".")[0];
	const field = (doctype_fields.value || []).find((f) => f.fieldname === fieldname);
	return field?.options || null;
}

/**
 * Custom metadata target options list.
 */
function getTargetOptions(target) {
	if (!target) return [];
	if (target.startsWith("doc.")) {
		const fieldname = target.slice(4).split(".")[0];
		if (fieldname === "docstatus") {
			return [
				{ label: __("0 (Draft)"), value: "0" },
				{ label: __("1 (Submitted)"), value: "1" },
				{ label: __("2 (Cancelled)"), value: "2" },
			];
		}
		const field = (doctype_fields.value || []).find((f) => f.fieldname === fieldname);
		if (field && field.fieldtype === "Select" && field.options) {
			return field.options;
		}
	}
	return [];
}

/**
 * Target-aware operator filtering: the key architectural enhancement.
 */
function getAvailableOperators(target) {
	const fieldtype = getTargetFieldtype(target);

	const operatorIcons = {
		set: "fa fa-pencil",
		clear: "fa fa-eraser",
		increment: "fa fa-plus",
		decrement: "fa fa-minus",
		append: "fa fa-list-ul",
		merge: "fa fa-compress",
		toggle: "fa fa-toggle-on",
	};

	return Object.entries(ASSIGNMENT_OPERATOR_METADATA)
		.filter(([, meta]) => {
			if (!meta.supported_target_types.length) return true; // "all types"
			if (!fieldtype) return true; // vars.* or unknown – show all
			return meta.supported_target_types.includes(fieldtype);
		})
		.map(([key, meta]) => ({
			value: key,
			label: __(meta.label),
			icon: operatorIcons[key] || "fa fa-cog",
		}));
}

// ─── Assignments State ────────────────────────────────────────────────────────

const assignments = ref([]);

watch(
	() => props.node?.data?.config,
	(val) => {
		let parsed = [];
		if (typeof val === "string") {
			try {
				parsed = JSON.parse(val);
			} catch (e) {
				parsed = [];
			}
		} else if (Array.isArray(val)) {
			parsed = val;
		}

		// Map parsed to ensure both value_template and value are populated on load
		parsed = parsed.map((a) => {
			const value_tpl = a.value_template || a.value || "";
			// Auto-detect resolver mode: value_template_ui has a `kind` field (no `segments` array)
			const isResolverUi =
				a.value_template_ui &&
				typeof a.value_template_ui === "object" &&
				"kind" in a.value_template_ui &&
				!Array.isArray(a.value_template_ui.segments);
			return {
				target: a.target || "",
				operator: a.operator || "set",
				value_mode: isResolverUi ? "resolver" : "template",
				value_template_ui: a.value_template_ui || { version: 2, segments: [] },
				when_condition: a.when_condition || null,
				when_expression: a.when_expression || a.when || "",
				value_template: value_tpl,
				value: value_tpl,
			};
		});

		if (JSON.stringify(parsed) !== JSON.stringify(assignments.value)) {
			assignments.value = JSON.parse(JSON.stringify(parsed));
		}
	},
	{ immediate: true, deep: true }
);

// ─── Target options for ComboBox ─────────────────────────────────────────────

const targetOptions = computed(() => {
	const opts = [];

	// ── Context variables (vars.*) ────────────────────────────────────────────
	(variable_options.value || [])
		.filter((v) => v.is_variable)
		.forEach((v) => {
			opts.push({
				value: `vars.${v.value}`,
				label: `${v.label} (vars.${v.value})`,
				icon: "fa fa-code",
				fieldtype: v.fieldtype || "Variable",
				type: v.fieldtype || "Variable",
				is_variable: true,
				fieldname: v.value,
			});
		});

	// ── Doc fields (doc.*) ────────────────────────────────────────────────────
	(doctype_fields.value || []).forEach((f) => {
		opts.push({
			value: f.value,
			label: f.label,
			icon: f.icon || "fa fa-columns",
			fieldtype: f.fieldtype,
			type: f.fieldtype,
			fieldname: f.fieldname,
			options: f.options,
		});
	});

	return opts;
});

// ─── Mutations ────────────────────────────────────────────────────────────────

function syncToNode() {
	const clean = assignments.value.map((a) => ({
		target: a.target,
		operator: a.operator,
		value_mode: a.value_mode || "template",
		when_condition: a.when_condition || null,
		when_expression: a.when_condition ? "" : a.when_expression || "",
		value_template_ui: a.value_template_ui,
		value_template: a.value_template,
		value: a.value_template, // standardized output key alignment
	}));
	update_action_field("config", JSON.stringify(clean));
	store.mark_dirty();
}

function addAssignment() {
	assignments.value.push({
		target: "",
		operator: "set",
		value_mode: "template",
		when_condition: null,
		when_expression: "",
		value_template_ui: { version: 2, segments: [] },
		value_template: "",
		value: "",
	});
	syncToNode();
}

function removeAssignment(index) {
	assignments.value.splice(index, 1);
	syncToNode();
}

function moveAssignment(index, direction) {
	const newIndex = index + direction;
	if (newIndex < 0 || newIndex >= assignments.value.length) return;
	const item = assignments.value.splice(index, 1)[0];
	assignments.value.splice(newIndex, 0, item);
	syncToNode();
}

function clearAssignments() {
	frappe.confirm(__("Are you sure you want to clear all assignments?"), () => {
		assignments.value = [];
		syncToNode();
	});
}

function onTargetChange(index, value) {
	assignments.value[index].target = value;
	// Reset operator if it's no longer compatible with new target type
	const available = getAvailableOperators(value).map((o) => o.value);
	if (!available.includes(assignments.value[index].operator)) {
		assignments.value[index].operator = "set";
	}
	syncToNode();
}

function hasWhenCondition(assignment) {
	return !!(assignment?.when_condition && Array.isArray(assignment.when_condition.conditions));
}

const whenConditionDocFields = computed(() =>
	(doctype_fields.value || []).map((f) => ({
		label: f.label || f.fieldname,
		value: f.value || `doc.${f.fieldname}`,
		fieldname: f.fieldname,
		fieldtype: f.fieldtype,
		options: f.options,
	}))
);

function openWhenConditionEditor(index) {
	const current = assignments.value[index];
	const fallback = { op: "and", conditions: [] };
	whenEditor.value = {
		open: true,
		index,
		draft: JSON.parse(JSON.stringify(current?.when_condition || fallback)),
	};
}

function closeWhenConditionEditor() {
	whenEditor.value = { open: false, index: -1, draft: null };
}

function saveWhenCondition() {
	if (whenEditor.value.index < 0) return;
	const tree = whenEditor.value.draft;
	const hasConditions = !!(tree && Array.isArray(tree.conditions) && tree.conditions.length);
	assignments.value[whenEditor.value.index].when_condition = hasConditions ? tree : null;
	assignments.value[whenEditor.value.index].when_expression = "";
	syncToNode();
	closeWhenConditionEditor();
}

function clearWhenCondition() {
	if (whenEditor.value.index < 0) return;
	assignments.value[whenEditor.value.index].when_condition = null;
	assignments.value[whenEditor.value.index].when_expression = "";
	syncToNode();
	closeWhenConditionEditor();
}
function getDefaultResolverKind(target) {
	const fieldtype = getTargetFieldtype(target);
	if (!fieldtype) return "string_formula";

	if (["Int", "Float", "Percent", "Currency"].includes(fieldtype)) {
		return "math_formula";
	}
	if (["Date", "Datetime"].includes(fieldtype)) {
		return "date_formula";
	}
	return "string_formula";
}

function toggleValueMode(index) {
	const current = assignments.value[index].value_mode || "template";
	const next = current === "resolver" ? "template" : "resolver";
	assignments.value[index].value_mode = next;
	// Reset UI state when switching modes
	if (next === "resolver") {
		const defaultKind = getDefaultResolverKind(assignments.value[index].target);
		assignments.value[index].value_template_ui = { kind: defaultKind };
	} else {
		assignments.value[index].value_template_ui = { version: 2, segments: [] };
	}
	assignments.value[index].value_template = "";
	assignments.value[index].value = "";
	syncToNode();
}

function onOperatorChange(index, value) {
	assignments.value[index].operator = value;
	// Clear value template if operator no longer needs it
	if (!needsValue(value)) {
		assignments.value[index].value_template_ui = { version: 2, segments: [] };
		assignments.value[index].value_template = "";
		assignments.value[index].value = "";
	}
	syncToNode();
}

function compileStructuredValueToJinja(val) {
	if (!val) return "";
	if (val.mode === "static") {
		return String(val.value ?? "");
	}
	if (val.mode === "variable") {
		let path = val.path;
		if (path && !path.startsWith("vars.") && !path.startsWith("doc.")) {
			const isVar = (variable_options.value || []).some(
				(opt) => opt.value === path && opt.is_variable
			);
			path = isVar ? `vars.${path}` : `doc.${path}`;
		}
		return `{{ ${path} }}`;
	}
	if (val.mode === "formula") {
		return `{{ ${val.expression} }}`;
	}
	if (val.mode === "resolver") {
		const args = Object.entries(val.config || {})
			.map(([k, v]) => `${k}=${JSON.stringify(v)}`)
			.join(", ");
		return `{{ resolve("${val.resolver}", ${args}) }}`;
	}
	if (val.mode === "formatter") {
		return `{{ format(${JSON.stringify(val.formatter)}, ${JSON.stringify(val.options)}) }}`;
	}
	if (val.mode === "link" || val.mode === "dynamic_link") {
		return String(val.value ?? "");
	}
	return "";
}

/**
 * Compile ValueResolverControl structured state → Jinja {{ expr }} string.
 * Mirrors the expressionSnippet logic in ValueResolverControl.vue.
 */
function compileValueResolverToJinja(s) {
	if (!s || !s.kind) return "";

	if (s.kind === "date_formula") {
		const baseExpr = s.base_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.base_field}`;
		const offset =
			s.offset_sign === "-" ? -Math.abs(s.offset_value || 0) : Math.abs(s.offset_value || 0);
		if (offset === 0) return `{{ ${baseExpr} }}`;
		if (s.offset_unit === "days") return `{{ frappe.utils.add_days(${baseExpr}, ${offset}) }}`;
		return `{{ frappe.utils.add_to_date(${baseExpr}, ${s.offset_unit}=${offset}) }}`;
	}

	if (s.kind === "math_formula") {
		const a = s.field_a ? `frappe.utils.flt(doc.${s.field_a})` : "0";
		const b =
			s.field_b_type === "field"
				? s.field_b
					? `frappe.utils.flt(doc.${s.field_b})`
					: "0"
				: String(s.constant_b ?? 0);
		const prec = s.precision ?? 2;
		return `{{ frappe.utils.flt(${a} ${s.math_op || "+"} ${b}, ${prec}) }}`;
	}

	if (s.kind === "date_diff") {
		const start =
			s.diff_start_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.diff_start_field}`;
		const end =
			s.diff_end_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.diff_end_field}`;
		if (s.diff_unit === "days") return `{{ frappe.utils.date_diff(${end}, ${start}) }}`;
		if (s.diff_unit === "months") return `{{ frappe.utils.month_diff(${end}, ${start}) }}`;
		return `{{ int(frappe.utils.month_diff(${end}, ${start}) / 12) }}`;
	}

	if (s.kind === "child_aggregation") {
		const tbl = s.agg_table || "items";
		const fld = s.agg_field || "amount";
		if (s.agg_op === "sum")
			return `{{ sum([frappe.utils.flt(row.${fld}) for row in doc.get("${tbl}")]) }}`;
		if (s.agg_op === "avg")
			return `{{ sum([frappe.utils.flt(row.${fld}) for row in doc.get("${tbl}")]) / max(len(doc.get("${tbl}")), 1) }}`;
		if (s.agg_op === "count") return `{{ len(doc.get("${tbl}")) }}`;
	}

	if (s.kind === "string_formula") {
		const a = s.str_a_type === "field" ? `doc.${s.str_a || ""}` : `"${s.str_a || ""}"`;
		if (s.str_op === "concat") {
			const b = s.str_b_type === "field" ? `doc.${s.str_b || ""}` : `"${s.str_b || ""}"`;
			return `{{ str(${a} or "") + str(${b} or "") }}`;
		}
		if (s.str_op === "fmt_money") {
			const curr = s.str_b_type === "field" ? `doc.${s.str_b || ""}` : `"${s.str_b || ""}"`;
			return `{{ frappe.utils.fmt_money(${a}, currency=${curr}) }}`;
		}
		if (s.str_op === "uppercase") return `{{ str(${a} or "").upper() }}`;
		if (s.str_op === "lowercase") return `{{ str(${a} or "").lower() }}`;
	}

	if (s.kind === "system_context") {
		if (s.sys_token === "user") return `{{ frappe.session.user }}`;
		if (s.sys_token === "role_check")
			return `{{ "${s.sys_role || ""}" in frappe.get_roles(frappe.session.user) }}`;
	}

	return "";
}

/**
 * Handler for ValueResolverControl updates.
 */
function updateResolverTemplate(index, value) {
	assignments.value[index].value_template_ui = value;
	const compiled = compileValueResolverToJinja(value);
	assignments.value[index].value_template = compiled;
	assignments.value[index].value = compiled;
	syncToNode();
}

function updateTemplate(index, value) {
	assignments.value[index].value_template_ui = value;

	let compiled = "";
	if (value && typeof value === "object" && "mode" in value) {
		compiled = compileStructuredValueToJinja(value);
	} else if (value && typeof value === "object" && Array.isArray(value.segments)) {
		const knownVarRoots = (variable_options.value || [])
			.map((v) => String(v?.value || ""))
			.filter((p) => p.startsWith("vars."))
			.map((p) => p.slice(5).split(".")[0]);
		compiled = compileSegmentsToJinja(value.segments, { knownVarRoots });
	} else {
		compiled = String(value || "");
	}

	assignments.value[index].value_template = compiled;
	assignments.value[index].value = compiled;
	syncToNode();
}

// ─── Validation ──────────────────────────────────────────────────────────────

function validate() {
	const errors = [];
	assignments.value.forEach((a, idx) => {
		const n = idx + 1;
		if (!a.target) errors.push(__(`Assignment #${n}: Target is required`));
		if (!a.operator) errors.push(__(`Assignment #${n}: Operator is required`));
		if (needsValue(a.operator)) {
			const ui = a.value_template_ui;
			if (!ui || (!Array.isArray(ui.segments) && !ui.mode)) {
				errors.push(
					__(`Assignment #${n}: Value Template is required for operator '${a.operator}'`)
				);
			}
		}
		// Target path validation
		if (a.target && !a.target.startsWith("doc.") && !a.target.startsWith("vars.")) {
			errors.push(__(`Assignment #${n}: Target must start with 'doc.' or 'vars.'`));
		}
	});
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.assignment-config {
	display: flex;
	flex-direction: column;
}

.section-card {
	border: 1px solid var(--border-color, #e2e8f0);
	border-radius: 8px;
	padding: 12px;
	background: var(--bg-light, #fff);
}

.header-compact {
	background: var(--gray-50, #f8fafc);
}

/* Horizontal Table Grid Styling */
.assignment-grid-header,
.assignment-grid-row {
	display: grid;
	grid-template-columns:
		minmax(180px, 1.2fr) minmax(110px, 0.8fr) minmax(220px, 2fr) minmax(120px, 1fr)
		100px;
	gap: 12px;
	align-items: center;
}

.when-editor-cell {
	display: flex;
	flex-direction: column;
}

.fxr-modal-overlay {
	position: fixed;
	inset: 0;
	background: rgba(15, 23, 42, 0.35);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 13000;
}

.fxr-modal-card {
	width: min(980px, 92vw);
	max-height: 86vh;
	background: #fff;
	border-radius: 10px;
	border: 1px solid #e2e8f0;
	padding: 14px;
	overflow: hidden;
	display: flex;
	flex-direction: column;
}

.condition-builder-wrap {
	overflow: auto;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	padding: 8px;
}

/* Value mode toggle + control wrapper */
.value-mode-wrap {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
}

.value-mode-toggle {
	flex-shrink: 0;
	width: 32px;
	height: 32px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 6px;
	color: #64748b;
	border: 1px solid #e2e8f0;
	background: #ffffff;
	transition: all 0.2s ease;
	cursor: pointer;
}

.value-mode-toggle:hover:not(:disabled) {
	color: var(--primary, #1e293b);
	border-color: #cbd5e1;
	background: #f8fafc;
}

.assignment-grid-header {
	padding: 8px 12px;
	font-size: 11px;
	font-weight: 600;
	color: #64748b;
	letter-spacing: 0.02em;
	border-bottom: 1px solid #e2e8f0;
	margin-bottom: 8px !important;
}

.assignment-grid-row {
	background: #ffffff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	padding: 8px 12px;
	transition: all 0.2s ease;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

.assignment-grid-row:hover {
	border-color: var(--primary, #1e293b);
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
	transform: translateY(-1px);
}

.operator-hint-text {
	display: flex;
	align-items: center;
	padding: 6px 12px;
	background: #f8fafc;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	height: 32px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.empty-state {
	border: 2px dashed var(--fxr-border, #e2e8f0);
	border-radius: var(--fxr-radius-lg, 12px);
	background-color: var(--fxr-bg-muted, #f8fafc);
	transition: all 0.2s ease;
	flex: 0 0 auto;
}

.empty-state:hover {
	border-color: var(--fxr-border-strong);
	background-color: var(--fxr-bg-hover);
}

.add-assignment-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
	background: #f8fafc;
	border: 1px dashed #cbd5e1;
	border-radius: 8px;
	padding: 10px;
	width: 100%;
	color: #475569;
	font-weight: 500;
	transition: all 0.2s ease;
	cursor: pointer;
}

.add-assignment-btn:hover:not(:disabled) {
	background: #f1f5f9;
	border-color: var(--primary, #1e293b);
	color: var(--primary, #1e293b);
}
</style>
