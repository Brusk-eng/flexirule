<template>
	<div class="wait-node-config">
		<div class="form-row">
			<div
				class="form-group col-md-6"
				:class="{ 'has-error': showValidation && getJsonConfig('value', 1) <= 0 }"
				v-fxr-fieldname="'config.value'"
			>
				<label class="small text-muted">{{ __("Delay Value") }}</label>
				<input
					type="number"
					class="form-control"
					:value="getJsonConfig('value', 1)"
					@input="$emit('update-field', 'value', parseFloat($event.target.value))"
				/>
				<div v-if="showValidation && getJsonConfig('value', 1) <= 0" class="fxr-error-msg">
					{{ __("Delay must be greater than 0") }}
				</div>
			</div>
			<div class="form-group col-md-6" v-fxr-fieldname="'config.unit'">
				<label class="small text-muted">{{ __("Unit") }}</label>
				<SelectControl
					:df="{ fieldtype: 'Select', options: ['Seconds', 'Minutes', 'Hours', 'Days'] }"
					:modelValue="getJsonConfig('unit', 'Minutes')"
					:hideLabel="true"
					@update:modelValue="(val) => $emit('update-field', 'unit', val)"
				/>
			</div>
		</div>
		<div class="alert alert-info py-2 px-3 small mt-2">
			<i class="fa fa-info-circle mr-1"></i>
			{{ __("Rule execution will pause for the specified duration.") }}
		</div>
	</div>
</template>

<script setup>
import SelectControl from "../controls/SelectControl.vue";
const props = defineProps({
	nodeData: Object,
	showValidation: { type: Boolean, default: false },
});

defineEmits(["update-field"]);

function getJsonConfig(key, defaultVal = "") {
	const configStr = props.nodeData?.config;
	const config = flexirule.utils.safe_json_parse(configStr, {});

	// Legacy migration: if key is 'value' but only 'duration' exists
	if (key === "value" && config.duration !== undefined && config.value === undefined) {
		return config.duration;
	}

	return config[key] !== undefined ? config[key] : defaultVal;
}

function validate() {
	const value = getJsonConfig("value", 1);
	const errors = [];
	if (value <= 0) {
		errors.push(__("Delay value must be greater than 0"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
