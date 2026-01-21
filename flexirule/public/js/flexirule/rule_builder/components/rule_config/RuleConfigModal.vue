<template>
	<Teleport to="body">
		<transition name="fade">
			<div v-if="modelValue" class="config-modal-overlay" @click.self="close">
				<div class="config-modal-container">
					<header class="config-modal-header">
						<div class="header-left">
							<!-- Replaced badge with simple title or icon if needed -->
                            <div class="header-icon mr-2" v-if="localNode">
                                <i :class="localNode.data?.icon || getIcon(localNode.type)"></i>
                            </div>
							<h3>{{ title }}</h3>
							<!-- Experimental toggle moved or kept if needed, assuming user ignored it -->
						</div>
						<div class="header-actions">
							<button class="btn btn-sm btn-default mr-2" v-if="actionType === 'process'" @click="useExperimentalV2 = !useExperimentalV2">
								<i class="fa fa-flask"></i> {{ useExperimentalV2 ? __("Standard View") : __("V2 Vision") }}
							</button>
							<button class="btn btn-sm btn-default" @click="close">
								{{ __("Cancel") }}
							</button>
							<button class="btn btn-sm btn-primary ml-2" @click="save">
								{{ __("Save Changes") }}
							</button>
							<button class="btn-close-modal ml-3" @click="close">×</button>
						</div>
					</header>

					<main class="config-modal-body">
						<ResizablePanel v-if="localNode && !useExperimentalV2">
							<!-- Left Panel: Input Selection -->
							<div class="resizable-panel left-panel" v-if="showLeftPanel">
								<InputPanel :node="localNode" ref="inputPanelRef" />
							</div>

							<div class="panel-resizer" v-if="showLeftPanel"></div>

							<!-- Middle Panel: Dynamic Configuration -->
							<div class="resizable-panel middle-panel">
								<ConfigurationPanel :node="localNode" ref="configurationPanelRef" />
							</div>

							<div class="panel-resizer" v-if="showRightPanel"></div>

							<!-- Right Panel: Output/Mapping -->
							<div class="resizable-panel right-panel" v-if="showRightPanel">
								<OutputPanel :node="localNode" ref="outputPanelRef" />
							</div>
						</ResizablePanel>

						<V2PreviewPanel v-else-if="localNode && useExperimentalV2" />
					</main>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import { computed, ref, watch, nextTick } from "vue";
import ResizablePanel from "./ResizablePanel.vue";
import InputPanel from "./InputPanel.vue";
import ConfigurationPanel from "./ConfigurationPanel.vue";
import OutputPanel from "./OutputPanel.vue";
import V2PreviewPanel from "./V2PreviewPanel.vue";
import { useStore } from "../../store";
import { validateAgainstContract, getContract } from "../../../core/contracts.js";

const props = defineProps({
	modelValue: Boolean,
	node: Object,
});

const emit = defineEmits(["update:modelValue", "save"]);
const store = useStore();

const localNode = ref(null); // Draft copy
// Detect action type for UI hints, fallback to props
const actionType = computed(() => (localNode.value?.data?.action_type || props.node?.data?.action_type || props.node?.type)?.toLowerCase());

const useExperimentalV2 = ref(false);

// Watch for node changes or modal open to create draft
watch(() => [props.node, props.modelValue], ([newNode, isOpen]) => {
	if (isOpen && newNode) {
		// Deep clone logic. Using JSON parse/stringify is safe enough for this data structure usually,
		// but we need to ensure we don't lose reactive references if child panels expect them?
		// Actually, child panels likely expect a standard object. 
		// Node structure: { id, type, label, data: {...}, ... }
		// We want to edit 'data' primarily.
		localNode.value = JSON.parse(JSON.stringify(newNode));
	}
}, { immediate: true });


const title = computed(() => {
	if (!localNode.value) return __("Rule Configuration");
	return localNode.value.data?.action_label || localNode.value.label || __("Rule Configuration");
});

