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
	min-width: 180px;
}

.node-body {
	background: #157347; /* Professional Green */
	color: white;
	display: flex;
	align-items: center;
	padding: 10px 20px 10px 12px;
	border-radius: 4px 50px 50px 4px; /* Reflected D-Shape */
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
	transition: all 0.2s ease;
	border: 1px solid rgba(255, 255, 255, 0.1);
}

.node-body:hover {
	transform: translateY(-1px);
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
	background: #198754;
}

.icon-section {
	width: 32px;
	height: 32px;
	background: rgba(255, 255, 255, 0.15);
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 12px;
	margin-right: 12px;
	flex-shrink: 0;
}

.info-section {
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.type-label {
	font-size: 9px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	opacity: 0.8;
	margin-bottom: 2px;
}

.main-label {
	font-size: 13px;
	font-weight: 600;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.handle-source {
	background: white !important;
	border: 3px solid #157347 !important;
	width: 14px !important;
	height: 14px !important;
	right: -7px !important;
}

.start-node-d.test-executed .node-body {
	box-shadow: 0 0 0 3px #198754;
	background: #198754;
}

.execution-badge {
	position: absolute;
	top: -8px;
	left: -8px;
	background: #fff;
	color: #198754;
	width: 20px;
	height: 20px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
	font-weight: 700;
	z-index: 10;
	box-shadow: 0 2px 4px rgba(0,0,0,0.2);
	border: 2px solid #198754;
}
</style>
