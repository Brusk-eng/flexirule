<template>
	<Teleport to="body">
		<transition name="fade">
			<div v-if="modelValue" class="config-modal-overlay" @click.self="cancel">
				<div
					class="config-modal-container"
					:class="{
						'show-context-sidebar': showContextSidebar,
						'show-guide-sidebar': showGuideSidebar,
						'show-settings-bar': showSettingsBar,
					}"
				>
					<header class="config-modal-header">
						<div class="header-left">
							<div
								class="header-icon"
								v-if="draftNode"
								:style="{ background: contract?.css?.color + '20' }"
							>
								<i
									:class="
										contract?.css?.icon ||
										getIcon(draftNode.data?.action_type || draftNode.type)
									"
									:style="{ color: contract?.css?.color }"
								></i>
							</div>
							<div class="header-title-container">
								<div class="d-flex align-items-center gap-2">
									<h3 class="modal-title">{{ title }}</h3>
									<i
										v-if="store.is_read_only"
										class="fa fa-lock text-muted"
										:title="__('Read Only')"
									></i>
								</div>
								<div class="modal-breadcrumb">
									<span
										class="type-badge"
										:style="{ color: contract?.css?.color }"
									>
										{{ draftNode?.data?.action_id }}
									</span>
									<i
										class="fa fa-chevron-right small mx-1 text-muted opacity-50"
									></i>
									<span class="text-muted">{{
										draftNode?.data?.action_type
									}}</span>
								</div>
							</div>
						</div>

						<!-- Efficient Navigation -->
						<div class="header-center">
							<div class="modal-navigation-compact">
								<button
									class="nav-btn-sm"
									@click="store.prev_config_node()"
									:disabled="currentNodeIndex <= 0"
								>
									<i class="fa fa-chevron-left"></i>
								</button>
								<div class="nav-counter">
									<span class="current">{{ currentNodeIndex + 1 }}</span>
									<span class="separator">/</span>
									<span class="total">{{ totalNodes }}</span>
								</div>
								<button
									class="nav-btn-sm"
									@click="store.next_config_node()"
									:disabled="currentNodeIndex >= totalNodes - 1"
								>
									<i class="fa fa-chevron-right"></i>
								</button>
							</div>
						</div>

						<div class="header-right">
							<div class="header-tools">
								<button
									class="tool-btn"
									:class="{ active: showContextSidebar }"
									@click="showContextSidebar = !showContextSidebar"
								>
									<i class="fa fa-database"></i>
									<span>{{ __("Variables") }}</span>
								</button>
								<button
									class="tool-btn"
									:class="{ active: showSettingsBar }"
									@click="showSettingsBar = !showSettingsBar"
								>
									<i class="fa fa-cog"></i>
									<span>{{ __("Settings") }}</span>
								</button>
							</div>
							<div class="divider-v mx-3"></div>
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

							<!-- Unified Action Setup -->
							<div v-else-if="draftNode" class="panels-container-modern">
								<!-- Context Variable Sidebar (Left) -->
								<aside class="sidebar-variables" v-if="showContextSidebar">
									<InputPanel
										:node="draftNode"
										:readOnly="store.is_read_only"
										mode="variables"
									/>
								</aside>

								<!-- Main Config Area -->
								<div class="config-main-area">
									<div class="config-scroll-container">
										<div class="config-content-wrapper">
											<!-- Top Settings Bar (Integrated) -->
											<div
												class="integrated-settings-bar"
												v-if="showSettingsBar"
											>
												<ActionSettings
													:node="draftNode"
													:readOnly="store.is_read_only"
													@update:field="on_update_action_field"
												/>
											</div>

											<!-- Split View: Setup (Left) & Config (Right/Center) -->
											<div class="action-core-layout">
												<div class="core-setup-panel">
													<InputPanel
														:node="draftNode"
														:readOnly="store.is_read_only"
														:ref="panelRefs.input"
														mode="config"
													/>
												</div>
												<div class="core-config-panel">
													<ConfigurationPanel
														:node="draftNode"
														:readOnly="store.is_read_only"
														:ref="panelRefs.config"
													/>
												</div>
											</div>
										</div>
									</div>

									<!-- Right Side Utility Panel (Mutation & Results) -->
									<aside class="sidebar-mutation">
										<OutputPanel
											:node="draftNode"
											:readOnly="store.is_read_only"
											:ref="panelRefs.output"
										/>
									</aside>
								</div>
							</div>

							<!-- Guide Sidebar (Right Sliding) -->
							<aside class="sidebar guide-sidebar" v-if="showGuideSidebar">
								<div class="guide-panel p-4">
									<h5>{{ __("Action Guide") }}</h5>
									<div class="guide-content mt-3" v-if="contract">
										<p>{{ contract.description }}</p>
										<!-- Operation specific guide could go here -->
									</div>
								</div>
							</aside>
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
import { ref, computed } from "vue";
import ResizablePanel from "./ResizablePanel.vue";
import InputPanel from "./InputPanel.vue";
import ConfigurationPanel from "./ConfigurationPanel.vue";
import OutputPanel from "./OutputPanel.vue";
import ActionSettings from "./ActionSettings.vue";
import ConditionStep from "./types/ConditionStep.vue";
import StartNodeProperties from "../StartNodeProperties.vue";
import { useStore } from "../../store";
import { useRuleConfig } from "../../composables/useRuleConfig";
import { getContract } from "../../../core/contracts.js";

