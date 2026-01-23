<template>
	<div class="output-panel">
		<div class="panel-header">
			<h4>{{ __("Outputs & Results") }}</h4>
			<p class="text-muted small">{{ __("Define what this action returns") }}</p>
		</div>

		<div class="panel-sections">
			<!-- Return Variable -->
			<div class="panel-section">
				<h5 class="section-title">{{ __("Execution Result") }}</h5>
				<div class="form-group">
					<ControlFactory
						:df="{
							fieldname: 'return_variable',
							fieldtype: 'Data',
							label: __('Result Variable Name'),
							description: __('Name of the variable to store the action output'),
							read_only: readOnly
						}"
						:modelValue="node.data?.return_variable"
						:read_only="readOnly"
						@update:modelValue="updateField('return_variable', $event)"
					/>
				</div>
			</div>

			<!-- Output Mapping (Table-like Editor for JSON) -->
			<div class="panel-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Variable Assignments") }}</h5>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addMapping">
						<i class="fa fa-plus"></i> {{ __("Add") }}
					</button>
				</div>
				
				<div class="assignment-list">
					<div v-if="!mappings.length" class="empty-state">
						{{ __("No variables assigned. Use assignments to map specific response keys to context.") }}
					</div>
					<div v-for="(m, idx) in mappings" :key="idx" class="mapping-row">
						<div class="mapping-inputs">
							<input 
								type="text" 
								class="form-control input-xs" 
								v-model="m.source" 
								:placeholder="__('Result Key')"
								:disabled="readOnly"
								@change="saveMappings"
							/>
							<i class="fa fa-arrow-right text-muted mx-1"></i>
							<AutocompleteControl
								:df="{ fieldtype: 'Autocomplete', label: '', read_only: readOnly }"
								:modelValue="m.target"
								:get_options="getVariableOptions"
								:placeholder="__('Context Variable')"
								:read_only="readOnly"
								@update:modelValue="m.target = $event; saveMappings();"
							/>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link text-danger" @click="removeMapping(idx)">
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>

			<!-- Preview -->
			<div v-if="operation_metadata?.output_schema" class="panel-section">
				<h5 class="section-title">{{ __("Output Schema") }}</h5>
				<div class="preview-box">
					<pre class="json-preview"><code>{{ operation_metadata.output_schema }}</code></pre>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useStore } from "../../store";
import ControlFactory from "../../controls/ControlFactory.vue";
import AutocompleteControl from "../../controls/AutocompleteControl.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();

// Mappings state
const mappings = ref([]);

// Parse mappings from JSON
watch(() => props.node.data?.output_mapping, (val) => {
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
	updateField('output_mapping', obj);
}

function getVariableOptions() {
	// Standard variables plus any produced by prior nodes
	return [
		{ label: 'doc (Main Document)', value: 'doc' },
		...store.doc_fields.map(f => ({ label: `doc.${f.fieldname}`, value: `doc.${f.fieldname}` }))
	];
}

const operation_metadata = computed(() => {
	if (!props.node.data?.process_name || !props.node.data?.operation) return null;
	const proc = store.processes.find(p => p.name === props.node.data.process_name);
	return proc?.operations?.find(op => op.func_name === props.node.data.operation);
});

function validate() {
	const errors = [];
	mappings.value.forEach((m, idx) => {
		if ((m.source && !m.target) || (!m.source && m.target)) {
			errors.push(__("Output Mapping #{0} is incomplete", [idx + 1]));
		}
	});

	// Optional: Check return variable validity? 
	// For now, let's keep it loose as Frappe handles variable names mostly, 
	// unless we want to enforce python identifier rules.
	
	if (errors.length) {
		return { valid: false, errors };
	}
	return { valid: true };
}

defineExpose({ validate });
</script>

<style scoped>
.output-panel {
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

.assignment-list {
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

.preview-box {
	background: #1e1e1e;
	border-radius: 8px;
	padding: 12px;
	overflow: hidden;
}

.json-preview {
	margin: 0;
	font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
	font-size: 11px;
	line-height: 1.5;
	color: #dcdcdc;
	white-space: pre-wrap;
}

.input-xs {
	height: 24px !important;
	padding: 0 4px !important;
	font-size: 11px !important;
}
</style>
