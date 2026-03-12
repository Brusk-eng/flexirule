<template>
	<div class="set-value-config">
		<div class="config-section section-card">
			<h5>{{ __("Set Value Configuration") }}</h5>
			<p class="text-muted small">
				{{ __("Configure the target field and the value to set using Jinja.") }}
			</p>
		</div>

		<div class="config-section section-card">
			<div class="form-group mb-3">
				<label class="form-label"
					>{{ __("Target Field") }} <span class="text-danger">*</span></label
				>
				<FieldPickerControl
					:df="with_read_only({ label: '' })"
					:fields="doctype_fields"
					:documentType="reference_doctype || store.rule_doc?.document_type"
					:modelValue="props.node?.data?.target_field"
					:read_only="readOnly"
					@update:modelValue="(val) => update_action_field('target_field', val)"
				/>
				<small class="text-muted">{{
					__("The document field that will be updated")
				}}</small>
			</div>

			<div class="form-group mb-3">
				<label class="form-label"
					>{{ __("Value Template") }} <span class="text-danger">*</span></label
				>
				<ControlFactory
					:df="with_read_only(valueTemplateField)"
					:modelValue="props.node?.data?.value_template"
					@update:modelValue="(val) => update_action_field('value_template', val)"
				/>
				<small class="text-muted">
					{{
						__("Jinja template. Use {0}, {1}, etc.", [
							double_left + " doc.fieldname " + double_right,
							double_left + " vars.variable " + double_right,
						])
					}}
				</small>
			</div>

			<div class="template-helpers">
				<span class="helper-label">{{ __("Quick Insert:") }}</span>
				<button
					v-for="helper in helpers"
					:key="helper.label"
					class="btn btn-xs btn-outline-secondary"
					:disabled="readOnly"
					@click="insert_template(helper.value)"
				>
					{{ helper.label }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import FieldPickerControl from "../../../controls/FieldPickerControl.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { store, doctype_fields, reference_doctype, with_read_only, update_action_field } =
	useActionConfig(props);

const double_left = "{{";
const double_right = "}}";

const valueTemplateField = {
	fieldname: "value_template",
	fieldtype: "Code",
	label: "",
	options: "Jinja",
	rows: 5,
};

const helpers = [
	{ label: "doc.name", value: "{{ doc.name }}" },
	{ label: "now()", value: "{{ frappe.utils.now() }}" },
	{ label: "user", value: "{{ frappe.session.user }}" },
];

function insert_template(text) {
	const current = props.node?.data?.value_template || "";
	update_action_field("value_template", current + text);
}

function validate() {
	const errors = [];
	if (!props.node?.data?.target_field) {
		errors.push(__("Target Field is required"));
	}
	if (!props.node?.data?.value_template) {
		errors.push(__("Value Template is required"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.set-value-config {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.section-card {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 16px;
	background: var(--bg-light, #fff);
}

.form-label {
	font-weight: 500;
	margin-bottom: 6px;
	display: block;
	font-size: 13px;
}

.template-helpers {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-top: 12px;
	flex-wrap: wrap;
}

.helper-label {
	font-size: 12px;
	color: var(--text-muted);
}
</style>
