<template>
	<div class="schema-renderer">
		<div v-for="field in visibleFields" :key="field.fieldname" class="schema-field-wrapper">
			<!-- Section Break -->
			<div v-if="field.fieldtype === 'Section Break'" class="section-break">
				<h5 v-if="field.label">{{ field.label }}</h5>
				<hr />
			</div>

			<!-- Column Break (Simplified) -->
			<div v-else-if="field.fieldtype === 'Column Break'" class="column-break"></div>

			<!-- Use ControlFactory for standard fields -->
			<div v-else class="form-group" :class="{ 'has-error': fieldState(field).reqd && !getValue(field) }">
				<ControlFactory 
					:df="getNormalizedDf(field)"
					:modelValue="getValue(field)"
					:doc="engine._get_context(row).doc"
					:engine="engine"
					@update:modelValue="updateValue(field, $event)"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import ControlFactory from "../../controls/ControlFactory.vue";

const props = defineProps({
	fields: { type: Array, default: () => [] },
	engine: { type: Object, required: true },
	readOnly: { type: Boolean, default: false },
	row: { type: Object, default: null } // If rendering for a child table row
});

const visibleFields = computed(() => {
	return props.fields.filter(f => !fieldState(f).hidden);
});

function fieldState(field) {
	const contextId = props.row ? props.row.name : "root";
	const state = props.engine.dependency_states[contextId]?.[field.fieldname] || {
		reqd: field.reqd,
		read_only: field.read_only,
		hidden: field.hidden,
		options: field.options
	};

	if (props.readOnly) {
		state.read_only = true;
	}
	return state;
}

function getNormalizedDf(field) {
	const state = fieldState(field);
	return {
		...field,
		reqd: state.reqd,
		read_only: state.read_only,
		hidden: state.hidden,
		options: state.options || field.options
	};
}

function getValue(field) {
	const target = props.row || props.engine.config;
	return target[field.fieldname];
}

function updateValue(field, value) {
	props.engine.handleFieldChange(field.fieldname, value, props.row);
}
</script>

<style scoped>
.schema-renderer {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.section-break {
	margin-top: 24px;
	margin-bottom: 8px;
}

.section-break h5 {
	margin: 0 0 8px 0;
	font-size: 14px;
	font-weight: 700;
	color: var(--text-color);
}

.has-error :deep(.form-control) {
	border-color: var(--red-500, #ef4444);
}
</style>