function getIcon(type) {
	if (!type) return 'fa fa-circle';
	const icons = {
		'process': 'fa fa-cog',
		'condition': 'fa fa-code-fork',
		'loop': 'fa fa-refresh',
		'switch': 'fa fa-code-fork rotate-90',
		'sub-rule': 'fa fa-cube',
		'wait': 'fa fa-clock-o',
		'start': 'fa fa-play',
		'stop': 'fa fa-stop'
	};
	return icons[type.toLowerCase()] || 'fa fa-circle';
}

// -- Dynamic Layout Logic --

const layoutConfig = computed(() => {
	const type = actionType.value;
	
	// Default: Config Only
	let config = { input: false, config: true, output: false };

	if (type === 'process') {
		config = { input: true, config: true, output: true };
	} else if (['condition', 'set value', 'raise error', 'notify'].includes(type)) {
		// Enabled Input panel for variable binding/visibility
		config = { input: true, config: true, output: false };
	} else if (type === 'loop') {
		// Loop uses iterator config, output usually handled implicitly or via child nodes.
		// If we want explicit output mapping (e.g. aggregation), we enalbe output.
		// For now, simple Config only as per standard.
		config = { input: false, config: true, output: false };
	}
	
	return config;
});

const showLeftPanel = computed(() => layoutConfig.value.input);
const showRightPanel = computed(() => layoutConfig.value.output);

const inputPanelRef = ref(null);
const configurationPanelRef = ref(null);
const outputPanelRef = ref(null);

function close() {
	// Just close, discarding localNode changes
	emit("update:modelValue", false);
}

async function save() {
	const errors = [];

	// 0. Validate against ACTION_TYPE_CONTRACT
	const contractResult = validateAgainstContract(localNode.value?.data);
	if (!contractResult.valid) {
		errors.push(...contractResult.errors);
	}

	// 1. Validate Input Panel
	if (showLeftPanel.value && inputPanelRef.value && typeof inputPanelRef.value.validate === "function") {
		const res = await inputPanelRef.value.validate();
		if (!res.valid) {
			if (res.errors) errors.push(...res.errors);
			if (res.message) errors.push(res.message);
		}
	}

	// 2. Validate Configuration Panel
	if (configurationPanelRef.value && typeof configurationPanelRef.value.validate === "function") {
		const res = await configurationPanelRef.value.validate();
		if (!res.valid) {
			if (res.errors) errors.push(...res.errors);
			if (res.message) errors.push(res.message);
		}
	}

	// 3. Validate Output Panel
	if (showRightPanel.value && outputPanelRef.value && typeof outputPanelRef.value.validate === "function") {
		const res = await outputPanelRef.value.validate();
		if (!res.valid) {
			if (res.errors) errors.push(...res.errors);
			if (res.message) errors.push(res.message);
		}
	}

	if (errors.length > 0) {
		const message = errors.map(e => `<li>${e}</li>`).join("");
		frappe.msgprint({
			title: __("Validation Error"),
			message: `<ul class="text-left" style="list-style-type: disc; padding-left: 20px;">${message}</ul>`,
			indicator: "red"
		});
		return;
	}

	// Commit changes from localNode to props.node
	if (props.node && localNode.value) {
		// 1. Update data
		props.node.data = JSON.parse(JSON.stringify(localNode.value.data));
		// 2. Update label if changed
		props.node.label = localNode.value.label;
		
		// 3. Mark dirty in store
		store.mark_dirty();
	}

	emit("save");
	close();
}
</script>

<style scoped>
/* ... (Existing styles kept) ... */

/* Dynamic sizing overrides if needed, but flex:1 on middle-panel usually handles it. 
   We just need to ensure initial width or flex-grow is aggressive. */
