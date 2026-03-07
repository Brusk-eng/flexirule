<script setup>
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../store";

const props = defineProps(["data", "label", "id", "selected"]);
const store = useStore();

const isEffectiveDisabled = computed(() => {
	return store.effectiveDisabledIds?.has(props.id);
});

const testResult = computed(() => {
	const path = store.test_execution_path || [];
	return path.find((entry) => entry.action_id === props.id);
});

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}

function openConfig() {
	store.selected_id = props.id;
	store.show_config_modal = true;
	store.config_modal_mode = "setup";
}
</script>

<template>
	<div
		class="condition-node-card"
		:class="{
			selected: selected,
			disabled: isEffectiveDisabled,
			'test-executed': !!testResult,
			'outcome-true': testResult && testResult.result === true,
			'outcome-false': testResult && testResult.result === false,
		}"
	>
		<!-- Execution Badge -->
		<div v-if="testResult" class="execution-badge" :title="__('Visit Order')">
			{{ store.test_execution_path.indexOf(testResult) + 1 }}
		</div>
		<!-- Input Handle -->
		<Handle type="target" :position="Position.Left" class="handle-target" />

		<!-- Card Body -->
		<div class="node-header">
			<i class="fa fa-question-circle"></i>
			<span class="type-text">{{ __("CONDITION") }}</span>
			<button class="action-btn" @click.stop="openConfig" :title="__('Configure')">
				<i class="fa fa-pencil"></i>
			</button>
			<button class="action-btn delete" @click.stop="deleteNode" v-if="selected">
				<i class="fa fa-trash"></i>
			</button>
		</div>

		<div class="node-body" @dblclick.stop="openConfig">
			<div class="condition-text">{{ label }}</div>
		</div>

		<!-- True Output (Top) -->
		<div class="out-port out-true">
			<span class="port-label">{{ __("YES") }}</span>
			<Handle
				type="source"
				:position="Position.Top"
				id="true"
				class="handle-out handle-true"
			/>
		</div>

		<!-- False Output (Bottom) -->
		<div class="out-port out-false">
			<span class="port-label">{{ __("NO") }}</span>
			<Handle
				type="source"
				:position="Position.Bottom"
				id="false"
				class="handle-out handle-false"
			/>
		</div>
	</div>
</template>

<style scoped>
.condition-node-card {
	width: 160px;
	background: #fff;
	border: 1px solid #ffd8a8; /* Light Orange */
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	border-top: 4px solid #fd7e14; /* Orange 700 */
	transition: all 0.2s ease;
}

.condition-node-card:hover {
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
	border-color: #fd7e14;
}

.condition-node-card.selected {
	box-shadow: 0 0 0 2px #fd7e14;
	border-color: #fd7e14;
}

.condition-node-card.test-executed {
	box-shadow: 0 0 0 3px #198754;
	border-color: #198754;
}

.condition-node-card.outcome-true {
	background-color: #f6ffed;
}

.condition-node-card.outcome-false {
	background-color: #fff1f0;
}

.execution-badge {
	position: absolute;
	top: -8px;
	left: -8px;
	background: #198754;
	color: #fff;
	width: 20px;
	height: 20px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
	font-weight: 700;
	z-index: 10;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* Header */
.node-header {
	display: flex;
	align-items: center;
	padding: 6px 10px;
	border-bottom: 1px solid #fff4e6;
	gap: 6px;
}

.node-header i {
	color: #fd7e14;
	font-size: 12px;
}

.type-text {
	font-size: 9px;
	font-weight: 800;
	color: #6c757d;
	letter-spacing: 0.5px;
	flex: 1;
}

.action-btn {
	background: none;
	border: none;
	padding: 0 2px;
	cursor: pointer;
	color: #adb5bd;
	font-size: 10px;
}

.action-btn:hover {
	color: #dc3545;
}

/* Body */
.node-body {
	padding: 10px;
	text-align: center;
	min-height: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.condition-text {
	font-size: 12px;
	font-weight: 600;
	color: #1a1a1a;
	line-height: 1.2;
}

/* Ports/Handles */
.handle-target {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid #fd7e14 !important;
}

.out-port {
	position: absolute;
	left: 50%;
	transform: translateX(-50%);
	display: flex;
	flex-direction: column;
	align-items: center;
	z-index: 5;
}

.out-true {
	top: -20px;
}
.out-false {
	bottom: -20px;
}

.port-label {
	font-size: 8px;
	font-weight: 800;
}

.out-true .port-label {
	color: #198754;
}
.out-false .port-label {
	color: #dc3545;
}

.handle-out {
	position: relative !important;
	transform: none !important;
	top: auto !important;
	width: 10px !important;
	height: 10px !important;
	background: #fff !important;
	border-width: 2px !important;
	border-style: solid !important;
}

.handle-true {
	border-color: #198754 !important;
}
.handle-false {
	border-color: #dc3545 !important;
}

/* Fixed port label alignment */
.out-true .port-label {
	top: -12px;
}

.out-false .port-label {
	bottom: -12px;
}
</style>
