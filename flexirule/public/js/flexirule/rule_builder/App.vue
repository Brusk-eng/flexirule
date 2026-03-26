<template>
	<div class="rule-builder-container">
		<!-- Main Canvas + Sidebar -->
		<div class="builder-main">
			<div class="canvas-container" ref="flowWrapper" @dragover="onDragOver" @drop="onDrop">
				<VueFlow
					:edges-editable="false"
					v-model:nodes="nodes"
					v-model:edges="edges"
					:default-viewport="{ zoom: 1 }"
					:min-zoom="0.2"
					:max-zoom="2"
					:snap-to-grid="true"
					:snap-grid="[15, 15]"
					fit-view-on-init
					@node-click="onNodeClick"
					@node-dblclick="onNodeDblClick"
					@pane-click="onPaneClick"
					@connect="onConnect"
					@nodes-change="onNodesChange"
					@edges-change="onEdgesChange"
					@edge-click="onEdgeClick"
					@pane-ready="onPaneReady"
				>
					<template #node-start="nodeProps">
						<StartNode v-bind="nodeProps" />
					</template>
					<template #node-process="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-condition="nodeProps">
						<ConditionNode v-bind="nodeProps" />
					</template>
					<template #node-loop="nodeProps">
						<LoopNode v-bind="nodeProps" />
					</template>
					<template #node-stop="nodeProps">
						<StopNode v-bind="nodeProps" />
					</template>
					<template #node-selector="nodeProps">
						<ActionSelectorNode v-bind="nodeProps" />
					</template>
					<template #node-raise-error="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-set-value="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-notify="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-wait="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-sub-rule="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-query="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-aggregate="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-documentaction="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>

					<Background :gap="15" />
					<Panel :position="PanelPosition.BottomLeft" class="controls-panel">
						<div class="btn-group">
							<button
								class="btn btn-sm btn-default"
								@click="zoomIn"
								:title="__('Zoom In')"
							>
								+
							</button>
							<button
								class="btn btn-sm btn-default"
								@click="zoomOut"
								:title="__('Zoom Out')"
							>
								-
							</button>
							<button
								class="btn btn-sm btn-default"
								@click="fitView()"
								:title="__('Fit View')"
							>
								{{ __("Fit") }}
							</button>
						</div>

						<div class="divider-vertical"></div>

						<div class="show-disabled-control" :title="__('Show Disabled Nodes')">
							<label class="switch small-switch">
								<input type="checkbox" v-model="showDisabledNodes" />
								<span class="slider round"></span>
							</label>
							<span class="small text-muted">{{ __("Disabled") }}</span>
						</div>

						<div v-if="isReadOnly" class="read-only-badge">
							<i class="fa fa-lock"></i> {{ __("Read Only") }}
						</div>
					</Panel>
				</VueFlow>

				<!-- Floating Draggable Toolbar -->
				<div
					v-if="!isReadOnly"
					ref="toolbarRef"
					class="floating-toolbar"
					:class="{ collapsed: isCollapsed }"
					:style="{ left: toolbarPos.x + 'px', top: toolbarPos.y + 'px' }"
					@mousedown="startDrag"
				>
					<div class="toolbar-handle" @dblclick="toggleCollapse">
						<i class="fa fa-ellipsis-v"></i> <i class="fa fa-ellipsis-v"></i>
						<span class="pull-right collapse-btn" @click.stop="toggleCollapse">
							<i
								class="fa"
								:class="isCollapsed ? 'fa-angle-down' : 'fa-angle-up'"
							></i>
						</span>
					</div>
					<div class="btn-group-vertical" v-show="!isCollapsed">
						<button
							class="btn btn-xs btn-default"
							@click="addNode('selector')"
							:title="__('Add Action')"
						>
							<i class="fa fa-plus-circle"></i> {{ __("Add Action") }}
						</button>
						<div class="divider-horizontal"></div>
						<button
							class="btn btn-xs btn-link text-muted toolbar-sub-btn"
							@click="addNode('condition')"
						>
							<i class="fa fa-code-fork"></i> {{ __("Condition") }}
						</button>
						<button
							class="btn btn-xs btn-link text-muted toolbar-sub-btn"
							@click="addNode('process')"
						>
							<i class="fa fa-cog"></i> {{ __("Process") }}
						</button>
						<button
							class="btn btn-xs btn-link text-muted toolbar-sub-btn"
							@click="addNode('set value')"
						>
							<i class="fa fa-edit"></i> {{ __("Set Value") }}
						</button>
						<button
							class="btn btn-xs btn-link text-muted toolbar-sub-btn"
							@click="addNode('sub-rule')"
						>
							<i class="fa fa-cube"></i> {{ __("Sub-Rule") }}
						</button>
					</div>
				</div>
			</div>
			<div
				class="sidebar-container"
				:class="{ 'sidebar-rtl': isRTL }"
				v-if="showSidebar"
				@click.stop
			>
				<Sidebar @close="closeSidebar" />
			</div>
		</div>
		<RuleConfigModal
			v-if="store.show_config_modal"
			v-model="store.show_config_modal"
			:node="store.nodes.find((n) => n.id === store.selected_id)"
			@save="store.mark_dirty()"
		/>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { VueFlow, Panel, PanelPosition } from "@vue-flow/core";
import { useVueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { useStore } from "./store";
import { isTerminalAction } from "../core/contracts";

import { generateShortId } from "../utils/index.js";
import "../utils/utils.js";

import StartNode from "./components/nodes/StartNode.vue";
import ProcessNode from "./components/nodes/ProcessNode.vue";
import ConditionNode from "./components/nodes/ConditionNode.vue";
import LoopNode from "./components/nodes/LoopNode.vue";
import StopNode from "./components/nodes/StopNode.vue";
import ActionSelectorNode from "./components/nodes/ActionSelectorNode.vue";

import Sidebar from "./components/Sidebar.vue";
import RuleConfigModal from "./components/rule_config/RuleConfigModal.vue";

const props = defineProps({ rule: String });
const store = useStore();
const { zoomIn, zoomOut, removeEdges } = useVueFlow();
let vfInstance = null;

const toolbarRef = ref(null);
const toolbarPos = ref({ x: 20, y: 20 });
let isDragging = false;
let dragOffset = { x: 0, y: 0 };

function startDrag(e) {
	// Only allow dragging from the handle or the container background, not buttons
	if (e.target.closest("button")) return;

	isDragging = true;
	const rect = toolbarRef.value.getBoundingClientRect();
	const parentRect = toolbarRef.value.parentElement.getBoundingClientRect();

	// Calculate offset relative to the toolbar's top-left corner
	dragOffset.x = e.clientX - rect.left;
	dragOffset.y = e.clientY - rect.top;

	window.addEventListener("mousemove", onDrag);
	window.addEventListener("mouseup", stopDrag);
}

function onDrag(e) {
	if (!isDragging) return;
	const parentRect = toolbarRef.value.parentElement.getBoundingClientRect();

	// Calculate new position relative to parent container
	let newX = e.clientX - parentRect.left - dragOffset.x;
	let newY = e.clientY - parentRect.top - dragOffset.y;

	// Constrain to container bounds
	const maxX = parentRect.width - toolbarRef.value.offsetWidth;
	const maxY = parentRect.height - toolbarRef.value.offsetHeight;

	newX = Math.max(0, Math.min(newX, maxX));
	newY = Math.max(0, Math.min(newY, maxY));

	toolbarPos.value = { x: newX, y: newY };
}

function stopDrag() {
	isDragging = false;
	window.removeEventListener("mousemove", onDrag);
	window.removeEventListener("mouseup", stopDrag);
}

const isCollapsed = ref(false);

function toggleCollapse() {
	isCollapsed.value = !isCollapsed.value;
}

const showDisabledNodes = ref(true);

const nodes = computed({
	get: () => {
		return (store.nodes || []).filter((el) => {
			if (el.type === "start") return true;
			// Filtering
			if (!showDisabledNodes.value && el.data?.is_enabled === 0) return false;
			return true;
		});
	},
	set: (val) => {
		const currentIds = new Set(val.map((n) => n.id));
		// Preserve hidden nodes
		const hiddenNodes = store.nodes.filter((el) => !currentIds.has(el.id));
		store.nodes = [...val, ...hiddenNodes];
	},
});

const edges = computed({
	get: () => store.edges || [],
	set: (val) => {
		store.edges = val;
	},
});

const showSidebar = computed(() => store.selected_id !== null);
const isRTL = computed(() => document.documentElement.dir === "rtl");
const isReadOnly = computed(() => store.is_read_only);

function closeSidebar() {
	store.selected_id = null;
}

function onPaneReady(instance) {
	vfInstance = instance;
	instance.fitView();
}

onMounted(async () => {
	if (props.rule) store.rule_name = props.rule;
	await store.fetch();
	autoConnectStartNode();
	window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
	window.removeEventListener("keydown", handleKeydown);
});

function handleKeydown(e) {
	// Save: Ctrl+S
	if ((e.ctrlKey || e.metaKey) && e.key === "s") {
		e.preventDefault();
		store.save_changes();
	}
	// Undo: Ctrl+Z
	if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
		e.preventDefault();
		if (store.can_undo()) store.undo();
	}
	// Redo: Ctrl+Y or Ctrl+Shift+Z
	if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
		e.preventDefault();
		if (store.can_redo()) store.redo();
	}
}

