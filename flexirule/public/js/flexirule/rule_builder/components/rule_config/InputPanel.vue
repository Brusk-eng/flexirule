<template>
	<div class="input-panel reference-utility">
		<div class="panel-header">
			<h4>{{ __("Reference & Variables") }}</h4>
			<p class="text-muted small">{{ __("Explore available data and action guide") }}</p>
		</div>

		<div class="panel-sections">
			<!-- Available Variables -->
			<div class="panel-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Available Variables") }}</h5>
					<button class="btn btn-xs btn-link" @click="refreshVariables">
						<i class="fa fa-refresh"></i>
					</button>
				</div>
				<div class="variable-search mb-2">
					<div class="input-group input-group-sm">
						<div class="input-group-prepend">
							<span class="input-group-text"><i class="fa fa-search"></i></span>
						</div>
						<input
							type="text"
							class="form-control"
							v-model="searchQuery"
							:placeholder="__('Search variables...')"
						/>
					</div>
				</div>

				<div class="variable-list v2-scrollbar">
					<div v-if="loading" class="text-center p-3">
						<div class="spinner-border spinner-border-sm text-muted"></div>
					</div>
					<template v-else>
						<div
							v-for="v in filteredVariables"
							:key="v.value"
							class="variable-item"
							:title="v.label"
							draggable="true"
							@dragstart="onDragStart($event, v)"
						>
							<span class="variable-label">{{ v.label }}</span>
							<span class="variable-type">{{ v.type || "Data" }}</span>
						</div>
						<div v-if="filteredVariables.length === 0" class="empty-state">
							{{
								searchQuery
									? __("No matching variables")
									: __("No scope variables available")
							}}
						</div>
					</template>
				</div>
			</div>

			<!-- Divider -->
			<div class="section-divider"></div>

			<!-- Configuration Guide (Integrated from V2PreviewPanel) -->
			<div class="panel-section guide-section">
				<h5 class="section-title">{{ __("Configuration Guide") }}</h5>
				<div v-if="contract" class="guide-content p-3 mt-1">
					<div class="d-flex align-items-center mb-3">
						<div class="guide-icon-small" :style="{ background: contract.color }">
							<i :class="contract.icon"></i>
						</div>
						<h6 class="mb-0 ml-2">{{ node.data?.action_type || node.type }}</h6>
					</div>
					<p class="guide-text-small">{{ contract.description }}</p>

					<div v-if="operationDescription" class="operation-insight mt-3">
						<label class="insight-label">{{ __("Operation Insight") }}</label>
						<p class="insight-text italic">{{ operationDescription }}</p>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "../../store";
import { getContract } from "../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();
const variables = ref([]);
const loading = ref(false);
const searchQuery = ref("");
const operationDescription = ref("");

const contract = computed(() => {
	const type = props.node?.data?.action_type || props.node?.type;
	return type ? getContract(type) : null;
});

const filteredVariables = computed(() => {
	if (!searchQuery.value) return variables.value;
	const q = searchQuery.value.toLowerCase();
	return variables.value.filter(
		(v) => v.label.toLowerCase().includes(q) || v.value.toLowerCase().includes(q)
	);
});

function onDragStart(event, variable) {
	if (event.dataTransfer) {
		const text = `{{ ${variable.value} }}`;
		event.dataTransfer.setData("text/plain", text);
		event.dataTransfer.setData("application/x-flexirule-variable", variable.value);
		event.dataTransfer.effectAllowed = "copy";
	}
}

async function refreshVariables() {
	if (!props.node?.id) return;
	loading.value = true;
	try {
		variables.value = await store.getAvailableVariables(props.node.id);
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
}

async function loadOperationDetails() {
	const processName = props.node?.data?.process_name;
	const opName = props.node?.data?.operation;
	if (processName && opName) {
		try {
			const ops = await store.get_process_operations(processName);
			const op = ops.find((o) => o.func_name === opName);
			operationDescription.value = op?.description || "";
		} catch (e) {
			operationDescription.value = "";
		}
	} else {
		operationDescription.value = "";
	}
}

watch(
	() => [props.node?.data?.process_name, props.node?.data?.operation],
	() => loadOperationDetails(),
	{ immediate: true }
);

watch(
	() => props.node?.id,
	() => refreshVariables(),
	{ immediate: true }
);

onMounted(() => {
	refreshVariables();
});

defineExpose({
	validate: () => ({ valid: true }),
});
</script>

<style scoped>
.input-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: #f8fafc;
}

.panel-header {
	padding: 20px;
	border-bottom: 1px solid var(--border-color);
	background: #fff;
}

.panel-header h4 {
	margin: 0 0 4px 0;
	font-size: 15px;
	font-weight: 600;
}

.panel-sections {
	flex: 1;
	overflow-y: auto;
	padding: 20px;
	display: flex;
	flex-direction: column;
	gap: 24px;
}

.panel-section {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.section-title {
	margin: 0;
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: #64748b;
}

.section-divider {
	height: 1px;
	background: #e2e8f0;
	margin: 4px 0;
}

.variable-list {
	display: flex;
	flex-direction: column;
	gap: 6px;
	max-height: 350px;
	overflow-y: auto;
	padding-right: 4px;
}

.variable-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 12px;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	font-size: 11px;
	cursor: grab;
	transition: all 0.2s;
}

.variable-item:hover {
	border-color: var(--primary);
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	transform: translateX(2px);
}

.variable-label {
	font-weight: 600;
	color: #1e293b;
}

.variable-type {
	font-size: 9px;
	padding: 2px 6px;
	background: #f1f5f9;
	border-radius: 4px;
	color: #64748b;
}

.guide-content {
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 12px;
}

.guide-icon-small {
	width: 24px;
	height: 24px;
	border-radius: 6px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #fff;
	font-size: 12px;
}

.guide-text-small {
	font-size: 12px;
	line-height: 1.5;
	color: #475569;
	margin: 0;
}

.insight-label {
	font-size: 10px;
	font-weight: 700;
	color: var(--primary);
	text-transform: uppercase;
	display: block;
	margin-bottom: 4px;
}

.insight-text {
	font-size: 11px;
	color: #64748b;
	background: #f0f9ff;
	padding: 8px;
	border-radius: 8px;
	border-left: 3px solid var(--primary);
	margin: 0;
}

.v2-scrollbar::-webkit-scrollbar {
	width: 4px;
}
.v2-scrollbar::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 10px;
}

.empty-state {
	padding: 20px;
	text-align: center;
	color: #94a3b8;
	font-size: 11px;
	background: #f8fafc;
	border: 1px dashed #e2e8f0;
	border-radius: 8px;
}
</style>