.middle-panel {
	flex: 2; /* Increased flex grow to favored size */
	min-width: 400px;
    border-right: 1px solid var(--border-color, #e2e8f0); /* Visual separation if right panel hidden */
}

/* Hide border if right panel is missing */
.middle-panel:last-child {
    border-right: none;
}

/* ... */
</style>

<style scoped>
.config-modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background: rgba(var(--gray-900-rgb, 0, 0, 0), 0.6);
	backdrop-filter: blur(8px);
	z-index: 2000;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 40px;
}

.config-modal-container {
	background: #fff;
	width: 100%;
	height: 100%;
	max-width: 1600px;
	border-radius: 12px;
	box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.config-modal-header {
	height: 64px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 24px;
	border-bottom: 1px solid var(--border-color);
	background: #fcfcfc;
}

.header-left {
	display: flex;
	align-items: center;
	gap: 12px;
}

.header-left h3 {
	margin: 0;
	font-size: 18px;
	font-weight: 600;
	color: var(--text-color);
}

.v2-badge {
	font-size: 10px;
	font-weight: 700;
	padding: 3px 6px;
	border-radius: 4px;
	background: var(--primary);
	color: #fff;
}

.v2-toggle {
	display: flex;
	align-items: center;
	gap: 10px;
}

.v2-toggle-label {
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted);
}

.switch-v2 {
	position: relative;
	display: inline-block;
	width: 32px;
	height: 18px;
}

.switch-v2 input {
	opacity: 0;
	width: 0;
	height: 0;
}

.slider-v2 {
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

.slider-v2:before {
	position: absolute;
	content: "";
	height: 14px;
	width: 14px;
	left: 2px;
	bottom: 2px;
	background-color: #fff;
	transition: 0.4s;
	border-radius: 50%;
}

input:checked + .slider-v2 {
	background-color: var(--primary);
}

input:checked + .slider-v2:before {
	transform: translateX(14px);
}

.config-modal-body {
	flex: 1;
	overflow: hidden;
}

/* Panel Layouts */
.resizable-panel {
	height: 100%;
	overflow-y: auto;
	background: #fff;
    transition: all 0.3s ease;
}

/* Default 2-panel or 3-panel logic handled via flex */
.left-panel {
    /* Default behavior: Fixed or Flex? */
    /* User wants 3-panel logic specifically. */
    flex: 0 0 20%; /* 20% by default in 3-panel mode */
    min-width: 250px;
	border-right: 1px solid var(--border-color);
	background: #f9f9f9;
}

.middle-panel {
    flex: 0 0 60%; /* 60% fixed ratio when 3 panels */
	min-width: 400px;
    border-right: 1px solid var(--border-color, #e2e8f0);
}

.right-panel {
    flex: 0 0 20%; /* Remaining 20% */
	min-width: 250px;
	border-left: 1px solid var(--border-color);
	background: #f9f9f9;
}

/* Adjustments if Right Panel is HIDDEN (2-panel mode) */
/* We rely on Vue to remove the right-panel DOM element. */
/* If right panel is gone, Middle panel should take available space or specific ratio? */
/* CSS Selector hacking: if right-panel is missing, middle-panel should grow. */
/* But styling applies to classes. We can use :last-child on middle-panel? */
.middle-panel:last-child {
    flex: 1; /* Take remaining space if it's the last child (no right panel) */
    border-right: none;
}

/* If Left panel also missing? (Future proofing) */
.middle-panel:first-child {
    flex: 1;
}

.btn-close-modal {
	background: none;
	border: none;
	font-size: 24px;
	color: var(--text-muted);
	cursor: pointer;
	line-height: 1;
	padding: 0;
}

.btn-close-modal:hover {
	color: var(--text-color);
}

.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}

@media (max-width: 992px) {
	.config-modal-overlay {
		padding: 0;
	}
	
	.config-modal-container {
		border-radius: 0;
	}
	
	.left-panel, .right-panel {
		width: 100% !important;
	}
}
</style>
