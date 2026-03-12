<template>
	<Teleport to="body">
		<transition name="fade">
			<div v-if="modelValue" class="config-modal-overlay" @click.self="cancel">
				<div class="config-modal-container">
					<header class="config-modal-header">
						<div class="header-left">
							<div class="header-icon" v-if="draftNode">
								<i
									:class="getIcon(draftNode.data?.action_type || draftNode.type)"
								></i>
							</div>
							<div class="header-title-container">
								<h3>{{ title }}</h3>
								<span v-if="draftNode?.data?.action_type" class="type-badge">
									{{ draftNode.data.action_type }}
								</span>
							</div>
						</div>

						<!-- Centered Navigation -->
						<div class="header-center">
							<div class="modal-navigation">
								<button
									class="nav-btn"
									@click="store.prev_config_node()"
									:title="__('Previous Node')"
									:disabled="currentNodeIndex <= 0"
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
									:disabled="currentNodeIndex >= totalNodes - 1"
								>
									<i class="fa fa-chevron-right"></i>
								</button>
							</div>
						</div>

						<div class="header-right">
							<button class="btn-close-modal" @click="cancel">
								<i class="fa fa-times"></i>
							</button>
						</div>
					</header>

					<main class="config-modal-body">
						<!-- Logic Mode (Conditions) -->
						<template v-if="store.config_modal_mode === 'logic'">
							<div class="conditions-view">
								<ConditionStep
									:node="draftNode"
									:read-only="store.is_read_only"
									:ref="panelRefs.logic"
								/>
							</div>
						</template>

						<!-- Standard Action Setup -->
						<template v-else>
							<!-- Start Node Setup (Full width) -->
							<div v-if="draftNode?.type === 'start'" class="start-node-setup">
								<div class="setup-container">
									<header class="section-header mb-4">
										<h4>{{ __("Trigger Configuration") }}</h4>
										<p class="text-muted">
											{{
												__("Configure how and when this rule is triggered.")
											}}
										</p>
									</header>
									<StartNodeProperties
										:nodeData="draftNode.data"
										:readOnly="store.is_read_only"
										@update:field="(f, v) => (draftNode.data[f] = v)"
										@open:conditions="store.config_modal_mode = 'logic'"
									/>
								</div>
							</div>

							<!-- Multi-panel Action Setup -->
							<ResizablePanel v-else-if="draftNode">
								<!-- Left Panel: Reference & Variables -->
								<div
									class="resizable-panel left-panel reference-panel"
									v-if="showLeftPanel"
								>
									<InputPanel
										:node="draftNode"
										:readOnly="store.is_read_only"
										:ref="panelRefs.input"
									/>
								</div>

								<div class="panel-resizer" v-if="showLeftPanel"></div>

								<!-- Middle Panel: Core Configuration -->
								<div class="resizable-panel middle-panel config-panel">
									<ConfigurationPanel
										:node="draftNode"
										:readOnly="store.is_read_only"
										:ref="panelRefs.config"
									/>
								</div>

								<div class="panel-resizer" v-if="showRightPanel"></div>

								<!-- Right Panel: Data IO (Mappings) -->
								<div
									class="resizable-panel right-panel io-panel"
									v-if="showRightPanel"
								>
									<OutputPanel
										:node="draftNode"
										:readOnly="store.is_read_only"
										:ref="panelRefs.output"
									/>
								</div>
							</ResizablePanel>
						</template>
					</main>

					<footer class="config-modal-footer">
						<div class="footer-left">
							<div v-if="store.is_dirty" class="dirty-indicator">
								<i class="fa fa-circle mr-1"></i>
								{{ __("Unsaved Changes") }}
							</div>
						</div>
						<div class="footer-right">
							<button class="btn btn-default btn-sm" @click="cancel">
								{{ store.is_read_only ? __("Close") : __("Cancel") }}
							</button>
							<button
								v-if="!store.is_read_only"
								class="btn btn-primary btn-sm ml-2"
								@click="save"
							>
								{{ __("Save Action") }}
							</button>
						</div>
					</footer>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import { computed } from "vue";
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

const { draftNode, panelRefs, save, cancel } = useRuleConfig(props, emit);

const actionType = computed(() =>
	(draftNode.value?.data?.action_type || draftNode.value?.type)?.toLowerCase()
);

const totalNodes = computed(() => store.nodes.length);
const currentNodeIndex = computed(() => {
	if (!store.selected_id) return -1;
	return store.nodes.findIndex((n) => n.id === store.selected_id);
});

const title = computed(() => {
	if (!draftNode.value) return __("Rule Configuration");
	let baseTitle =
		draftNode.value.data?.action_label || draftNode.value.label || __("Rule Configuration");
	let suffix = store.config_modal_mode === "logic" ? ` [${__("Logic")}]` : "";
	return baseTitle + suffix;
});