const props = defineProps({
	modelValue: Boolean,
	node: Object,
});

const emit = defineEmits(["update:modelValue", "save"]);
const store = useStore();

const { draftNode, panelRefs, save, cancel } = useRuleConfig(props, emit);

// -- Sidebar / Slide States --
const showContextSidebar = ref(false);
const showGuideSidebar = ref(false);
const showSettingsBar = ref(false);

const contract = computed(() => {
	const type = draftNode.value?.data?.action_type || draftNode.value?.type;
	return type ? getContract(type) : null;
});

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

function on_update_action_field({ fieldname, value, scope }) {
	if (!draftNode.value?.data) return;
	if (fieldname && scope === "config") {
		let baseConfig = {};
		if (draftNode.value.data.config && typeof draftNode.value.data.config === "object") {
			baseConfig = draftNode.value.data.config;
		} else if (typeof draftNode.value.data.config === "string") {
			try {
				baseConfig = JSON.parse(draftNode.value.data.config) || {};
			} catch (e) {
				baseConfig = {};
			}
		}
		const nextConfig = {
			...baseConfig,
		};
		if (
			value === null ||
			value === undefined ||
			value === "" ||
			(typeof value === "object" && !Array.isArray(value) && !Object.keys(value).length)
		) {
			delete nextConfig[fieldname];
		} else {
			nextConfig[fieldname] = value;
		}
		draftNode.value.data.config = nextConfig;
		store.mark_dirty();
		return;
	}
	draftNode.value.data[fieldname] = value;
	store.mark_dirty();
}

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
		"document action": "fa fa-plus-circle",
		"set value": "fa fa-edit",
		notify: "fa fa-bell",
	};
	return icons[type.toLowerCase()] || "fa fa-circle";
}
</script>

<style scoped>
.config-modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background: rgba(15, 23, 42, 0.4);
	backdrop-filter: blur(12px);
	z-index: 1040;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 24px;
}

.config-modal-container {
	background: #fff;
	width: 100%;
	height: 100%;
	max-width: 1800px;
	border-radius: 20px;
	box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.3);
	display: flex;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid #e2e8f0;
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.config-modal-header {
	height: 80px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 32px;
	border-bottom: 1px solid #e2e8f0;
	background: #fff;
}

.header-left {
	display: flex;
	align-items: center;
	gap: 16px;
	min-width: 300px;
}

.header-icon {
	width: 48px;
	height: 48px;
	border-radius: 12px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 20px;
	border: 1px solid rgba(0, 0, 0, 0.05);
}

.header-title-container {
	display: flex;
	flex-direction: column;
}

.header-left h3 {
	margin: 0;
	font-size: 18px;
	font-weight: 800;
	color: #0f172a;
	letter-spacing: -0.02em;
}

.type-badge {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.1em;
	opacity: 0.8;
}

.header-center {
	flex: 1;
	display: flex;
	justify-content: center;
}

.header-actions {
	display: flex;
	align-items: center;
	gap: 24px;
}

/* Toggle Buttons */
.toggle-group {
	display: flex;
	background: #f1f5f9;
	padding: 4px;
	border-radius: 12px;
	border: 1px solid #e2e8f0;
}

