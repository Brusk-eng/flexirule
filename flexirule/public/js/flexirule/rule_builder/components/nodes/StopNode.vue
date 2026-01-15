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
	<div class="stop-node-card" :class="{ selected: selected, disabled: isEffectiveDisabled }">
		<Handle type="target" :position="Position.Left" class="handle-target" />

		<div class="node-content">
			<div class="icon-section">
				<i class="fa fa-stop-circle"></i>
			</div>
			<div class="text-section">
				<div class="type-label">{{ __("TERMINAL") }}</div>
				<div class="main-label">STOP</div>
			</div>
			<button class="action-btn delete" @click.stop="deleteNode" v-if="selected">
				<i class="fa fa-trash"></i>
			</button>
		</div>
	</div>
</template>

<style scoped>
.stop-node-card {
	min-width: 140px;
	background: #dc3545; /* Professional Red */
	color: white;
	border-radius: 8px;
	padding: 8px 12px;
	position: relative;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	transition: all 0.2s ease;
	border: 1px solid rgba(255, 255, 255, 0.1);
}

.stop-node-card:hover {
	transform: translateY(-1px);
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.15);
	background: #c82333;
}

.stop-node-card.selected {
	box-shadow: 0 0 0 2px #fff, 0 0 0 4px #dc3545;
}

.node-content {
	display: flex;
	align-items: center;
	gap: 12px;
}

.icon-section {
	width: 28px;
	height: 28px;
	background: rgba(255, 255, 255, 0.2);
	border-radius: 6px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 16px;
}

.text-section {
	flex: 1;
	display: flex;
	flex-direction: column;
}

.type-label {
	font-size: 8px;
	font-weight: 800;
	opacity: 0.8;
	letter-spacing: 0.5px;
}

.main-label {
	font-size: 13px;
	font-weight: 700;
}

.action-btn {
	background: none;
	border: none;
	color: rgba(255, 255, 255, 0.6);
	cursor: pointer;
	padding: 4px;
	font-size: 12px;
}

.action-btn:hover {
	color: white;
}

.handle-target {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid #dc3545 !important;
	left: -5px !important;
}
</style>