function hasOutgoingEdge(nodeId) {
	return (store.edges || []).some((edge) => edge.source === nodeId);
}

function getAutoConnectSource() {
	const selectedNode = (store.nodes || []).find((node) => node.id === store.selected_id);
	const selectedActionType = selectedNode?.data?.action_type || selectedNode?.type;
	if (
		selectedNode &&
		selectedNode.type !== "selector" &&
		selectedNode.type !== "condition" &&
		!isTerminalAction(selectedActionType) &&
		!hasOutgoingEdge(selectedNode.id)
	) {
		return selectedNode;
	}

	const startNode = (store.nodes || []).find(
		(node) => node.id === "start" || node.type === "start"
	);
	if (startNode && !hasOutgoingEdge(startNode.id)) {
		return startNode;
	}

	return null;
}

function getNextNodePosition(parentNode = null) {
	if (parentNode?.position) {
		return {
			x: (parentNode.position.x || 0) + 300,
			y: parentNode.position.y || 0,
		};
	}

	const placedNodes = (store.nodes || []).filter(
		(node) =>
			node.type !== "start" &&
			Number.isFinite(node.position?.x) &&
			Number.isFinite(node.position?.y)
	);
	if (placedNodes.length) {
		const lastNode = placedNodes[placedNodes.length - 1];
		return {
			x: (lastNode.position.x || 0) + 260,
			y: lastNode.position.y || 0,
		};
	}

	return { x: 340, y: 255 };
}

function autoConnectNode(nodeId, parentNode = null) {
	const sourceNode = parentNode || getAutoConnectSource();
	if (!sourceNode) return;

	const sourceHandle = sourceNode.type === "condition" ? null : "default";
	const edgeId = `e-${sourceNode.id}-${nodeId}-${sourceHandle || "default"}`;
	const exists = (store.edges || []).some(
		(edge) =>
			edge.source === sourceNode.id &&
			edge.target === nodeId &&
			(edge.sourceHandle || "default") === (sourceHandle || "default")
	);
	if (exists) return;

	store.edges.push({
		id: edgeId,
		source: sourceNode.id,
		target: nodeId,
		sourceHandle: sourceHandle || "default",
		animated: sourceNode.type === "start",
	});
}

function addNode(type, position) {
	const id = generateShortId();
	let label = "";
	let actionType = "";
	const parentNode = getAutoConnectSource();
	const resolvedPosition = position || getNextNodePosition(parentNode);

	const nodeData = store.get_default_node_data(type.toLowerCase(), label);
	const nodeType = mapActionTypeToNodeType(nodeData.action_type);
	const newNode = {
		id,
		type: nodeType,
		position: resolvedPosition,
		label: nodeData.action_label,
		data: {
			...nodeData,
			action_id: id,
			suggested_parent_id: parentNode?.id || null,
			suggested_source_handle: parentNode?.type === "condition" ? "true" : "default",
		},
	};

	store.nodes.push(newNode);
	autoConnectNode(id, parentNode);
	store.selected_id = id;
	store.mark_dirty();

	if (vfInstance) {
		setTimeout(() => {
			vfInstance.setCenter(newNode.position.x + 100, newNode.position.y, {
				zoom: 1,
				duration: 500,
			});
		}, 50);
	}
}
function autoConnectStartNode() {
	const startNode = (store.nodes || []).find((el) => el.id === "start" || el.type === "start");
	if (!startNode) return;

	// Check if start node has any outgoing edges
	const hasStartEdge = (store.edges || []).some((el) => el.source === startNode.id);
	if (hasStartEdge) return;

	const firstNode = (store.nodes || []).find(
		(el) => el.type !== "start" && el.data?.is_enabled !== 0
	);
	if (firstNode) {
		store.edges.push({
			id: `e-${startNode.id}-${firstNode.id}`,
			source: startNode.id,
			target: firstNode.id,
			sourceHandle: "default",
			animated: true,
		});
	}
}

