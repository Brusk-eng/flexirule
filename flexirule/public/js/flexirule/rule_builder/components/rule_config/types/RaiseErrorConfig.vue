<template>
	<div class="raise-error-config">
		<div class="config-section">
			<h5>{{ __("Raise Error Configuration") }}</h5>
			
			<div class="terminal-warning mb-3">
				<i class="fa fa-exclamation-triangle"></i>
				{{ __("This action will stop rule execution and throw an error.") }}
			</div>

			<div class="form-group mb-3">
				<label class="form-label">{{ __("Error Message Template") }} <span class="text-danger">*</span></label>
				<CodeControl
					v-model="errorTemplate"
					:language="'jinja'"
					:placeholder="__('Enter error message template')"
					:rows="4"
				/>
				<small class="text-muted">
					{{ __("Jinja template for error message. Use {0}, {1}, etc.", [doubleLeft + " doc.name " + doubleRight, doubleLeft + " vars.result " + doubleRight]) }}
				</small>
			</div>

			<div class="template-helpers">
				<span class="helper-label">{{ __("Quick Insert:") }}</span>
				<button 
					class="btn btn-xs btn-outline-secondary" 
					@click="insertTemplate('{{ doc.name }}')"
				>doc.name</button>
				<button 
					class="btn btn-xs btn-outline-secondary" 
					@click="insertTemplate('{{ doc.doctype }}')"
				>doctype</button>
			</div>

			<div class="preview-section mt-3" v-if="errorTemplate">
				<label class="form-label">{{ __("Preview") }}</label>
				<div class="error-preview">
					<i class="fa fa-times-circle"></i>
					<span>{{ previewText }}</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import CodeControl from "../../../controls/CodeControl.vue";

const props = defineProps({
	node: Object,
});

// Define variables to avoid parsing issues with {{ }}
const doubleLeft = String.fromCharCode(123, 123); // {{
const doubleRight = String.fromCharCode(125, 125); // }}

const errorTemplate = computed({
	get: () => props.node?.data?.error_template || "",
	set: (val) => {
		if (props.node?.data) {
			props.node.data.error_template = val;
		}
	},
});

const previewText = computed(() => {
	// Simple preview - just show template with placeholders
	return errorTemplate.value?.replace(/\{\{[^}]+\}\}/g, '[...]') || '';
});

function insertTemplate(text) {
	errorTemplate.value = (errorTemplate.value || "") + text;
}

function validate() {
	const errors = [];
	if (!errorTemplate.value) {
		errors.push(__("Error Message Template is required"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.raise-error-config {
	padding: 16px;
}

.config-section h5 {
	margin-bottom: 16px;
	font-weight: 600;
	color: var(--heading-color);
}

.terminal-warning {
	background: #fef2f2;
	border: 1px solid #fecaca;
	border-radius: 6px;
	padding: 12px;
	color: #dc2626;
	display: flex;
	align-items: center;
	gap: 10px;
}

.terminal-warning i {
	font-size: 16px;
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

.error-preview {
	background: #fef2f2;
	border: 1px solid #fecaca;
	border-radius: 6px;
	padding: 12px;
	color: #b91c1c;
	display: flex;
	align-items: flex-start;
	gap: 10px;
}

.error-preview i {
	color: #dc2626;
	margin-top: 2px;
}
</style>
