<template>
	<div class="input-panel">
		<div class="panel-header">
			<h4>{{ __("Inputs & Sources") }}</h4>
			<p class="text-muted small">{{ __("Select the data sources for this action") }}</p>
		</div>

		<div class="panel-sections">
			<!-- Trigger Source -->
			<div class="panel-section">
				<h5 class="section-title">{{ __("Trigger Source") }}</h5>
				<div class="source-item active">
					<div class="source-icon">
						<i class="fa fa-bolt"></i>
					</div>
					<div class="source-info">
						<span class="source-name">{{ __("Main Document") }}</span>
						<span class="source-meta">{{ node.data?.document_type }}</span>
					</div>
					<div class="source-check">
						<i class="fa fa-check-circle"></i>
					</div>
				</div>
			</div>

			<!-- Input Mapping -->
			<div class="panel-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Input Mapping") }}</h5>
					<button class="btn btn-xs btn-link" @click="addMapping">
						<i class="fa fa-plus"></i> {{ __("Add") }}
					</button>
				</div>
				<div class="mapping-list">
					<div v-if="!mappings.length" class="empty-state">
						{{ __("No input mappings. Param names will be auto-matched if they match context variable names.") }}
					</div>
					<div v-for="(m, idx) in mappings" :key="idx" class="mapping-row">
						<div class="mapping-inputs">
							<AutocompleteControl
								:df="{ fieldtype: 'Autocomplete', label: '' }"
								:modelValue="m.source"
								:get_options="getVariableOptions"
								:placeholder="__('From Context')"
								@update:modelValue="m.source = $event; saveMappings();"
							/>
							<i class="fa fa-arrow-right text-muted mx-1"></i>
							<input 
								type="text" 
								class="form-control input-xs" 
								v-model="m.target" 
								:placeholder="__('To Param')"
								@change="saveMappings"
							/>
						</div>
						<button class="btn btn-xs btn-link text-danger" @click="removeMapping(idx)">
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>

			<!-- Available Variables -->
			<div class="panel-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Available Variables") }}</h5>
					<button class="btn btn-xs btn-link" @click="refreshVariables">
						<i class="fa fa-refresh"></i>
					</button>
				</div>
				
				<div class="variable-list">
					<div v-if="loading" class="text-center p-3">
						<div class="spinner-border spinner-border-sm text-muted text-center"></div>
					</div>
					<template v-else>
						<div 
							v-for="v in variables" 
							:key="v.value" 
							class="variable-item"
							:title="v.label"
							draggable="true"
							@dragstart="onDragStart($event, v)"
						>
							<span class="variable-label">{{ v.label }}</span>
							<span class="variable-type">{{ v.type || 'Data' }}</span>
						</div>
						<div v-if="variables.length === 0" class="empty-state">
							{{ __("No scope variables available") }}
						</div>
					</template>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";
import { useStore } from "../../store";
import AutocompleteControl from "../../controls/AutocompleteControl.vue";

const props = defineProps({
	node: Object,
});

const store = useStore();
const variables = ref([]);
const loading = ref(false);
const mappings = ref([]);

function onDragStart(event, variable) {
    if (event.dataTransfer) {
        // Default to Jinja style for templates as that's the primary use case
        const text = `{{ ${variable.value} }}`;
        event.dataTransfer.setData('text/plain', text);
        event.dataTransfer.effectAllowed = 'copy';
    }
}

// Parse mappings from JSON
watch(() => props.node.data?.input_mapping, (val) => {
	if (val) {
		try {
			const obj = typeof val === 'string' ? JSON.parse(val) : val;
			mappings.value = Object.entries(obj).map(([source, target]) => ({ source, target }));
		} catch (e) {
			mappings.value = [];
		}
	} else {
		mappings.value = [];
	}
}, { immediate: true });

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

function updateField(fieldname, value) {
	if (props.node.data) {
		props.node.data[fieldname] = value;
		store.mark_dirty();
	}
}

function addMapping() {
	mappings.value.push({ source: "", target: "" });
}

function removeMapping(idx) {
	mappings.value.splice(idx, 1);
	saveMappings();
}

function saveMappings() {
	const obj = {};
	mappings.value.forEach(m => {
		if (m.source && m.target) {
			obj[m.source] = m.target;
		}
	});
	updateField('input_mapping', obj);
}

function getVariableOptions() {
	return variables.value.map(v => ({ label: v.label, value: v.value }));
}

watch(() => props.node?.id, () => {
	refreshVariables();
}, { immediate: true });

onMounted(() => {
	refreshVariables();
});

function validate() {
	const errors = [];
	mappings.value.forEach((m, idx) => {
		if ((m.source && !m.target) || (!m.source && m.target)) {
			errors.push(__("Input Mapping #{0} is incomplete", [idx + 1]));
		}
	});
	
	if (errors.length) {
		return { valid: false, errors };
	}
	return { valid: true };
}

defineExpose({ validate });
</script>

<style scoped>
.input-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
}

.panel-header {
	padding: 20px;
	border-bottom: 1px solid var(--border-color);
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

.section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.section-title {
	margin: 0;
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: var(--text-muted);
}

.source-item {
	display: flex;
	align-items: center;
	padding: 12px;
	border: 1px solid var(--border-color);
	border-radius: 8px;
	background: #fff;
	gap: 12px;
}

.source-item.active {
	border-color: var(--primary);
	background: var(--blue-50, #f0f7ff);
}

.source-icon {
	width: 32px;
	height: 32px;
	border-radius: 6px;
	background: var(--primary);
	color: #fff;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
}

.source-info {
	flex: 1;
	display: flex;
	flex-direction: column;
}

.source-name {
	font-size: 13px;
	font-weight: 600;
}

.source-meta {
	font-size: 11px;
	color: var(--text-muted);
}

.source-check {
	color: var(--primary);
	font-size: 16px;
}

.variable-list {
	display: flex;
	flex-direction: column;
	gap: 6px;
	max-height: 200px;
	overflow-y: auto;
}

.variable-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 6px 10px;
	background: #fcfcfc;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	font-size: 11px;
	cursor: grab;
}

.variable-item:active {
	cursor: grabbing;
}

.variable-label {
	font-weight: 500;
	color: var(--text-color);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	flex: 1;
}

.variable-type {
	font-size: 9px;
	padding: 1px 4px;
	background: var(--gray-100);
	border-radius: 3px;
	color: var(--text-muted);
	margin-left: 8px;
}

.mapping-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.mapping-row {
	display: flex;
	align-items: center;
	gap: 8px;
}

.mapping-inputs {
	flex: 1;
	display: flex;
	align-items: center;
	padding: 4px 8px;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	background: #fff;
}

.mapping-inputs :deep(.autocomplete-control),
.mapping-inputs input {
	border: none;
	background: transparent;
	font-size: 12px;
	padding: 0;
	height: 24px;
}

.mapping-inputs :deep(.autocomplete-control) {
	flex: 1;
}

.empty-state {
	padding: 16px;
	text-align: center;
	color: var(--text-muted);
	font-size: 11px;
	background: var(--gray-50);
	border: 1px dashed var(--border-color);
	border-radius: 8px;
}

.input-xs {
	height: 24px !important;
	padding: 0 4px !important;
	font-size: 11px !important;
}
</style>
