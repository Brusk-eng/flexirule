<script setup>
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../store";

const props = defineProps(["data", "label", "id", "selected"]);
const store = useStore();

const selectedType = ref("Process");
const customLabel = ref("");

const actionTypes = computed(() => {
	const meta = frappe.get_meta("Rule Action");
	if (!meta || !meta.fields) return [];

	const typeField = meta.fields.find((f) => f.fieldname === "action_type");
	if (!typeField || !typeField.options) return [];

	// Map of action types to icons
	const iconMap = {
		Process: "fa-cog",
		Condition: "fa-code-fork",
		Loop: "fa-refresh",
		Switch: "fa-code-fork",
		Wait: "fa-clock-o",
		"Sub-Rule": "fa-cube",
		Stop: "fa-stop-circle",
		"Set Value": "fa-edit",
		"Raise Error": "fa-exclamation-triangle",
		Notify: "fa-bell",
	};

	return typeField.options
		.split("\n")
		.filter((t) => t && t !== "Entry Action" && t !== "Start")
		.map((t) => ({
			label: __(t),
			value: t, // Keep exact value for action_type
			actionType: t,
			icon: iconMap[t] || "fa-cog",
		}));
});

function onCreate() {
	const typeConfig = actionTypes.value.find((t) => t.value === selectedType.value);
	const nodeIndex = store.nodes.findIndex((n) => n.id === props.id);

	if (nodeIndex === -1) return;

	const label = customLabel.value.trim() || typeConfig.label;

	// Upgrade the node
	store.nodes[nodeIndex].type = typeConfig.actionType.toLowerCase();
	store.nodes[nodeIndex].label = label;
	store.nodes[nodeIndex].data = {
		...store.nodes[nodeIndex].data,
		action_type: typeConfig.actionType,
		action_label: label,
	};

	store.mark_dirty();
}

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}
</script>

<template>
	<div class="action-selector-card" :class="{ selected: selected }">
		<Handle type="target" :position="Position.Left" class="handle-target" />

		<div class="node-header">
			<i class="fa fa-plus-circle"></i>
			<span class="header-text">{{ __("New Action") }}</span>
			<button class="delete-btn" @click.stop="deleteNode" v-if="selected">
				<i class="fa fa-trash"></i>
			</button>
		</div>

		<div class="node-body" @dblclick.stop="store.selected_id = props.id">
			<div class="form-group">
				<label class="small text-muted">{{ __("Action Type") }}</label>
				<select v-model="selectedType" class="form-control input-xs">
					<option v-for="type in actionTypes" :key="type.value" :value="type.value">
						{{ type.label }}
					</option>
				</select>
			</div>
			<div class="form-group">
				<label class="small text-muted">{{ __("Label") }}</label>
				<input
					type="text"
					v-model="customLabel"
					class="form-control input-xs"
					:placeholder="__('Enter label...')"
					@keyup.enter="onCreate"
				/>
			</div>
			<button class="btn btn-primary btn-xs btn-block mt-2" @click="onCreate">
				{{ __("Create") }}
			</button>
		</div>

		<div class="node-footer">
			<span class="text-muted small">{{ __("Configure to proceed") }}</span>
		</div>

		<Handle type="source" :position="Position.Right" id="default" class="handle-source" />
	</div>
</template>

<style scoped>
.action-selector-card {
	width: 200px;
	background: #fff;
	border: 2px dashed #d1d8dd;
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	transition: all 0.2s ease;
}

.action-selector-card.selected {
	border-color: var(--primary);
	border-style: solid;
	box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2);
}

.node-header {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid #f0f4f7;
	gap: 8px;
	background: #f8f9fa;
	border-radius: 8px 8px 0 0;
}

.node-header i {
	color: var(--primary);
	font-size: 14px;
}

.header-text {
	font-size: 11px;
	font-weight: 700;
	color: #6c757d;
	flex: 1;
}

.delete-btn {
	background: none;
	border: none;
	padding: 2px;
	cursor: pointer;
	color: #adb5bd;
}

.delete-btn:hover {
	color: #dc3545;
}

.node-body {
	padding: 12px;
}

.form-group {
	margin-bottom: 8px;
}

.form-group label {
	display: block;
	margin-bottom: 2px;
}

.node-footer {
	padding: 6px 12px;
	background-color: #f8fcfd;
	border-bottom-left-radius: 8px;
	border-bottom-right-radius: 8px;
	border-top: 1px solid #f0f4f7;
	text-align: center;
}

.handle-target,
.handle-source {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid #d1d8dd !important;
}

.action-selector-card.selected .handle-target,
.action-selector-card.selected .handle-source {
	border-color: var(--primary) !important;
}
</style>
