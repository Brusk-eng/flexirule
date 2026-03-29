<script setup>
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../store";
import { getContract } from "../../../core/contracts";
import { computed } from "vue";

const props = defineProps(["data", "label", "id"]);
const store = useStore();

const displayLabel = computed(() => {
	if (
		props.data?.document_type &&
		props.data?.trigger_type === "DocType Event" &&
		props.data?.trigger_event
	) {
		return `${props.data.document_type} / ${props.data.trigger_event}`;
	}
	if (props.data?.document_type && props.data?.trigger_type) {
		return `${props.data.document_type} / ${props.data.trigger_type}`;
	}
	return props.label || __("Start");
});

const nodeMeta = computed(() => {
	const actionType = props.data?.action_type || "Entry Action";
	const contract = getContract(actionType);
	const css = contract.css || {};

	return {
		color: css.color || "#10b981",
		icon: css.icon || "fa-play",
		typeLabel: __("TRIGGER"),
	};
});

const testResult = computed(() => {
	const path = store.test_execution_path || [];
	return path.find(
		(entry) =>
			entry.action_id === props.id ||
			entry.action_id === "root" ||
			entry.action_id === "start"
	);
});

function openConfig() {
	store.selected_id = props.id || "start"; // Start node might be 'start' or have ID
	store.show_config_modal = true;
	store.config_modal_mode = "setup";
}
</script>

<template>
	<div class="start-node-d" :class="{ 'test-executed': !!testResult }">
		<!-- Execution Badge -->
		<div v-if="testResult" class="execution-badge" :title="__('Visit Order')">
			{{ store.test_execution_path.indexOf(testResult) + 1 }}
		</div>
		<div
			class="node-body"
			@dblclick.stop="openConfig"
			:style="{ '--accent-color': nodeMeta.color }"
		>
			<div class="icon-section">
				<i class="fa" :class="nodeMeta.icon"></i>
			</div>
			<div class="info-section">
				<div class="type-label">{{ nodeMeta.typeLabel }}</div>
				<div class="main-label">{{ displayLabel }}</div>
			</div>

			<button class="action-btn" @click.stop="openConfig" :title="__('Configure')">
				<i class="fa fa-pencil"></i>
			</button>
		</div>
		<Handle
			type="source"
			:position="Position.Right"
			id="default"
			class="handle-source"
			:connectable="true"
			style="
				display: block !important;
				opacity: 1 !important;
				visibility: visible !important;
				right: -8px !important;
				z-index: 9999 !important;
				width: 14px !important;
				height: 14px !important;
				background: #fff !important;
				pointer-events: all !important;
			"
		/>
	</div>
</template>

<style scoped>
.start-node-d {
	position: relative;
	min-width: 140px;
}

.node-body {
	background: var(--accent-color);
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
	filter: brightness(0.9);
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
	border: 3px solid var(--accent-color) !important;
	width: 12px !important;
	height: 12px !important;
	right: -6px !important;
	z-index: 10 !important;
	cursor: crosshair !important;
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
	color: var(--accent-color);
	width: 18px;
	height: 18px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 9px;
	font-weight: 700;
	z-index: 10;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	border: 2px solid var(--accent-color);
}

.action-btn {
	background: none;
	border: none;
	color: rgba(255, 255, 255, 0.6);
	cursor: pointer;
	padding: 4px;
	font-size: 12px;
	margin-left: auto;
}

.action-btn:hover {
	color: white;
}
</style>
