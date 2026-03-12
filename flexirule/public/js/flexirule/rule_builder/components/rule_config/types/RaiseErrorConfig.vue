<template>
	<div class="raise-error-config">
		<div class="config-section section-card">
			<h5>{{ __("Raise Error Configuration") }}</h5>
			<p class="text-muted small">
				{{ __("This action will stop rule execution and throw an error.") }}
			</p>
		</div>

		<div class="config-section section-card">
			<div class="terminal-warning mb-4">
				<i class="fa fa-exclamation-triangle"></i>
				<span>{{
					__("Critical: Stops all further processing of the current rule flow.")
				}}</span>
			</div>

			<div class="form-group mb-3">
				<label class="form-label"
					>{{ __("Error Message Template") }} <span class="text-danger">*</span></label
				>
				<ControlFactory
					:df="with_read_only(errorTemplateField)"
					:modelValue="props.node?.data?.error_template"
					@update:modelValue="(val) => update_action_field('error_template', val)"
				/>
				<small class="text-muted">
					{{
						__("Jinja template for error message. Use {0}, {1}, etc.", [
							double_left + " doc.name " + double_right,
							double_left + " vars.result " + double_right,
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

			<div class="preview-section mt-4" v-if="props.node?.data?.error_template">
				<label class="form-label text-muted small uppercase font-weight-bold">{{
					__("Preview")
				}}</label>
				<div class="error-preview">
					<i class="fa fa-times-circle"></i>
					<span>{{ preview_text }}</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { with_read_only, update_action_field } = useActionConfig(props);

const double_left = "{{";
const double_right = "}}";

const errorTemplateField = {
	fieldname: "error_template",
	fieldtype: "Code",
	label: "",
	options: "Jinja",
	rows: 5,
};

const helpers = [
	{ label: "doc.name", value: "{{ doc.name }}" },
	{ label: "doctype", value: "{{ doc.doctype }}" },
	{ label: "owner", value: "{{ doc.owner }}" },
];

const preview_text = computed(() => {
	return props.node?.data?.error_template?.replace(/\{\{[^}]+\}\}/g, "[...]") || "";
});

function insert_template(text) {
	const current = props.node?.data?.error_template || "";
	update_action_field("error_template", current + text);
}

function validate() {
	const errors = [];
	if (!props.node?.data?.error_template) {
		errors.push(__("Error Message Template is required"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.raise-error-config {
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

.terminal-warning {
	background: #fff5f5;
	border: 1px solid #feb2b2;
	border-radius: 6px;
	padding: 12px;
	color: #c53030;
	display: flex;
	align-items: center;
	gap: 10px;
	font-size: 13px;
	font-weight: 500;
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

.error-preview {
	background: #fff5f5;
	border: 1px solid #feb2b2;
	border-radius: 6px;
	padding: 12px;
	color: #c53030;
	display: flex;
	align-items: flex-start;
	gap: 10px;
	font-size: 13px;
}

.error-preview i {
	margin-top: 2px;
}

.uppercase {
	text-transform: uppercase;
	letter-spacing: 0.025em;
}
</style>
