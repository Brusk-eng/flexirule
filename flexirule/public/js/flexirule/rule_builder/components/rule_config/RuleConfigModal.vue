<template>
	<Teleport to="body">
		<transition name="fade">
			<div v-if="modelValue" class="config-modal-overlay" @click.self="cancel">
				<div class="config-modal-container">
					<header class="config-modal-header">
						<div class="header-left">
							<div class="header-icon mr-2" v-if="draftNode">
								<i :class="draftNode.data?.icon || getIcon(draftNode.type)"></i>
							</div>
							<h3>{{ title }}</h3>
						</div>
						
						<!-- Centered Navigation -->
						<div class="header-center">
							<div class="modal-navigation">
								<button 
									class="nav-btn" 
									@click="store.prev_config_node()"
									:title="__('Previous Node')"
								>
									<i class="fa fa-chevron-left"></i>
								</button>
								<div class="nav-status">
									{{ currentNodeIndex + 1 }} / {{ totalNodes }}
								</div>
								<button 
									class="nav-btn" 
									@click="store.next_config_node()"
									:title="__('Next Node')"
								>
									<i class="fa fa-chevron-right"></i>
								</button>
							</div>
						</div>

						<div class="header-right">
							<button class="btn-close-modal" @click="cancel">×</button>
						</div>
					</header>

					<main class="config-modal-body">
						<!-- Content based on Mode -->
						<template v-if="store.config_modal_mode === 'logic'">
							<div class="conditions-view p-4">
								<ConditionStep 
									:node="draftNode" 
									:read-only="store.is_read_only" 
									:ref="panelRefs.logic"
								/>
							</div>
						</template>

						<template v-else>
							<!-- Start Node Setup -->
							<div v-if="draftNode?.type === 'start'" class="start-node-setup p-5">
								<div class="setup-container">
									<header class="section-header mb-4">
										<h4>{{ __("Trigger Configuration") }}</h4>
										<p class="text-muted">{{ __("Configure how and when this rule is triggered.") }}</p>
									</header>
									<StartNodeProperties 
										:nodeData="draftNode.data"
										:readOnly="store.is_read_only"
										@update:field="(f, v) => draftNode.data[f] = v"
										@open:conditions="store.config_modal_mode = 'logic'"
									/>
								</div>
							</div>

							<!-- Standard Action Setup -->
							<ResizablePanel v-else-if="draftNode">
								<!-- Left Panel: Input Selection -->
								<div class="resizable-panel left-panel" v-if="showLeftPanel">
									<InputPanel :node="draftNode" :readOnly="store.is_read_only" :ref="panelRefs.input" />
								</div>

								<div class="panel-resizer" v-if="showLeftPanel"></div>

								<!-- Middle Panel: Dynamic Configuration -->
								<div class="resizable-panel middle-panel">
									<ConfigurationPanel :node="draftNode" :readOnly="store.is_read_only" :ref="panelRefs.config" />
								</div>

								<div class="panel-resizer" v-if="showRightPanel"></div>

								<!-- Right Panel: Output/Mapping -->
								<div class="resizable-panel right-panel" v-if="showRightPanel">
									<OutputPanel :node="draftNode" :readOnly="store.is_read_only" :ref="panelRefs.output" />
								</div>
							</ResizablePanel>
						</template>
					</main>

					<footer class="config-modal-footer">
						<div class="footer-left">
							<!-- Optional: Status info or reset -->
						</div>
						<div class="footer-right">
							<button class="btn btn-default" @click="cancel">
								{{ store.is_read_only ? __("Close") : __("Cancel") }}
							</button>
							<button v-if="!store.is_read_only" class="btn btn-primary ml-2" @click="save">
								{{ __("Save Changes") }}
							</button>
						</div>
					</footer>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import ResizablePanel from "./ResizablePanel.vue";
import InputPanel from "./InputPanel.vue";
import ConfigurationPanel from "./ConfigurationPanel.vue";
import OutputPanel from "./OutputPanel.vue";
import ConditionStep from "./types/ConditionStep.vue";
import StartNodeProperties from "../StartNodeProperties.vue";
import { useStore } from "../../store";
import { useRuleConfig } from "../../composables/useRuleConfig";

