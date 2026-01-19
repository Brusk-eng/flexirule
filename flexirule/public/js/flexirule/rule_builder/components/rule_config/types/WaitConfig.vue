<template>
	<div class="wait-config">
		<WaitNodeConfig :nodeData="node.data" @update-field="updateField" />
	</div>
</template>

<script setup>
import WaitNodeConfig from "../../node_configs/WaitNodeConfig.vue";

const props = defineProps({
	node: Object,
});

const emit = defineEmits(["update:field"]);

function updateField(key, val) {
	emit("update:field", key, val);
}
</script>
