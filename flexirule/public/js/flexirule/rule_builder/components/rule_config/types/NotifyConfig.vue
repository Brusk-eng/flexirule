<template>
	<div class="notify-config">
		<div v-if="!props.node?.data?.operation" class="empty-mode-state text-center p-5">
			<i class="fa fa-bell fa-3x text-muted mb-3 opacity-20"></i>
			<p class="text-muted">
				{{ __("Please select a Notification Type in the Setup panel to proceed.") }}
			</p>
		</div>

		<div v-else class="config-container">
			<div class="config-section section-card">
				<div class="form-group mb-3">
					<label class="form-label"
						>{{ __("Message Template") }} <span class="text-danger">*</span></label
					>
					<ControlFactory
						:df="with_read_only(valueTemplateField)"
						:modelValue="props.node?.data?.value_template"
						@update:modelValue="(val) => update_action_field('value_template', val)"
					/>
					<small class="text-muted">
						{{
							__("Jinja template for message. Use {0}, {1}, etc.", [
								double_left + " doc.name " + double_right,
								double_left + " vars.result " + double_right,
							])
						}}
					</small>
				</div>

				<div class="form-group mb-3" v-if="props.node?.data?.operation === 'email'">
					<label class="form-label">{{ __("Recipients") }}</label>
					<ControlFactory
						:df="with_read_only(recipientsField)"
						:modelValue="props.node?.data?.recipients"
						@update:modelValue="(val) => update_action_field('recipients', val)"
					/>
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

				<div class="preview-section mt-4" v-if="props.node?.data?.value_template">
					<label class="form-label text-muted small uppercase font-weight-bold">{{
						__("Preview")
					}}</label>
					<div
						class="notify-preview"
						:class="'type-' + (props.node?.data?.operation || 'toast')"
					>
						<i :class="preview_icon"></i>
						<span>{{ preview_text }}</span>
					</div>
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


const valueTemplateField = {
	fieldname: "value_template",
	fieldtype: "Code",
	label: __("Message Template"),
	options: "Jinja",
	rows: 4,
	reqd: 1,
};

const recipientsField = {
	fieldname: "recipients",
	fieldtype: "Data",
	label: "",
	placeholder: __("Comma-separated emails or Jinja template"),
};

const helpers = [
	{ label: "doc.name", value: "{{ doc.name }}" },
	{ label: "owner", value: "{{ doc.owner }}" },
	{ label: "user", value: "{{ frappe.session.user }}" },
];

const preview_icon = computed(() => {
	const icons = {
		toast: "fa fa-check-circle",
		alert: "fa fa-info-circle",
		realtime: "fa fa-bell",
		email: "fa fa-envelope",
	};
	return icons[props.node?.data?.operation || "toast"] || "fa fa-bell";
});

const preview_text = computed(() => {
	return props.node?.data?.notification_template?.replace(/\{\{[^}]+\}\}/g, "[...]") || "";
});

function insert_template(text) {
	const current = props.node?.data?.notification_template || "";
	update_action_field("notification_template", current + text);
}

function validate() {
	const errors = [];
	if (!props.node?.data?.notification_template) {
		errors.push(__("Notification Message Template is required"));
	}
	if (props.node?.data?.notification_type === "email" && !props.node?.data?.recipients) {
		errors.push(__("Recipients are required for email notifications"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.notify-config {
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

.notify-preview {
	border-radius: 6px;
	padding: 12px;
	display: flex;
	align-items: flex-start;
	gap: 10px;
	font-size: 13px;
}

.notify-preview.type-toast {
	background: #ecfdf5;
	border: 1px solid #a7f3d0;
	color: #047857;
}

.notify-preview.type-alert {
	background: #eff6ff;
	border: 1px solid #bfdbfe;
	color: #1d4ed8;
}

.notify-preview.type-realtime {
	background: #fef3c7;
	border: 1px solid #fcd34d;
	color: #b45309;
}

.notify-preview.type-email {
	background: #f3f4f6;
	border: 1px solid #d1d5db;
	color: #374151;
}

.notify-preview i {
	margin-top: 2px;
}

.uppercase {
	text-transform: uppercase;
	letter-spacing: 0.025em;
}
</style>
