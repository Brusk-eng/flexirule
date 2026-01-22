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
							:draggable="true"
							@dragstart="onDragStart($event, 'selector')"
							@click="addNode('selector')"
							:title="__('Add Action')"
						>
							<i class="fa fa-plus-circle"></i> {{ __("Add Action") }}
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
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { VueFlow, Panel, PanelPosition } from "@vue-flow/core";
import { useVueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { useStore } from "./store";
import { generateShortId } from "../utils/index.js";
import "../utils/utils.js";

import StartNode from "./components/nodes/StartNode.vue";
import ProcessNode from "./components/nodes/ProcessNode.vue";
import ConditionNode from "./components/nodes/ConditionNode.vue";
import LoopNode from "./components/nodes/LoopNode.vue";
import StopNode from "./components/nodes/StopNode.vue";
import ActionSelectorNode from "./components/nodes/ActionSelectorNode.vue";
import Sidebar from "./components/Sidebar.vue";

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
function addNode(type, position) {
	const id = generateShortId();
	let label = "";
	let actionType = "";

	switch (type) {
		case "process":
			label = __("New Process");
			actionType = "Process";
			break;
		case "condition":
			label = __("New Condition");
			actionType = "Condition";
			break;
		case "switch":
			label = __("New Switch");
			actionType = "Switch";
			break;
		case "loop":
			label = __("Loop");
			actionType = "Loop";
			break;
		case "wait":
			label = __("Wait");
			actionType = "Wait";
			break;
		case "sub-rule":
			label = __("Sub Rule");
			actionType = "Sub-Rule";
			break;
		case "stop":
			label = __("Stop");
			actionType = "Stop";
			break;
		case "selector":
			label = __("New Action");
			actionType = "Selector";
			break;
		default:
			label = __("New Action");
			actionType = "Selector";
	}

	const newNode = {
		id,
		type,
		position,
		label,
		data: {
			action_id: id,
			action_type: actionType,
			action_label: label,
			is_enabled: 1,
		},
	};
	store.nodes.push(newNode);
	store.selected_id = id;
	store.mark_dirty();
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
function onPaneClick() {
	store.selected_id = null;
}

function onConnect(params) {
	const newEdge = {
		id: `e-${params.source}-${params.target}-${params.sourceHandle || "default"}`,
		source: params.source,
		target: params.target,
		sourceHandle: params.sourceHandle || "default",
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
</style>