const props = defineProps({
	modelValue: Boolean,
	node: Object,
});

const emit = defineEmits(["update:modelValue", "save"]);
const store = useStore();

const { 
	draftNode, 
	panelRefs, 
	save, 
	cancel 
} = useRuleConfig(props, emit);

const actionType = computed(() => (draftNode.value?.data?.action_type || draftNode.value?.type)?.toLowerCase());

const totalNodes = computed(() => store.nodes.length);
const currentNodeIndex = computed(() => {
	if (!store.selected_id) return -1;
	return store.nodes.findIndex(n => n.id === store.selected_id);
});

const title = computed(() => {
	if (!draftNode.value) return __("Rule Configuration");
	let baseTitle = draftNode.value.data?.action_label || draftNode.value.label || __("Rule Configuration");
	let suffix = store.config_modal_mode === 'logic' ? ` [${__("Logic")}]` : "";
	return baseTitle + suffix;
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
	let config = { input: false, config: true, output: false };

	if (type === 'process') {
		config = { input: true, config: true, output: true };
	} else if (['condition', 'set value', 'raise error', 'notify'].includes(type)) {
		config = { input: true, config: true, output: false };
	}
	
	return config;
});

const showLeftPanel = computed(() => layoutConfig.value.input);
const showRightPanel = computed(() => layoutConfig.value.output);
</script>

<style scoped>
/* ... (Existing styles kept) ... */

/* Navigation */
.modal-navigation {
	display: flex;
	align-items: center;
	background: #f1f5f9;
	padding: 4px;
	border-radius: 8px;
	gap: 8px;
}

.nav-btn {
	width: 28px;
	height: 28px;
	border-radius: 6px;
	border: none;
	background: transparent;
	color: #64748b;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.2s;
}

.nav-btn:hover {
	background: #fff;
	color: var(--primary);
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.nav-status {
	font-size: 11px;
	font-weight: 700;
	color: #64748b;
	min-width: 40px;
	text-align: center;
}

.conditions-view {
	height: 100%;
	overflow-y: auto;
	background: #f8fafc;
}

.start-node-setup {
	height: 100%;
	overflow-y: auto;
	background: #f8fafc;
	display: flex;
	justify-content: center;
}

.setup-container {
	width: 100%;
	max-width: 600px;
	background: #fff;
	padding: 32px;
	border-radius: 12px;
	border: 1px solid var(--border-color);
	height: fit-content;
	margin: 20px;
}

.section-header h4 {
	font-weight: 700;
	margin-bottom: 4px;
}
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
	padding: 24px;
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

.header-center {
	flex: 1;
	display: flex;
	justify-content: center;
}

.header-right {
	display: flex;
	align-items: center;
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

.config-modal-footer {
	height: 60px;
	border-top: 1px solid var(--border-color);
	background: #fff;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 24px;
}

.footer-right {
	display: flex;
	align-items: center;
}

/* Default 2-panel or 3-panel logic handled via flex */
.left-panel {
    flex: 0 0 20%;
    min-width: 250px;
	border-right: 1px solid var(--border-color);
	background: #fcfcfc;
}

.middle-panel {
    flex: 1;
	min-width: 400px;
}

.right-panel {
    flex: 0 0 20%;
    min-width: 250px;
	border-left: 1px solid var(--border-color);
	background: #fcfcfc;
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

@media (max-width: 1200px) {
    .left-panel, .right-panel {
        flex: 0 0 25%;
    }
}

@media (max-width: 992px) {
	.config-modal-overlay {
		padding: 12px;
	}
	
    .left-panel, .right-panel {
        display: none !important; /* Hide side panels on smaller screens to prioritize config */
    }
    
    .middle-panel {
        flex: 1;
        min-width: 0;
    }

	.config-modal-container {
		max-width: 100%;
	}
}

@media (max-width: 768px) {
    .config-modal-header {
        padding: 0 12px;
    }
    
    .header-left h3 {
        font-size: 14px;
    }
    
    .modal-navigation {
        gap: 4px;
    }
}
</style>
