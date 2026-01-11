<script setup>
import { ref, computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../store";

const props = defineProps(["data", "label", "id", "selected"]);
const store = useStore();

const showConfig = ref(false);

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
	return { color: "#0d6efd", icon: "fa-cog", typeLabel: __("PROCESS") };
});

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}

function toggleConfig() {
	showConfig.value = !showConfig.value;
}
</script>

<template>
	<div
		class="process-node-card"
		:class="{ selected: selected, disabled: isEffectiveDisabled }"
		:style="{ '--accent-color': nodeMeta.color }"
	>
		<Handle type="target" :position="Position.Left" class="handle-target" />

		<!-- Header with Type and Icon -->
		<div class="node-header">
			<i class="fa" :class="nodeMeta.icon"></i>
			<span class="type-text">{{ nodeMeta.typeLabel }}</span>
			
			<div class="header-actions">
				<button class="action-btn delete" @click.stop="deleteNode" v-if="selected">
					<i class="fa fa-trash"></i>
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="node-body">
			<div class="node-title">{{ data.action_label || label }}</div>
			<div class="node-subtitle" v-if="data.operation || data.process_method">
				{{ data.operation || data.process_method }}
			</div>
		</div>

		<!-- Footer/Status -->
		<div class="node-footer">
			<div 
				class="config-status" 
				:class="{ configured: data.config }"
				@click.stop="toggleConfig"
			>
				<i class="fa" :class="data.config ? 'fa-check-circle' : 'fa-circle-o'"></i>
				<span>{{ data.config ? __("Configured") : __("Not Configured") }}</span>
			</div>
		</div>

		<!-- Config Popover (Simplified) -->
		<div v-if="showConfig" class="popover-card config-popover">
			<div class="popover-header">
				<span>{{ __("JSON Preview") }}</span>
				<button class="close-btn" @click.stop="showConfig = false">×</button>
			</div>
			<div class="popover-body">
				<pre>{{ data.config || data.method_config || __("No config data") }}</pre>
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

/* Popover */
.popover-card {
	position: absolute;
	top: 100%;
	left: 0;
	width: 260px;
	background: #fff;
	border: 1px solid #d1d8dd;
	border-radius: 8px;
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
	z-index: 1000;
	margin-top: 10px;
}

.popover-header {
	padding: 8px 12px;
	background: #f8f9fa;
	border-bottom: 1px solid #eee;
	display: flex;
	justify-content: space-between;
	align-items: center;
	font-weight: 600;
	font-size: 11px;
}

.close-btn {
	background: none;
	border: none;
	font-size: 16px;
	cursor: pointer;
	line-height: 1;
}

.popover-body {
	padding: 10px;
	max-height: 200px;
	overflow-y: auto;
}

.popover-body pre {
	margin: 0;
	font-size: 10px;
	background: #f8f9fa;
	padding: 8px;
	border-radius: 4px;
}
</style>
