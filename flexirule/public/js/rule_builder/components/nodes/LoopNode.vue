<script setup>
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../store";

const props = defineProps(["data", "label", "id"]);
const store = useStore();

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}
</script>

<template>
	<div
		class="loop-node-container"
		:class="{ 'effectively-disabled': data.is_effectively_disabled }"
	>
		<Handle type="target" :position="Position.Left" class="handle-target" />

		<div class="pill-body">
			<div class="inset-stripe"></div>
			<div class="content">
				<i class="fa fa-refresh"></i>
				<div class="text-group">
					<span class="node-title">{{ data.action_label || label }}</span>
					<span class="node-type">ITERATE</span>
				</div>
			</div>
		</div>

		<button class="delete-btn" @click.stop="deleteNode">×</button>

		<Handle type="source" :position="Position.Right" id="default" class="handle-do" />
		<span class="handle-label label-do">DO</span>

		<Handle type="source" :position="Position.Bottom" id="false" class="handle-done" />
		<span class="handle-label label-done">DONE</span>
	</div>
</template>

<style scoped>
.loop-node-container {
	position: relative;
	padding: 5px;
}

.pill-body {
	background: #fff;
	border: 2px solid var(--yellow-400);
	border-radius: 50px; /* Pill */
	padding: 10px 20px;
	min-width: 150px;
	box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
	display: flex;
	align-items: center;
	position: relative;
	background: var(--yellow-50);
}

.inset-stripe {
	position: absolute;
	left: 10px;
	right: 10px;
	top: 6px;
	height: 2px;
	background: var(--yellow-200);
	border-radius: 1px;
}

.content {
	display: flex;
	align-items: center;
	gap: 12px;
}

.content i {
	font-size: 18px;
	color: var(--yellow-600);
}

.text-group {
	display: flex;
	flex-direction: column;
}
.node-title {
	font-weight: 700;
	font-size: 13px;
	color: var(--text-color);
}
.node-type {
	font-size: 8px;
	font-weight: 900;
	color: var(--yellow-700);
	opacity: 0.7;
	letter-spacing: 1px;
}

.delete-btn {
	position: absolute;
	top: 0;
	right: 0;
	width: 22px;
	height: 22px;
	border-radius: 50%;
	background: var(--danger);
	color: white;
	border: 2px solid white;
	cursor: pointer;
	display: none;
	align-items: center;
	justify-content: center;
	z-index: 5;
}
.loop-node-container:hover .delete-btn {
	display: flex;
}

.handle-target {
	background: var(--gray-400) !important;
	border: 2px solid white;
}
.handle-do {
	background: var(--yellow-500) !important;
	border: 2px solid white;
	width: 12px !important;
	height: 12px !important;
}
.handle-done {
	background: var(--gray-400) !important;
	border: 2px solid white;
	width: 12px !important;
	height: 12px !important;
}

.handle-label {
	position: absolute;
	font-size: 9px;
	font-weight: 900;
	color: var(--text-muted);
	pointer-events: none;
}
.label-do {
	right: -25px;
	top: 38%;
	color: var(--yellow-600);
}
.label-done {
	bottom: -20px;
	left: 50%;
	transform: translateX(-50%);
}
</style>
