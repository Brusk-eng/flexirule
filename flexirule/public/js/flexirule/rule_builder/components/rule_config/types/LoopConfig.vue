<template>
	<div class="loop-config">
		<LoopNodeConfig 
			:nodeData="node.data"
			@update-json-config="updateJsonConfig"
		/>
		<hr />
		<ConditionStep :node="node" />
	</div>
</template>

<script setup>
import { useStore } from "../../../store";
import LoopNodeConfig from "../../node_configs/LoopNodeConfig.vue";
import ConditionStep from "./ConditionStep.vue";

const props = defineProps({
	node: Object,
});

const store = useStore();

function updateJsonConfig(key, val) {
	if (!props.node.data) return;
	
	let config = {};
	try {
		config = JSON.parse(props.node.data.config || "{}");
	} catch (e) {
		config = {};
	}
	
	config[key] = val;
	props.node.data.config = JSON.stringify(config);
	store.mark_dirty();
}
</script>
