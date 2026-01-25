<script setup>
import { computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../store";

const props = defineProps(["data", "label", "id"]);
const store = useStore();

const displayLabel = computed(() => {
	if (props.data?.document_type && props.data?.trigger_event) {
		return `${props.data.document_type} / ${props.data.trigger_event}`;
	}
	return props.label || __("Start");
});

const testResult = computed(() => {
	const path = store.test_execution_path || [];
	return path.find(entry => entry.action_id === props.id || entry.action_id === 'root' || entry.action_id === 'start');
});
</script>

<template>
	<div class="start-node-d" :class="{ 'test-executed': !!testResult }">
		<!-- Execution Badge -->
		<div v-if="testResult" class="execution-badge" :title="__('Visit Order')">
			{{ store.test_execution_path.indexOf(testResult) + 1 }}
		</div>
		<div class="node-body">
			<div class="icon-section">
				<i class="fa fa-play"></i>
			</div>
			<div class="info-section">
				<div class="type-label">{{ __("TRIGGER") }}</div>
				<div class="main-label">{{ displayLabel }}</div>
			</div>
		</div>
		<Handle type="source" :position="Position.Right" id="default" class="handle-source" />
	</div>
</template>

<style scoped>
.start-node-d {
	position: relative;
	min-width: 140px;
}

.node-body {
	background: #10b981; /* Vibrant Green */
	color: white;
	display: flex;
	align-items: center;
	padding: 8px 16px 8px 10px;
	border-radius: 4px 40px 40px 4px; /* Reflected D-Shape */
	box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.06);
	transition: all 0.2s ease;
	border: 1px solid rgba(255, 255, 255, 0.2);
}

.node-body:hover {
	transform: translateY(-1px);
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	background: #059669; /* Darker Green for hover */
}

.icon-section {
	width: 28px;
	height: 28px;
	background: rgba(255, 255, 255, 0.2);
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
	margin-right: 10px;
	flex-shrink: 0;
}

.info-section {
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.type-label {
	font-size: 8px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	opacity: 0.9;
	margin-bottom: 1px;
}

.main-label {
	font-size: 12px;
	font-weight: 600;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.handle-source {
	background: white !important;
	border: 3px solid #10b981 !important;
	width: 12px !important;
	height: 12px !important;
	right: -6px !important;
}

.start-node-d.test-executed .node-body {
	box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.4);
	background: #10b981;
}

.execution-badge {
	position: absolute;
	top: -6px;
	left: -6px;
	background: #fff;
	color: #10b981;
	width: 18px;
	height: 18px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 9px;
	font-weight: 700;
	z-index: 10;
	box-shadow: 0 2px 4px rgba(0,0,0,0.2);
	border: 2px solid #10b981;
}
</style>
