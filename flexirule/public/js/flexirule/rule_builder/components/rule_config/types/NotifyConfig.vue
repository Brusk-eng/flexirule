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
				<div v-if="is_email" class="form-group mb-3">
					<label class="form-label"
						>{{ __("Subject") }} <span class="text-danger">*</span></label
					>
					<ControlFactory
						:df="with_read_only(subjectField)"
						:modelValue="config.subject"
						@update:modelValue="(val) => update_config_key('subject', val)"
					/>
				</div>

				<div v-if="is_email" class="form-group mb-3">
					<label class="form-label"
						>{{ __("Recipients") }} <span class="text-danger">*</span></label
					>
					<ControlFactory
						:df="with_read_only(recipientsField)"
						:modelValue="config.recipients"
						@update:modelValue="(val) => update_config_key('recipients', val)"
					/>
				</div>

				<div v-if="is_system_notification" class="form-group mb-3">
					<label class="form-label"
						>{{ __("Subject") }} <span class="text-danger">*</span></label
					>
					<ControlFactory
						:df="with_read_only(subjectField)"
						:modelValue="config.subject"
						@update:modelValue="(val) => update_config_key('subject', val)"
					/>
				</div>

				<div v-if="is_system_notification" class="form-group mb-3">
					<label class="form-label">{{ __("For User") }}</label>
					<ControlFactory
						:df="with_read_only(forUserField)"
						:modelValue="config.for_user"
						@update:modelValue="(val) => update_config_key('for_user', val)"
					/>
					<small class="text-muted">
						{{
							__(
								"Leave blank to default to the document owner or current session user."
							)
						}}
					</small>
				</div>

				<div v-if="is_provider" class="form-group mb-3">
					<label class="form-label"
						>{{ __("Provider") }} <span class="text-danger">*</span></label
					>
					<ControlFactory
						:df="with_read_only(providerField)"
						:modelValue="config.provider"
						@update:modelValue="(val) => update_config_key('provider', val)"
					/>
				</div>

				<div v-if="is_provider" class="form-group mb-3">
					<label class="form-label"
						>{{ __("Recipient") }} <span class="text-danger">*</span></label
					>
					<ControlFactory
						:df="with_read_only(recipientField)"
						:modelValue="config.recipient"
						@update:modelValue="(val) => update_config_key('recipient', val)"
					/>
				</div>

				<div class="form-group mb-3">
					<label class="form-label"
						>{{ body_label }} <span class="text-danger">*</span></label
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

				<div v-if="is_email" class="form-group mb-3">
					<label class="form-label">{{ __("Attach Document PDF") }}</label>
					<ControlFactory
						:df="with_read_only(attachDocField)"
						:modelValue="config.attach_doc"
						@update:modelValue="(val) => update_config_key('attach_doc', val)"
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
					<div class="notify-preview" :class="preview_class">
						<i :class="preview_icon"></i>
						<span>{{ preview_text }}</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { config, with_read_only, update_action_field, sync_config } = useActionConfig(props);

const double_left = "{{";
const double_right = "}}";
const EMAIL_MODE = "Email";
const SYSTEM_NOTIFICATION_MODE = "System Notification";
const PROVIDER_MODE = "Provider";

const valueTemplateField = {
	fieldname: "value_template",
	fieldtype: "Code",
	label: __("Body Template"),
	options: "Jinja",
	rows: 4,
	reqd: 1,
};

const subjectField = {
	fieldname: "subject",
	fieldtype: "Data",
	label: __("Subject"),
	reqd: 1,
};

const recipientsField = {
	fieldname: "recipients",
	fieldtype: "Small Text",
	label: __("Recipients"),
	reqd: 1,
	description: __("One email per line, comma-separated values, or a Jinja template."),
};

const forUserField = {
	fieldname: "for_user",
	fieldtype: "Link",
	label: __("For User"),
	options: "User",
};

const attachDocField = {
	fieldname: "attach_doc",
	fieldtype: "Check",
	label: __("Attach Document PDF"),
};

const providerField = {
	fieldname: "provider",
	fieldtype: "Data",
	label: __("Provider"),
	reqd: 1,
	description: __("Hook key registered in flexirule_notification_providers."),
};

const recipientField = {
	fieldname: "recipient",
	fieldtype: "Data",
	label: __("Recipient"),
	reqd: 1,
};

const helpers = [
	{ label: "doc.name", value: "{{ doc.name }}" },
	{ label: "owner", value: "{{ doc.owner }}" },
	{ label: "user", value: "{{ frappe.session.user }}" },
];

const notify_mode = computed(() => props.node?.data?.operation || "");
const is_email = computed(() => notify_mode.value === EMAIL_MODE);
const is_system_notification = computed(() => notify_mode.value === SYSTEM_NOTIFICATION_MODE);
const is_provider = computed(() => notify_mode.value === PROVIDER_MODE);

const body_label = computed(() => {
	if (is_email.value) return __("Email Body");
	if (is_system_notification.value) return __("Notification Message");
	if (is_provider.value) return __("Provider Message");
	return __("Message Template");
});

const preview_icon = computed(() => {
	const icons = {
		Toast: "fa fa-check-circle",
		System: "fa fa-bell",
		Email: "fa fa-envelope",
		"System Notification": "fa fa-list-alt",
		Provider: "fa fa-paper-plane",
	};
	return icons[notify_mode.value || "Toast"] || "fa fa-bell";
});

const preview_text = computed(() => {
	return props.node?.data?.value_template?.replace(/\{\{[^}]+\}\}/g, "[...]") || "";
});

const preview_class = computed(() => {
	const mode = notify_mode.value || "Toast";
	return `type-${mode.toLowerCase().replace(/\s+/g, "-")}`;
});

function insert_template(text) {
	const current = props.node?.data?.value_template || "";
	update_action_field("value_template", current + text);
}

function update_config_key(key, value) {
	config[key] = value;
	sync_local_config();
}

function sync_local_config() {
	const new_config = {};
	Object.entries(config).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== "") {
			new_config[key] = value;
		}
	});
	sync_config(new_config);
}

function load_local_config(val) {
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

	Object.keys(config).forEach((key) => delete config[key]);
	Object.assign(config, parsed);
}

function validate() {
	const errors = [];
	if (!props.node?.data?.value_template) {
		errors.push(__("Notification message/body is required"));
	}
	if (is_email.value) {
		if (!config.subject) errors.push(__("Subject is required for email notifications"));
		if (!config.recipients) errors.push(__("Recipients are required for email notifications"));
	}
	if (is_system_notification.value && !config.subject) {
		errors.push(__("Subject is required for system notifications"));
	}
	if (is_provider.value) {
		if (!config.provider) errors.push(__("Provider is required for provider notifications"));
		if (!config.recipient) errors.push(__("Recipient is required for provider notifications"));
	}
	return { valid: errors.length === 0, errors };
}

watch(
	() => props.node?.data?.config,
	(val) => {
		load_local_config(val);
	},
	{ immediate: true, deep: true }
);

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

.notify-preview.type-system {
	background: #fef3c7;
	border: 1px solid #fcd34d;
	color: #b45309;
}

.notify-preview.type-system-notification {
	background: #eff6ff;
	border: 1px solid #bfdbfe;
	color: #1d4ed8;
}

.notify-preview i {
	margin-top: 2px;
}

.uppercase {
	text-transform: uppercase;
	letter-spacing: 0.025em;
}
</style>
