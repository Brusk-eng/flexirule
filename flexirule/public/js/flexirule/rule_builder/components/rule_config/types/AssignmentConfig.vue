<template>
	<div class="assignment-config">
		<div class="config-section section-card header-compact mb-3">
			<div class="d-flex align-items-center justify-content-between">
				<h5 class="mb-0">{{ __("Batch Assignments") }}</h5>
				<span class="text-muted small">{{
					__("Sequential state mutations applied in order")
				}}</span>
			</div>
		</div>

		<div class="assignments-list">
			<div
				v-for="(assignment, index) in assignments"
				:key="index"
				class="assignment-row section-card mb-3"
			>
				<div class="d-flex justify-content-between align-items-center mb-2">
					<span class="row-label text-muted small fw-semibold">
						<i class="fa fa-bars me-1 cursor-grab" title="Sequence order"></i>
						{{ __("Assignment") }} #{{ index + 1 }}
					</span>
					<button
						class="btn btn-xs btn-outline-danger"
						@click="removeAssignment(index)"
						:disabled="readOnly"
						:title="__('Remove')"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>

				<!-- Target + Operator row -->
				<div class="row gx-2 mb-2">
					<div class="col-sm-6">
						<label class="form-label small">
							{{ __("Target") }} <span class="text-danger">*</span>
						</label>
						<ComboBoxControl
							:df="{ fieldtype: 'Autocomplete', label: '' }"
							:modelValue="assignment.target"
							:get_query="async () => targetOptions"
							:read_only="readOnly"
							:hideLabel="true"
							:placeholder="__('doc.field or vars.variable')"
							@update:modelValue="(val) => onTargetChange(index, val)"
						/>
						<small
							v-if="getTargetFieldtype(assignment.target)"
							class="text-muted fieldtype-badge"
						>
							<i class="fa fa-tag"></i>
							{{ getTargetFieldtype(assignment.target) }}
						</small>
					</div>
					<div class="col-sm-6">
						<label class="form-label small">
							{{ __("Operator") }} <span class="text-danger">*</span>
						</label>
						<select
							class="form-control form-control-sm"
							:value="assignment.operator"
							@change="(e) => onOperatorChange(index, e.target.value)"
							:disabled="readOnly"
						>
							<option
								v-for="op in getAvailableOperators(assignment.target)"
								:key="op.value"
								:value="op.value"
							>
								{{ op.label }}
							</option>
						</select>
						<small v-if="getOperatorHint(assignment.operator)" class="text-muted">{{
							getOperatorHint(assignment.operator)
						}}</small>
					</div>
				</div>

				<!-- Value Template (hidden for 'clear' and 'toggle') -->
				<div v-if="needsValue(assignment.operator)" class="mt-2">
					<label class="form-label small">
						{{ __("Value Template") }} <span class="text-danger">*</span>
					</label>
					<TextGeneratorControl
						:df="{ fieldtype: 'Text Generator', label: '' }"
						:modelValue="assignment.value_template_ui"
						:read_only="readOnly"
						:variableOptions="variable_options"
						:docFieldOptions="doctype_fields"
						@update:modelValue="(val) => updateTemplate(index, val)"
					/>
				</div>
				<div v-else class="mt-1">
					<small class="text-muted fst-italic">
						<i class="fa fa-info-circle"></i>
						{{ operatorNoValueHint(assignment.operator) }}
					</small>
				</div>
			</div>
		</div>

		<div v-if="!assignments.length" class="empty-state text-center text-muted py-4">
			<i class="fa fa-list-ol fa-2x mb-2 d-block"></i>
			<p class="small">{{ __("No assignments defined. Add one below.") }}</p>
		</div>

		<button
			class="btn btn-sm btn-default w-100 mt-2"
			@click="addAssignment"
			:disabled="readOnly"
		>
			<i class="fa fa-plus me-1"></i> {{ __("Add Assignment") }}
		</button>
	</div>
</template>

<script setup>
import { computed, watch, ref } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import TextGeneratorControl from "../../../controls/TextGeneratorControl.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";
import { ASSIGNMENT_OPERATOR_METADATA } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { doctype_fields, variable_options, update_action_field, store } = useActionConfig(props);

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
 * For doc.* paths: looks up meta. For vars.*: unknown (returns null).
 */