function getIcon(type) {
	if (!type) return "fa fa-circle";
	const icons = {
		process: "fa fa-cog",
		condition: "fa fa-code-fork",
		loop: "fa fa-refresh",
		switch: "fa fa-random",
		"sub-rule": "fa fa-cube",
		wait: "fa fa-clock-o",
		start: "fa fa-play",
		stop: "fa fa-stop",
		"query records": "fa fa-search",
		"aggregate records": "fa fa-calculator",
		"create docs": "fa fa-plus-circle",
		"set value": "fa fa-edit",
		"raise error": "fa fa-exclamation-triangle",
		notify: "fa fa-bell",
	};
	return icons[type.toLowerCase()] || "fa fa-circle";
}

// -- Optimized Layout Logic (Maintaining 3-panel support) --
const layoutConfig = computed(() => {
	const type = actionType.value;
	// By default, show Ref panel and Config panel.
	let config = { input: true, config: true, output: false };

	const complexActions = [
		"process",
		"query records",
		"aggregate records",
		"create docs",
		"set value",
		"notify",
		"raise error",
	];

	if (complexActions.includes(type)) {
		config.output = true;
	}

	// Structural nodes might only need config
	if (["loop", "switch", "wait", "sub-rule"].includes(type)) {
		config.input = true; // Still show Reference panel
		config.output = false;
	}

	return config;
});

const showLeftPanel = computed(() => layoutConfig.value.input);
const showRightPanel = computed(() => layoutConfig.value.output);
</script>

<style scoped>
.config-modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background: rgba(15, 23, 42, 0.6);
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
	border-radius: 16px;
	box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
	display: flex;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid #e2e8f0;
}

.config-modal-header {
	height: 72px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 24px;
	border-bottom: 1px solid #e2e8f0;
	background: #fcfcfc;
}

.header-left {
	display: flex;
	align-items: center;
	gap: 16px;
	flex: 1;
}

.header-icon {
	width: 40px;
	height: 40px;
	background: #f1f5f9;
	border-radius: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--primary);
	font-size: 18px;
	border: 1px solid #e2e8f0;
}

.header-title-container {
	display: flex;
	flex-direction: column;
}

.header-left h3 {
	margin: 0;
	font-size: 16px;
	font-weight: 700;
	color: #0f172a;
}

.type-badge {
	font-size: 10px;
	font-weight: 600;
	color: #64748b;
	text-transform: uppercase;
	letter-spacing: 0.5px;
}

.header-center {
	flex: 1;
	display: flex;
	justify-content: center;
}

.header-right {
	flex: 1;
	display: flex;
	justify-content: flex-end;
}

/* Navigation */
.modal-navigation {
	display: flex;
	align-items: center;
	background: #f1f5f9;
	padding: 4px;
	border-radius: 10px;
	gap: 8px;
	border: 1px solid #e2e8f0;
}

.nav-btn {
	width: 32px;
	height: 32px;
	border-radius: 8px;
	border: none;
	background: transparent;
	color: #64748b;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.2s;
}

.nav-btn:hover:not(:disabled) {
	background: #fff;
	color: var(--primary);
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.nav-btn:disabled {
	opacity: 0.3;
	cursor: default;
}

.nav-status {
	font-size: 11px;
	font-weight: 800;
	color: #475569;
	min-width: 50px;
	text-align: center;
}

.btn-close-modal {
	background: #f1f5f9;
	border: none;
	width: 32px;
	height: 32px;
	border-radius: 8px;
	font-size: 14px;
	color: #64748b;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.2s;
}

.btn-close-modal:hover {
	background: #fee2e2;
	color: #ef4444;
}

.config-modal-body {
	flex: 1;
	overflow: hidden;
	background: #fff;
}

.conditions-view {
	height: 100%;
	overflow-y: auto;
	background: #f8fafc;
	padding: 24px;
}

.start-node-setup {
	height: 100%;
	overflow-y: auto;
	background: #f8fafc;
	display: flex;
	justify-content: center;
	padding: 40px 20px;
}

.setup-container {
	width: 100%;
	max-width: 700px;
	background: #fff;
	padding: 40px;
	border-radius: 16px;
	border: 1px solid #e2e8f0;
	height: fit-content;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.config-modal-footer {
	height: 72px;
	border-top: 1px solid #e2e8f0;
	background: #fcfcfc;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 24px;
}

.dirty-indicator {
	font-size: 11px;
	font-weight: 600;
	color: #f59e0b;
	display: flex;
	align-items: center;
}

.dirty-indicator i {
	font-size: 8px;
}

/* Panel Layouts */
.resizable-panel {
	height: 100%;
	overflow-y: auto;
}

.left-panel {
	flex: 0 0 22%;
	min-width: 280px;
	border-right: 1px solid #e2e8f0;
}

.middle-panel {
	flex: 1;
	min-width: 450px;
}

.right-panel {
	flex: 0 0 25%;
	min-width: 320px;
	border-left: 1px solid #e2e8f0;
}

.panel-resizer {
	width: 4px;
	cursor: col-resize;
	background: transparent;
	transition: background 0.2s;
	z-index: 10;
}

.panel-resizer:hover {
	background: #cbd5e1;
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
	.left-panel,
	.right-panel {
		flex: 0 0 25%;
	}
}

@media (max-width: 992px) {
	.left-panel,
	.right-panel {
		display: none !important;
	}
	.middle-panel {
		flex: 1;
		min-width: 0;
	}
}
</style>
