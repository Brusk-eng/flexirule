<template>
	<div class="configuration-panel">
		<div v-if="node" class="panel-content">
			<component 
				:is="configComponent" 
				v-if="configComponent"
				ref="configRef"
				:node="node"
				:readOnly="readOnly"
				@update:field="updateField"
			/>
			<div v-else class="empty-config p-5 text-center">
				<i class="fa fa-sliders fa-3x text-muted mb-3"></i>
				<p class="text-muted">{{ __("No configuration UI available for this node type ({0})").replace('{0}', node.type) }}</p>
			</div>
		</div>
		<div v-else class="panel-content empty-state p-5 text-center">
			<p class="text-muted">{{ __("Select a node to configure") }}</p>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useStore } from "../../store";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();
const actionLabel = ref(props.node?.data?.action_label || props.node?.label || "");

watch(() => props.node, (newNode) => {
	if (newNode) {
		actionLabel.value = newNode.data?.action_label || newNode.label || "";
	}
}, { immediate: true });

function updateLabel() {
	if (!props.node || props.readOnly) return;
	props.node.data.action_label = actionLabel.value;
	props.node.label = actionLabel.value;
	store.mark_dirty();
}

function updateField(fieldname, value) {
	if (!props.node?.data) return;
	props.node.data[fieldname] = value;
	store.mark_dirty();
}

import ProcessConfig from "./types/ProcessConfig.vue";
import ConditionConfig from "./types/ConditionConfig.vue";
import LoopConfig from "./types/LoopConfig.vue";
import SwitchConfig from "./types/SwitchConfig.vue";
import SubRuleConfig from "./types/SubRuleConfig.vue";
import WaitConfig from "./types/WaitConfig.vue";
import SetValueConfig from "./types/SetValueConfig.vue";
import RaiseErrorConfig from "./types/RaiseErrorConfig.vue";
import NotifyConfig from "./types/NotifyConfig.vue";

const configComponents = {
	'ProcessConfig': ProcessConfig,
	'ConditionConfig': ConditionConfig,
	'LoopConfig': LoopConfig,
	'SwitchConfig': SwitchConfig,
	'SubRuleConfig': SubRuleConfig,
	'WaitConfig': WaitConfig,
	'SetValueConfig': SetValueConfig,
	'RaiseErrorConfig': RaiseErrorConfig,
	'NotifyConfig': NotifyConfig
};

const configComponent = computed(() => {
	const type = props.node?.type;
	if (!type) return null;

	// Map internal types to component names
	const mapping = {
		'process': 'ProcessConfig',
		'condition': 'ConditionConfig',
		'loop': 'LoopConfig',
		'switch': 'SwitchConfig',
		'sub-rule': 'SubRuleConfig',
		'wait': 'WaitConfig',
		'set value': 'SetValueConfig',
		'raise error': 'RaiseErrorConfig',
		'notify': 'NotifyConfig'
	};

	const componentName = mapping[type];
	return configComponents[componentName] || null;
});

const configRef = ref(null);

async function validate() {
	if (configRef.value && typeof configRef.value.validate === "function") {
		return await configRef.value.validate();
	}
	// If no validation method exists (e.g. WaitConfig), assume valid
	return { valid: true };
}

defineExpose({
	validate
});

function getIcon(type) {
	const icons = {
		'process': 'fa fa-cog',
		'condition': 'fa fa-code-fork',
		'loop': 'fa fa-refresh',
		'switch': 'fa fa-code-fork rotate-90',
		'sub-rule': 'fa fa-cube',
		'wait': 'fa fa-clock-o',
		'start': 'fa fa-play',
		'stop': 'fa fa-stop'
	};
	return icons[type] || 'fa fa-circle';
}
</script>

<style scoped>
.configuration-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
}

.panel-header {
	padding: 24px;
	border-bottom: 1px solid var(--border-color);
	display: flex;
	align-items: center;
	gap: 16px;
	background: #fff;
}

.type-indicator {
	width: 48px;
	height: 48px;
	border-radius: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 20px;
	color: #fff;
	box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.type-indicator.process { background: #3b82f6; }
.type-indicator.condition { background: #10b981; }
.type-indicator.loop { background: #8b5cf6; }
.type-indicator.switch { background: #f59e0b; }
.type-indicator.sub-rule { background: #6366f1; }
.type-indicator.wait { background: #6b7280; }

.rotate-90 { transform: rotate(90deg); }

.type-info {
	flex: 1;
}

.node-type-label {
	margin: 0 0 4px 0;
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 1px;
	color: var(--text-muted);
}

.action-label-input {
	border: 1px solid transparent;
	background: transparent;
	font-size: 20px;
	font-weight: 600;
	width: 100%;
	padding: 4px 8px;
	margin-left: -8px;
	border-radius: 4px;
	color: var(--text-color);
}

.action-label-input:focus {
	background: var(--gray-50);
	border-color: var(--border-color);
	outline: none;
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
