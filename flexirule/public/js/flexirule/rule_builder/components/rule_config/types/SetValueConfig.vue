<template>
	<div class="set-value-config">
		<div class="config-section">
			<h5>{{ __("Set Value Configuration") }}</h5>
			
			<div class="form-group mb-3">
				<label class="form-label">{{ __("Target Field") }} <span class="text-danger">*</span></label>
				<FieldPickerControl
					v-model="targetField"
					:doctype="documentType"
					:placeholder="__('Select field to set')"
				/>
				<small class="text-muted">{{ __("The document field that will be updated") }}</small>
			</div>

			<div class="form-group mb-3">
				<label class="form-label">{{ __("Value Template") }} <span class="text-danger">*</span></label>
				<CodeControl
					v-model="valueTemplate"
					:language="'jinja'"
					:placeholder="__('Enter Jinja template for value')"
					:rows="4"
				/>
				<small class="text-muted">
					{{ __("Jinja template. Use {0}, {1}, etc.", [doubleLeft + " doc.fieldname " + doubleRight, doubleLeft + " vars.variable " + doubleRight]) }}
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
					@click="insertTemplate('{{ frappe.utils.now() }}')"
				>now()</button>
				<button 
					class="btn btn-xs btn-outline-secondary" 
					@click="insertTemplate('{{ frappe.session.user }}')"
				>user</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useStore } from "../../../store";

const props = defineProps({
	node: Object,
});

const store = useStore();

// Define variables to avoid parsing issues with {{ }}
const doubleLeft = String.fromCharCode(123, 123); // {{
const doubleRight = String.fromCharCode(125, 125); // }}

const documentType = computed(() => store.rule_doc?.document_type);

const targetField = computed({
	get: () => props.node?.data?.target_field || "",
	set: (val) => {
		if (props.node?.data) {
			props.node.data.target_field = val;
		}
	},
});

const valueTemplate = computed({
	get: () => props.node?.data?.value_template || "",
	set: (val) => {
		if (props.node?.data) {
			props.node.data.value_template = val;
		}
	},
});

function insertTemplate(text) {
	valueTemplate.value = (valueTemplate.value || "") + text;
}

function validate() {
	const errors = [];
	if (!targetField.value) {
		errors.push(__("Target Field is required"));
	}
	if (!valueTemplate.value) {
		errors.push(__("Value Template is required"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.set-value-config {
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
	margin-top: 12px;
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
</style>