function onNodeClick(event) {
	store.selected_id = event.node.id;
}
function onNodeDblClick(event) {
	store.selected_id = event.node.id;
	if (event.node.type !== "start") {
		store.show_config_modal = true;
	}
}
function onPaneClick() {
	store.selected_id = null;
}

function onConnect(params) {
	const sourceHandle = params.sourceHandle || "default";
	const id = `e-${params.source}-${params.target}-${sourceHandle}`;

	// Check for existing connection to avoid duplicates
	const exists = (store.edges || []).some(
		(e) =>
			e.source === params.source &&
			e.target === params.target &&
			(e.sourceHandle || "default") === sourceHandle
	);

	if (exists) {
		// console.warn("Connection already exists", id);
		return;
	}

	const newEdge = {
		id,
		source: params.source,
		target: params.target,
		sourceHandle,
		animated: store.nodes.find((el) => el.id === params.source)?.type === "start",
	};
	store.edges.push(newEdge);
	store.mark_dirty();
}

function onNodesChange(changes) {
	const hasDrag = changes.some((c) => c.type === "position" && c.dragging === false);
	if (hasDrag) store.mark_position_change();
}

function onEdgesChange(changes) {
	changes.forEach((change) => {
		if (change.type === "remove") {
			store.delete_edge(change.id);
		}
	});
}

function onDragStart(event, nodeType) {
	if (event.dataTransfer) {
		event.dataTransfer.setData("text/plain", nodeType);
		event.dataTransfer.effectAllowed = "move";
	}
}

function onDragOver(event) {
	event.preventDefault();
	if (event.dataTransfer) {
		event.dataTransfer.dropEffect = "move";
	}
}

const flowWrapper = ref(null);

function onDrop(event) {
	event.preventDefault();

	const nodeType = event.dataTransfer?.getData("text/plain");
	if (!nodeType || !vfInstance) return;

	const bounds = flowWrapper.value.getBoundingClientRect();

	const position = vfInstance.project({
		x: event.clientX - bounds.left,
		y: event.clientY - bounds.top,
	});

	addNode(nodeType, position);
}

function onEdgeClick({ edge, event }) {
	event?.stopPropagation();

	frappe.confirm(__("Delete this connection?"), () => {
		removeEdges([edge.id]);
	});
}

/**
 * Universal mapper from Action Type (DocField value) to VueFlow Node Type (slot name)
 */
function mapActionTypeToNodeType(actionType) {
	if (!actionType) return "process";
	const type = actionType.toLowerCase().trim();

	if (type === "selector") return "selector";
	if (type === "entry action" || type === "start") return "start";
	if (type === "condition") return "condition";
	if (type === "loop") return "loop";
	if (type === "wait") return "wait";
	if (type === "notify") return "notify";
	if (type === "sub-rule") return "sub-rule";
	if (type === "query records") return "query";
	if (type === "aggregate records") return "aggregate";
	if (type === "document action" || type === "create docs") return "documentaction";
	if (type === "set value") return "set-value";
	if (type === "raise error") return "raise-error";

	return "process";
}
</script>

<style>
@import "@vue-flow/core/dist/style.css";
@import "@vue-flow/core/dist/theme-default.css";

.rule-builder-container {
	display: flex;
	flex-direction: column;
	height: calc(100vh - var(--navbar-height) - var(--page-head-height) - 60px);
}
/* Removed .builder-toolbar */

