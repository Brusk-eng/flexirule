<template>
	<div class="configuration-panel">
		<div v-if="node" class="panel-content">
			<component
				:is="configComponent"
				v-if="configComponent"
				ref="configRef"
				:node="node"
				:readOnly="readOnly"
			/>
			<div v-else class="empty-config p-5 text-center">
				<i class="fa fa-sliders fa-3x text-muted mb-3"></i>
				<p class="text-muted">
					{{
						__("No configuration UI available for this node type ({0})").replace(
							"{0}",
							node.type
						)
					}}
				</p>
			</div>
		</div>
		<div v-else class="panel-content empty-state p-5 text-center">
			<p class="text-muted">{{ __("Select a node to configure") }}</p>
		</div>
	</div>
</template>

<script setup>
import ProcessConfig from "./types/ProcessConfig.vue";
import ConditionConfig from "./types/ConditionConfig.vue";
import LoopConfig from "./types/LoopConfig.vue";
import SwitchConfig from "./types/SwitchConfig.vue";
import SubRuleConfig from "./types/SubRuleConfig.vue";
import WaitConfig from "./types/WaitConfig.vue";
import SetValueConfig from "./types/SetValueConfig.vue";
import RaiseErrorConfig from "./types/RaiseErrorConfig.vue";
import NotifyConfig from "./types/NotifyConfig.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const configComponents = {
	process: ProcessConfig,
	condition: ConditionConfig,
	loop: LoopConfig,
	switch: SwitchConfig,
	"sub-rule": SubRuleConfig,
	wait: WaitConfig,
	"set value": SetValueConfig,
	"raise error": RaiseErrorConfig,
	notify: NotifyConfig,
};

const configComponent = computed(() => {
	const type = props.node?.type?.toLowerCase();
	return configComponents[type] || null;
});

const configRef = ref(null);

async function validate() {
	if (configRef.value && typeof configRef.value.validate === "function") {
		return await configRef.value.validate();
	}
	return { valid: true };
}

defineExpose({
	validate,
});
</script>

<style scoped>
.configuration-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
}

.panel-content {
	flex: 1;
	overflow-y: auto;
	padding: 24px;
}

.empty-config {
	height: 200px;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
}
</style>
