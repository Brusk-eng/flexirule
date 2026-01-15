<script setup>
import { computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../store";

const props = defineProps(["data", "label", "id", "selected"]);
const store = useStore();

const isEffectiveDisabled = computed(() => {
	return store.effectiveDisabledIds?.has(props.id);
});

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}
</script>

<template>
	<div 
		class="loop-node-card" 
		:class="{ selected: selected, disabled: isEffectiveDisabled }"
	>
		<Handle type="target" :position="Position.Left" class="handle-target" />

		<div class="node-header">
			<i class="fa fa-refresh"></i>
			<span class="type-text">{{ __("ITERATION") }}</span>
			<button class="action-btn delete" @click.stop="deleteNode" v-if="selected">
				<i class="fa fa-trash"></i>
			</button>
		</div>

		<div class="node-body">
			<div class="loop-title">{{ data.action_label || label }}</div>
		</div>

		<!-- Iteration Handle -->
		<div class="out-port out-do">
			<span class="port-label">{{ __("DO") }}</span>
			<Handle type="source" :position="Position.Right" id="default" class="handle-out handle-do" />
		</div>

		<!-- Done Handle -->
		<div class="out-port out-done">
			<span class="port-label">{{ __("DONE") }}</span>
			<Handle type="source" :position="Position.Bottom" id="false" class="handle-out handle-done" />
		</div>
	</div>
</template>

<style scoped>
.loop-node-card {
	width: 180px;
	background: #fff;
	border: 1px solid #ffe066; /* Light Yellow */
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	border-left: 4px solid #fab005; /* Yellow 7 */
	transition: all 0.2s ease;
}

.loop-node-card:hover {
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
	border-color: #fab005;
}

.loop-node-card.selected {
	box-shadow: 0 0 0 2px #fab005;
	border-color: #fab005;
}

.node-header {
	display: flex;
	align-items: center;
	padding: 6px 10px;
	border-bottom: 1px solid #fff9db;
	gap: 8px;
}

.node-header i {
	color: #fab005;
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
	cursor: pointer;
	color: #adb5bd;
	font-size: 10px;
}

.action-btn:hover {
	color: #dc3545;
}

.node-body {
	padding: 12px;
	min-height: 40px;
}

.loop-title {
	font-size: 13px;
	font-weight: 600;
	color: #1a1a1a;
}

/* Handles */
.handle-target {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid #fab005 !important;
}

.handle-out {
	position: relative !important;
	transform: none !important;
	width: 10px !important;
	height: 10px !important;
	background: #fff !important;
	border-width: 2px !important;
	border-style: solid !important;
}

.handle-do { border-color: #fab005 !important; }
.handle-done { border-color: #adb5bd !important; }

.out-port {
	position: absolute;
	display: flex;
	align-items: center;
	gap: 4px;
}

.out-do {
	right: -24px;
	top: 50%;
	transform: translateY(-50%);
}

.out-done {
	bottom: -22px;
	left: 50%;
	transform: translateX(-50%);
	flex-direction: column;
}

.port-label {
	font-size: 8px;
	font-weight: 800;
	color: #6c757d;
}

.out-do .port-label { color: #fab005; }
</style>
