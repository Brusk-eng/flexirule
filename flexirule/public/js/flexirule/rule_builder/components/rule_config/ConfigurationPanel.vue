<template>
	<div class="configuration-panel">
		<div v-if="node" class="panel-content">
			<div class="panel-header">
				<div class="header-text">
					<h4>{{ __("Configuration") }}</h4>
					<p class="text-muted small">
						{{ node.data?.action_type || node.type || __("Action") }}
					</p>
				</div>
			</div>
			<div class="panel-sections">
				<!-- Universal Action Settings (except for Start node) -->
				<ActionSettings
					v-if="node.type !== 'start'"
					:node="node"
					:readOnly="readOnly"
					@update:field="on_update_action_field"
				/>

				<component
					:is="configComponent"
					v-if="configComponent"
					ref="configRef"
					:node="node"
					:read_only="readOnly"
				/>
				<div v-else class="empty-config text-center">
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
		</div>
		<div v-else class="panel-content empty-state text-center">
			<p class="text-muted">{{ __("Select a node to configure") }}</p>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useStore } from "../../store";
import ActionSettings from "./ActionSettings.vue";
import ProcessConfig from "./types/ProcessConfig.vue";
import ConditionConfig from "./types/ConditionConfig.vue";
import LoopConfig from "./types/LoopConfig.vue";
import SwitchConfig from "./types/SwitchConfig.vue";
import SubRuleConfig from "./types/SubRuleConfig.vue";
import WaitConfig from "./types/WaitConfig.vue";
import SetValueConfig from "./types/SetValueConfig.vue";
import RaiseErrorConfig from "./types/RaiseErrorConfig.vue";
import NotifyConfig from "./types/NotifyConfig.vue";
import QueryRecordsConfig from "./types/QueryRecordsConfig.vue";
import AggregateRecordsConfig from "./types/AggregateRecordsConfig.vue";
import CreateDocsConfig from "./types/CreateDocsConfig.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();

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
	query: QueryRecordsConfig,
	aggregate: AggregateRecordsConfig,
	createdoc: CreateDocsConfig,
};

const configComponent = computed(() => {
	let type = props.node?.type?.toLowerCase();
	if (type === "query records") type = "query";
	if (type === "aggregate records") type = "aggregate";
	if (type === "create docs") type = "createdoc";
	return configComponents[type] || null;
});

const configRef = ref(null);

function on_update_action_field({ fieldname, value }) {
	if (!props.node?.data) return;
	props.node.data[fieldname] = value;
	store.mark_dirty();
}

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
	display: flex;
	flex-direction: column;
	min-height: 0;
}

.panel-header {
	padding: 20px;
	border-bottom: 1px solid var(--border-color);
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.panel-header h4 {
	margin: 0 0 4px 0;
	font-size: 15px;
	font-weight: 600;
}

.panel-sections {
	flex: 1;
	overflow-y: auto;
	padding: 20px;
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.empty-config {
	height: 200px;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
}

.empty-state {
	display: flex;
	align-items: center;
	justify-content: center;
	flex: 1;
	padding: 20px;
}
</style>
