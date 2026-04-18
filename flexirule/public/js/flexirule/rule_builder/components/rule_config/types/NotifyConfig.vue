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
					<TextGeneratorControl
						:df="with_read_only(textGeneratorField)"
						:modelValue="config.text_generator_ui"
						:read_only="readOnly"
						:variableOptions="variable_options"
						@update:modelValue="update_template_ui"
					/>
				</div>

				<div v-if="is_email" class="form-group mb-3">
					<label class="form-label">{{ __("Attach Document PDF") }}</label>
					<ControlFactory
						:df="with_read_only(attachDocField)"
						:modelValue="config.attach_doc"
						@update:modelValue="(val) => update_config_key('attach_doc', val)"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import TextGeneratorControl from "../../../controls/TextGeneratorControl.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { config, variable_options, with_read_only, sync_config, update_action_field } =
	useActionConfig(props);

const EMAIL_MODE = "Email";
const SYSTEM_NOTIFICATION_MODE = "System Notification";
const PROVIDER_MODE = "Provider";

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
};

const recipientField = {
	fieldname: "recipient",
	fieldtype: "Data",
	label: __("Recipient"),
	reqd: 1,
};

const textGeneratorField = {
	fieldname: "text_generator_ui",
	fieldtype: "Text Generator",
	label: __("Message Builder"),
	reqd: 1,
};

const notify_mode = computed(() => props.node?.data?.operation || "");
const is_email = computed(() => notify_mode.value === EMAIL_MODE);
const is_system_notification = computed(() => notify_mode.value === SYSTEM_NOTIFICATION_MODE);
const is_provider = computed(() => notify_mode.value === PROVIDER_MODE);

function update_template_ui(value) {
	config.text_generator_ui = value;
	const jinja = compileSegmentsToJinja(value?.segments || []);
	update_action_field("value_template", jinja);
	sync_local_config();
}

function update_config_key(key, value) {
	config[key] = value;
	sync_local_config();
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

	// Backwards compat: value_template
	if (!parsed.text_generator_ui && props.node?.data?.value_template) {
		parsed.text_generator_ui = {
			version: 2,
			segments: [{ type: "text", content: props.node.data.value_template }],
		};
	}

	// Compare with current local state to avoid re-triggering watchers
	const current_str = JSON.stringify(config);
	const next_str = JSON.stringify(parsed);
	if (current_str === next_str) return;

	Object.keys(config).forEach((key) => delete config[key]);
	Object.assign(config, parsed);
}

function sync_local_config() {
	const new_config = {};
	Object.entries(config).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== "") {
			new_config[key] = value;
		}
	});

	// sync_config in useActionConfig already performs a string compare against props.node.data.config
	sync_config(new_config);
}

watch(
	() => props.node?.data?.config,
	(val) => {
		load_local_config(val);
	},
	{ immediate: true, deep: true }
);

function validate() {
	const errors = [];
	const ui = config.text_generator_ui;
	if (!ui || !Array.isArray(ui.segments) || !ui.segments.length) {
		errors.push(__("Message Builder content is required"));
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
</style>
