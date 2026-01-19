<template>
	<div class="condition-config">
		<ConditionStep :node="node" ref="stepRef" />
	</div>
</template>

<script setup>
import { ref } from "vue";
import ConditionStep from "./ConditionStep.vue";

const props = defineProps({
	node: Object,
});

const stepRef = ref(null);

function validate() {
	if (stepRef.value && typeof stepRef.value.validate === "function") {
		return stepRef.value.validate();
	}
	return { valid: true };
}

defineExpose({
	validate
});
</script>
