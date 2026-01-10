<script setup>
import { Handle, Position } from "@vue-flow/core";
import { computed } from "vue";

const props = defineProps(["data", "label"]);

const displayLabel = computed(() => {
	if (props.data?.document_type && props.data?.trigger_event) {
		return `${props.data.document_type} / ${props.data.trigger_event}`;
	}
	return props.label || __("Start");
});
</script>

<template>
	<div class="start-node-d">
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
</style>
