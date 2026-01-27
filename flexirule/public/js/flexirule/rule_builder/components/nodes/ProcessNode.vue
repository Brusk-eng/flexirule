<script setup>
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../store";

const props = defineProps(["data", "label", "id", "selected"]);
const store = useStore();



const isEffectiveDisabled = computed(() => {
	return store.effectiveDisabledIds?.has(props.id);
});

const nodeMeta = computed(() => {
	const type = (props.data.action_type || "").toLowerCase();
	if (type.includes("switch")) {
		return { color: "#6f42c1", icon: "fa-random", typeLabel: __("SWITCH") };
	}
	if (type.includes("wait") || type.includes("delay")) {
		return { color: "#6c757d", icon: "fa-clock-o", typeLabel: __("WAIT") };
	}
	if (type.includes("sub-rule") || type.includes("nested")) {
		return { color: "#0dcaf0", icon: "fa-external-link", typeLabel: __("SUB-RULE") };
	}
	if (type.includes("stop") || type.includes("cancel")) {
		return { color: "#dc3545", icon: "fa-stop-circle", typeLabel: __("STOP") };
	}
	if (type.includes("raise error")) {
		return { color: "#dc3545", icon: "fa-exclamation-triangle", typeLabel: __("RAISE ERROR") };
	}
	if (type.includes("set value")) {
		return { color: "#198754", icon: "fa-edit", typeLabel: __("SET VALUE") };
	}
	if (type.includes("notify")) {
		return { color: "#ffc107", icon: "fa-bell", typeLabel: __("NOTIFY") };
	}
	return { color: "#0d6efd", icon: "fa-cog", typeLabel: __("PROCESS") };
});

const testResult = computed(() => {
	const path = store.test_execution_path || [];
	return path.find(entry => entry.action_id === props.id);
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
		class="process-node-card"
		:class="{ 
			selected: selected, 
			disabled: isEffectiveDisabled,
			'test-executed': !!testResult
		}"
		:style="{ '--accent-color': nodeMeta.color }"
	>
		<!-- Execution Badge -->
		<div v-if="testResult" class="execution-badge" :title="__('Visit Order')">
			{{ store.test_execution_path.indexOf(testResult) + 1 }}
		</div>
		<Handle type="target" :position="Position.Left" class="handle-target" />

		<!-- Header with Type and Icon -->
		<div class="node-header">
			<i class="fa" :class="nodeMeta.icon"></i>
			<span class="type-text">{{ nodeMeta.typeLabel }}</span>
			
			<button class="action-btn" @click.stop="openConfig" :title="__('Configure')">
				<i class="fa fa-pencil"></i>
			</button>
			<button class="action-btn delete" @click.stop="deleteNode" v-if="selected">
				<i class="fa fa-trash"></i>
			</button>
		</div>

		<!-- Main Content -->
		<div class="node-body" @dblclick.stop="openConfig">
			<div class="node-title">{{ data.action_label || label }}</div>
			<div class="node-subtitle" v-if="data.operation">
				{{ data.operation }}
			</div>
		</div>

		<!-- Footer/Status -->
		<div class="node-footer">
			<div 
				class="config-status" 
				:class="{ configured: data.config }"
				@click.stop="openConfig"
			>
				<i class="fa" :class="data.config ? 'fa-check-circle' : 'fa-circle-o'"></i>
				<span>{{ data.config ? __("Configured") : __("Not Configured") }}</span>
			</div>
		</div>

		<Handle type="source" :position="Position.Right" id="default" class="handle-source" />
	</div>
</template>

<style scoped>
.process-node-card {
	width: 220px;
	background: #fff;
	border: 1px solid #d1d8dd;
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	overflow: visible;
	border-left: 4px solid var(--accent-color);
	transition: all 0.2s ease;
}

.process-node-card:hover {
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
	border-color: var(--accent-color);
}

.process-node-card.selected {
	box-shadow: 0 0 0 2px var(--accent-color);
	border-color: var(--accent-color);
}

.process-node-card.test-executed {
	box-shadow: 0 0 0 3px #198754;
	border-color: #198754;
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
	box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

/* Header */
.node-header {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid #f0f4f7;
	gap: 8px;
}

.node-header i {
	color: var(--accent-color);
	font-size: 12px;
}

.type-text {
	font-size: 10px;
	font-weight: 700;
	color: #6c757d;
	letter-spacing: 0.5px;
	flex: 1;
}

.header-actions {
	display: flex;
	gap: 4px;
}

.action-btn {
	background: none;
	border: none;
	padding: 2px 4px;
	cursor: pointer;
	color: #adb5bd;
	font-size: 11px;
}

.action-btn.delete:hover {
	color: #dc3545;
}

/* Body */
.node-body {
	padding: 12px;
	min-height: 50px;
}

.node-title {
	font-size: 13px;
	font-weight: 600;
	color: #1a1a1a;
	margin-bottom: 4px;
	line-height: 1.2;
}

.node-subtitle {
	font-size: 11px;
	color: #6c757d;
	font-style: italic;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

/* Footer */
.node-footer {
	padding: 6px 12px;
	background-color: #f8fcfd;
	border-bottom-left-radius: 8px;
	border-bottom-right-radius: 8px;
	border-top: 1px solid #f0f4f7;
}

.config-status {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 10px;
	cursor: pointer;
	color: #adb5bd;
}

.config-status.configured {
	color: #198754;
}

.config-status:hover {
	opacity: 0.8;
}

/* Handles */
.handle-target, .handle-source {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid var(--accent-color) !important;
}


</style>
