<template>
	<div class="wait-node-config">
		<div class="form-group">
			<label>{{ __("Duration (Seconds)") }}</label>
			<input
				type="number"
				class="form-control"
				:value="getJsonConfig('duration')"
				@input="$emit('update-json-config', 'duration', parseFloat($event.target.value))"
			/>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	nodeData: Object,
});

defineEmits(["update-json-config"]);

function getJsonConfig(key, defaultVal = "") {
	// Support both new 'config' and legacy 'method_config'
	const configStr = props.nodeData?.config || props.nodeData?.method_config;
	if (!configStr) return defaultVal;
	try {
		const config = JSON.parse(configStr);
		return config[key] !== undefined ? config[key] : defaultVal;
	} catch (e) {
		return defaultVal;
	}
}
</script>