.toggle-btn {
	padding: 8px 16px;
	border-radius: 8px;
	border: none;
	background: transparent;
	color: #64748b;
	font-size: 13px;
	font-weight: 600;
	display: flex;
	align-items: center;
	gap: 8px;
	cursor: pointer;
	transition: all 0.2s;
}

.toggle-btn i {
	font-size: 14px;
}

.toggle-btn:hover {
	background: rgba(255, 255, 255, 0.5);
	color: #1e293b;
}

.toggle-btn.active {
	background: #fff;
	color: var(--primary);
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.config-modal-header {
	height: 64px;
	padding: 0 24px;
	border-bottom: 1px solid #e2e8f0;
	background: #fff;
	display: flex;
	align-items: center;
	justify-content: space-between;
	flex-shrink: 0;
}

.header-left {
	display: flex;
	align-items: center;
	gap: 16px;
	min-width: 250px;
}

.header-icon {
	width: 40px;
	height: 40px;
	border-radius: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 18px;
}

.modal-title {
	margin: 0;
	font-size: 16px;
	font-weight: 700;
	color: #1e293b;
}

.modal-breadcrumb {
	display: flex;
	align-items: center;
	font-size: 11px;
	margin-top: 2px;
}

.modal-navigation-compact {
	display: flex;
	align-items: center;
	background: #f1f5f9;
	padding: 4px;
	border-radius: 10px;
	gap: 4px;
}

.nav-btn-sm {
	width: 28px;
	height: 28px;
	border-radius: 6px;
	border: none;
	background: transparent;
	color: #64748b;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: all 0.2s;
}

.nav-btn-sm:hover:not(:disabled) {
	background: #fff;
	color: var(--primary);
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.nav-btn-sm:disabled {
	opacity: 0.3;
	cursor: default;
}

.nav-counter {
	display: flex;
	align-items: center;
	gap: 4px;
	padding: 0 8px;
	font-size: 12px;
	font-weight: 700;
	color: #475569;
}

.nav-counter .separator {
	opacity: 0.4;
}

.header-tools {
	display: flex;
	gap: 8px;
}

.tool-btn {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 12px;
	border-radius: 8px;
	border: 1px solid transparent;
	background: transparent;
	color: #64748b;
	font-size: 12px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.2s;
}

.tool-btn:hover {
	background: #f8fafc;
	color: #1e293b;
}

.tool-btn.active {
	background: #eff6ff;
	color: var(--primary);
	border-color: #bfdbfe;
}

.divider-v {
	width: 1px;
	height: 24px;
	background: #e2e8f0;
}

.btn-close-modal {
	width: 32px;
	height: 32px;
	border-radius: 8px;
	border: none;
	background: #f1f5f9;
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
	display: flex;
	background: #f8fafc;
}

.panels-container-modern {
	display: flex;
	flex: 1;
	overflow: hidden;
}

.sidebar-variables {
	width: 280px;
	background: #fff;
	border-right: 1px solid #e2e8f0;
	flex-shrink: 0;
}

.config-main-area {
	flex: 1;
	display: flex;
	overflow: hidden;
}

.config-scroll-container {
	flex: 1;
	overflow-y: auto;
	padding: 24px;
	display: flex;
	flex-direction: column;
}

.config-content-wrapper {
	max-width: 1200px;
	margin: 0 auto;
	width: 100%;
	display: flex;
	flex-direction: column;
	gap: 24px;
}

.integrated-settings-bar {
	background: #fff;
	border-radius: 12px;
	border: 1px solid #e2e8f0;
	padding: 16px 24px;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.action-core-layout {
	display: grid;
	grid-template-columns: 350px 1fr;
	gap: 24px;
	align-items: start;
}

.core-setup-panel,
.core-config-panel {
	background: #fff;
	border-radius: 12px;
	border: 1px solid #e2e8f0;
	overflow: hidden;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.sidebar-mutation {
	width: 350px;
	background: #fff;
	border-left: 1px solid #e2e8f0;
	flex-shrink: 0;
	overflow-y: auto;
}

.config-modal-footer {
	height: 72px;
	border-top: 1px solid #e2e8f0;
	background: #fff;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 32px;
	flex-shrink: 0;
}

.dirty-indicator {
	font-size: 11px;
	font-weight: 700;
	color: #d97706;
	display: flex;
	align-items: center;
	gap: 6px;
	background: #fffbeb;
	padding: 6px 12px;
	border-radius: 8px;
	border: 1px solid #fef3c7;
}

.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>