.builder-main {
	flex: 1;
	display: flex;
	position: relative;
	overflow: hidden;
}
/* ... */
.controls-panel {
	display: flex;
	align-items: center;
	gap: 10px;
	background: rgba(255, 255, 255, 0.8);
	padding: 5px 10px;
	border-radius: 4px;
	border: 1px solid var(--border-color);
	backdrop-filter: blur(2px);
}
.divider-vertical {
	width: 1px;
	height: 20px;
	background-color: var(--border-color);
}
.show-disabled-control {
	display: flex;
	align-items: center;
	gap: 5px;
}
.sidebar-container {
	position: relative;
	height: 100%;
	margin-left: 10px;
	border-radius: var(--border-radius-lg);
	border: 1px solid var(--border-color);
	background-color: var(--fg-color);
	order: 2;
}
.canvas-container {
	flex: 1;
	height: 100%;
	border-radius: var(--border-radius-lg);
	border: 1px solid var(--border-color);
	background-color: var(--fg-color);
	position: relative;
	order: 1;
}
.toolbar-center {
	display: flex;
	align-items: center;
	justify-content: center;
	flex: 1;
}

.floating-toolbar {
	position: absolute;
	z-index: 100;
	min-width: 140px; /* Adjust based on preference */
	background: var(--card-bg, #fff);
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-md);
	box-shadow: var(--shadow-base);
	padding: 10px;
	display: flex;
	flex-direction: column;
	gap: 8px;
	cursor: move;
}

.floating-toolbar .toolbar-handle {
	text-align: center;
	color: var(--text-muted);
	font-size: 10px;
	cursor: move;
	margin-bottom: 5px;
	border-bottom: 1px solid var(--border-color);
	padding-bottom: 5px;
}

.floating-toolbar .btn-group-vertical {
	display: flex;
	flex-direction: column;
	gap: 5px;
}

.floating-toolbar button {
	text-align: left;
	width: 100%;
}

.floating-toolbar.collapsed {
	min-width: auto;
	width: 40px;
}

.collapse-btn {
	cursor: pointer;
	padding: 0 4px;
	opacity: 0.6;
}
.collapse-btn:hover {
	opacity: 1;
}

/* Removed .rule-status-toggle logic */
.switch {
	position: relative;
	display: inline-block;
	width: 32px;
	height: 18px;
	margin: 0;
}
.switch input {
	opacity: 0;
	width: 0;
	height: 0;
}
.slider {
	position: absolute;
	cursor: pointer;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: #ccc;
	transition: 0.4s;
	border-radius: 34px;
}
.slider:before {
	position: absolute;
	content: "";
	height: 14px;
	width: 14px;
	left: 2px;
	bottom: 2px;
	background-color: white;
	transition: 0.4s;
	border-radius: 50%;
}

.read-only-badge {
	background-color: var(--orange-100);
	color: var(--orange-600);
	padding: 2px 8px;
	border-radius: 12px;
	font-size: 11px;
	font-weight: 600;
	display: flex;
	align-items: center;
	gap: 4px;
	border: 1px solid var(--orange-300);
}
input:checked + .slider {
	background-color: var(--primary);
}
input:focus + .slider {
	box-shadow: 0 0 1px var(--primary);
}
input:checked + .slider:before {
	transform: translateX(14px);
}

.small-switch {
	width: 28px;
	height: 16px;
	margin: 0;
}
.small-switch .slider:before {
	height: 12px;
	width: 12px;
}
.small-switch input:checked + .slider:before {
	transform: translateX(12px);
}

/* RTL sidebar positioning */
.sidebar-rtl {
	order: 0;
	margin-left: 0;
	margin-right: 10px;
}

.divider-horizontal {
	height: 1px;
	background: var(--border-color);
	margin: 4px 0;
	opacity: 0.6;
}

.toolbar-sub-btn {
	justify-content: flex-start !important;
	padding-left: 8px !important;
	font-weight: 500;
	opacity: 0.8;
}

.toolbar-sub-btn:hover {
	opacity: 1;
	background: var(--gray-50);
	text-decoration: none;
}

.toolbar-sub-btn i {
	width: 14px;
	margin-right: 6px;
	text-align: center;
}
</style>
