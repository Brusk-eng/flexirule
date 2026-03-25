<script setup>
import WaitNodeConfig from "../../node_configs/WaitNodeConfig.vue";

const props = defineProps({
	node: Object,
});

const emit = defineEmits(["update:field"]);

function updateJsonConfig(key, val) {
	// This component handles the 'config' field specifically
	const config = flexirule.utils.safe_json_parse(props.node?.data?.config, {});
	config[key] = val;
	emit("update:field", "config", JSON.stringify(config));
}
</script>

<template>
	<div class="wait-config">
		<WaitNodeConfig :nodeData="node.data" @update-field="updateJsonConfig" />
	</div>
</template>
