<template>
	<div class="notify-config">
		<div class="config-section">
			<h5>{{ __("Notify Configuration") }}</h5>

			<div class="form-group mb-3">
				<label class="form-label">{{ __("Notification Type") }}</label>
				<select v-model="notificationType" class="form-control form-select">
					<option value="toast">{{ __("Toast Message") }}</option>
					<option value="alert">{{ __("Alert Dialog") }}</option>
					<option value="realtime">{{ __("Realtime Push") }}</option>
					<option value="email">{{ __("Email") }}</option>
				</select>
			</div>

			<div class="form-group mb-3">
				<label class="form-label">{{ __("Message Template") }} <span class="text-danger">*</span></label>
				<CodeControl
					v-model="notificationTemplate"
					:language="'jinja'"
					:placeholder="__('Enter notification message template')"
					:rows="4"
				/>
				<small class="text-muted">
					{{ __("Jinja template for message. Use {0}, {1}, etc.", [doubleLeft + " doc.name " + doubleRight, doubleLeft + " vars.result " + doubleRight]) }}
				</small>
			</div>

			<div class="form-group mb-3" v-if="notificationType === 'email'">
				<label class="form-label">{{ __("Recipients") }}</label>
				<DataControl
					v-model="recipients"
					:placeholder="__('Comma-separated emails or Jinja template')"
				/>
			</div>

			<div class="template-helpers">
				<span class="helper-label">{{ __("Quick Insert:") }}</span>
				<button 
					class="btn btn-xs btn-outline-secondary" 
					@click="insertTemplate('{{ doc.name }}')"
				>doc.name</button>
				<button 
					class="btn btn-xs btn-outline-secondary" 
					@click="insertTemplate('{{ doc.owner }}')"
				>owner</button>
				<button 
					class="btn btn-xs btn-outline-secondary" 
					@click="insertTemplate('{{ frappe.session.user }}')"
				>user</button>
			</div>

			<div class="preview-section mt-3" v-if="notificationTemplate">
				<label class="form-label">{{ __("Preview") }}</label>
				<div class="notify-preview" :class="'type-' + notificationType">
					<i :class="previewIcon"></i>
					<span>{{ previewText }}</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	node: Object,
});

// Define variables to avoid parsing issues with {{ }}
const doubleLeft = String.fromCharCode(123, 123); // {{
const doubleRight = String.fromCharCode(125, 125); // }}

const notificationType = computed({
	get: () => props.node?.data?.notification_type || "toast",
	set: (val) => {
		if (props.node?.data) {
			props.node.data.notification_type = val;
		}
	},
});

const notificationTemplate = computed({
	get: () => props.node?.data?.notification_template || "",
	set: (val) => {
		if (props.node?.data) {
			props.node.data.notification_template = val;
		}
	},
});

const recipients = computed({
	get: () => props.node?.data?.recipients || "",
	set: (val) => {
		if (props.node?.data) {
			props.node.data.recipients = val;
		}
	},
});

const previewIcon = computed(() => {
	const icons = {
		toast: "fa fa-check-circle",
		alert: "fa fa-info-circle",
		realtime: "fa fa-bell",
		email: "fa fa-envelope",
	};
	return icons[notificationType.value] || "fa fa-bell";
});

const previewText = computed(() => {
	return notificationTemplate.value?.replace(/\{\{[^}]+\}\}/g, '[...]') || '';
});

function insertTemplate(text) {
	notificationTemplate.value = (notificationTemplate.value || "") + text;
}

function validate() {
	const errors = [];
	if (!notificationTemplate.value) {
		errors.push(__("Notification Message Template is required"));
	}
	if (notificationType.value === "email" && !recipients.value) {
		errors.push(__("Recipients are required for email notifications"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.notify-config {
	padding: 16px;
}

.config-section h5 {
	margin-bottom: 16px;
	font-weight: 600;
	color: var(--heading-color);
}

.form-label {
	font-weight: 500;
	margin-bottom: 6px;
	display: block;
}

.template-helpers {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}

.helper-label {
	font-size: 12px;
	color: var(--text-muted);
}

.btn-xs {
	font-size: 11px;
	padding: 2px 8px;
}

.notify-preview {
	border-radius: 6px;
	padding: 12px;
	display: flex;
	align-items: flex-start;
	gap: 10px;
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
</style>
