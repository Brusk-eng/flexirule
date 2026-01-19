<template>
	<div class="sub-rule-config">
		<SubRuleNodeConfig 
			:nodeData="node.data"
			:availableRules="store.available_rules"
			@update-field="updateField"
		/>
	</div>
</template>

<script setup>
import { onMounted } from "vue";
import { useStore } from "../../../store";
import SubRuleNodeConfig from "../../node_configs/SubRuleNodeConfig.vue";

const props = defineProps({
	node: Object,
});

const store = useStore();

const emit = defineEmits(["update:field"]);

function updateField(key, val) {
	emit("update:field", key, val);
}

onMounted(() => {
	if (!store.available_rules.length) {
		store.fetch_available_rules();
	}
});
</script>