function getTargetFieldtype(target) {
	if (!target || !target.startsWith("doc.")) return null;
	const fieldname = target.slice(4).split(".")[0];
	const field = (doctype_fields.value || []).find((f) => f.fieldname === fieldname);
	return field?.fieldtype || null;
}

/**
 * Target-aware operator filtering: the key architectural enhancement.
 * Empty `supported_target_types` means "all types".
 */
function getAvailableOperators(target) {
	const fieldtype = getTargetFieldtype(target);

	return Object.entries(ASSIGNMENT_OPERATOR_METADATA)
		.filter(([, meta]) => {
			if (!meta.supported_target_types.length) return true; // "all types"
			if (!fieldtype) return true; // vars.* or unknown – show all
			return meta.supported_target_types.includes(fieldtype);
		})
		.map(([key, meta]) => ({ value: key, label: __(meta.label) }));
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
		if (JSON.stringify(parsed) !== JSON.stringify(assignments.value)) {
			assignments.value = JSON.parse(JSON.stringify(parsed));
		}
	},
	{ immediate: true, deep: true }
);

// ─── Target options for ComboBox ─────────────────────────────────────────────

const targetOptions = computed(() => {
	const opts = [];

	// Context variables (vars.*)
	(variable_options.value || [])
		.filter((v) => v.is_variable)
		.forEach((v) => {
			opts.push({
				value: `vars.${v.value}`,
				label: `[Var] ${v.label}`,
			});
		});

	// Doc fields (doc.*)
	(doctype_fields.value || []).forEach((f) => {
		opts.push({
			value: `doc.${f.fieldname}`,
			label: `[Doc] ${f.label} (${f.fieldname})`,
		});
	});

	return opts;
});

// ─── Mutations ────────────────────────────────────────────────────────────────

function syncToNode() {
	const clean = assignments.value.map((a) => ({
		target: a.target,
		operator: a.operator,
		value_template_ui: a.value_template_ui,
		value_template: a.value_template,
	}));
	update_action_field("config", JSON.stringify(clean));
	store.mark_dirty();
}

function addAssignment() {
	assignments.value.push({
		target: "",
		operator: "set",
		value_template_ui: { version: 2, segments: [] },
		value_template: "",
	});
	syncToNode();
}

function removeAssignment(index) {
	assignments.value.splice(index, 1);
	syncToNode();
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

function onOperatorChange(index, value) {
	assignments.value[index].operator = value;
	// Clear value template if operator no longer needs it
	if (!needsValue(value)) {
		assignments.value[index].value_template_ui = { version: 2, segments: [] };
		assignments.value[index].value_template = "";
	}
	syncToNode();
}

function updateTemplate(index, value) {
	assignments.value[index].value_template_ui = value;

	const knownVarRoots = (variable_options.value || [])
		.map((v) => String(v?.value || ""))
		.filter((p) => p.startsWith("vars."))
		.map((p) => p.slice(5).split(".")[0]);

	assignments.value[index].value_template = compileSegmentsToJinja(value?.segments || [], {
		knownVarRoots,
	});
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
			if (!ui || !Array.isArray(ui.segments) || !ui.segments.length) {
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
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 12px;
	background: var(--bg-light, #fff);
}

.header-compact {
	background: var(--gray-50, #f8fafc);
}

.assignment-row {
	transition: box-shadow 0.15s ease;
}

.assignment-row:hover {
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.cursor-grab {
	cursor: grab;
	color: var(--text-muted);
	opacity: 0.6;
}

.row-label {
	display: flex;
	align-items: center;
	gap: 4px;
	font-size: 11px;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}

.fieldtype-badge {
	display: inline-block;
	margin-top: 3px;
	font-size: 10px;
	gap: 3px;
	color: var(--text-muted);
}

.empty-state {
	border: 1px dashed var(--border-color);
	border-radius: 8px;
}

.form-label {
	font-weight: 500;
	font-size: 12px;
	margin-bottom: 4px;
	display: block;
	color: var(--text-muted);
}
</style>
