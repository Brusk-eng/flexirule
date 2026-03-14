<template>
	<div class="output-panel data-io-center">
		<div class="panel-header">
			<h4>{{ __("Data Interaction") }}</h4>
			<p class="text-muted small">{{ __("Manage inputs, results, and assignments") }}</p>
		</div>

		<div class="panel-sections">
			<!-- Input Mapping (Moved from InputPanel) -->
			<div class="panel-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Input Mappings") }}</h5>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addInputMapping">
						<i class="fa fa-plus"></i> {{ __("Add") }}
					</button>
				</div>
				<p class="text-muted extra-small mb-2">
					{{ __("Map context variables to action parameters.") }}
				</p>
				<div class="mapping-list">
					<div v-if="!inputMappings.length" class="empty-state">
						{{
							__("No input mappings. Parameters will be auto-matched if names match.")
						}}
					</div>
					<div v-for="(m, idx) in inputMappings" :key="'in-' + idx" class="mapping-row">
						<div class="mapping-inputs">
							<AutocompleteControl
								:df="{ fieldtype: 'Autocomplete', label: '', read_only: readOnly }"
								:modelValue="m.source"
								:get_options="getVariableOptions"
								:placeholder="__('From Context')"
								:read_only="readOnly"
								@update:modelValue="
									m.source = $event;
									saveInputMappings();
								"
							/>
							<i class="fa fa-arrow-right text-muted mx-1"></i>
							<input
								type="text"
								class="form-control input-xs"
								v-model="m.target"
								:placeholder="__('To Param')"
								:disabled="readOnly"
								@change="saveInputMappings"
							/>
						</div>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link text-danger"
							@click="removeInputMapping(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>

			<div class="section-divider"></div>

			<!-- Detected Return Keys (Schema Discovery) -->
			<div class="panel-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Detected Return Keys") }}</h5>
				</div>
				<p class="text-muted extra-small mb-2">
					{{ __("Keys detected via 'Test Query'. Run test to update.") }}
				</p>

				<div class="detected-keys-list mb-1">
					<div v-if="!detectedKeys.length" class="empty-state">
						{{ __("No keys detected yet.") }}
					</div>
					<div v-else class="keys-grid">
						<div
							v-for="k in detectedKeys"
							:key="k.fieldname || k.key"
							class="key-tag"
							:title="`${k.fieldname || k.key} (${k.fieldtype || 'Data'})`"
						>
							<i class="fa fa-info-circle mr-1 opacity-70"></i>
							{{ k.label || k.fieldname || k.key }}
						</div>
					</div>
				</div>
			</div>

			<div class="section-divider"></div>

			<!-- Result Storage -->
			<div class="panel-section">
				<h5 class="section-title">{{ __("Execution Result") }}</h5>
				<div class="form-group mt-2">
					<ControlFactory
						:df="{
							fieldname: 'return_variable',
							fieldtype: 'Data',
							label: __('Result Variable Name'),
							description: __('Variable to store the full action output'),
							read_only: readOnly,
						}"
						:modelValue="node.data?.return_variable"
						:read_only="readOnly"
						@update:modelValue="updateField('return_variable', $event)"
					/>
				</div>
			</div>

			<!-- Output Assignments -->
			<div class="panel-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Variable Assignments") }}</h5>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addOutputMapping">
						<i class="fa fa-plus"></i> {{ __("Add") }}
					</button>
				</div>
				<p class="text-muted extra-small mb-2">
					{{ __("Assign specific result keys to context variables.") }}
				</p>

				<div class="mapping-list">
					<div v-if="!outputMappings.length" class="empty-state">
						{{ __("No variables assigned specifically.") }}
					</div>
					<div v-for="(m, idx) in outputMappings" :key="'out-' + idx" class="mapping-row">
						<div class="mapping-inputs">
							<input
								type="text"
								class="form-control input-xs"
								v-model="m.source"
								:placeholder="__('Result Key')"
								:disabled="readOnly"
								@change="saveOutputMappings"
							/>
							<i class="fa fa-arrow-right text-muted mx-1"></i>
							<AutocompleteControl
								:df="{ fieldtype: 'Autocomplete', label: '', read_only: readOnly }"
								:modelValue="m.target"
								:get_options="getVariableOptions"
								:placeholder="__('Context Variable')"
								:read_only="readOnly"
								@update:modelValue="
									m.target = $event;
									saveOutputMappings();
								"
							/>
						</div>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link text-danger"
							@click="removeOutputMapping(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from "vue";
import { useStore } from "../../store";
import ControlFactory from "../../controls/ControlFactory.vue";
import AutocompleteControl from "../../controls/AutocompleteControl.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();

const inputMappings = ref([]);
const outputMappings = ref([]);
const availableVariables = ref([]);

const detectedKeys = computed(() => {
	const schema = props.node?.data?.resolved_output_schema;
	if (Array.isArray(schema)) return schema;
	try {
		return typeof schema === "string" ? JSON.parse(schema) : [];
	} catch (e) {
		return [];
	}
});

// -- Input Mappings Logic --
watch(
	() => props.node.data?.input_mapping,
	(val) => {
		if (val) {
			try {
				const obj = typeof val === "string" ? JSON.parse(val) : val;
				inputMappings.value = Object.entries(obj).map(([source, target]) => ({
					source,
					target,
				}));
			} catch (e) {
				inputMappings.value = [];
			}
		} else {
			inputMappings.value = [];
		}
	},
	{ immediate: true }
);

function addInputMapping() {
	inputMappings.value.push({ source: "", target: "" });
}

function removeInputMapping(idx) {
	inputMappings.value.splice(idx, 1);
	saveInputMappings();
}

function saveInputMappings() {
	const obj = {};
	inputMappings.value.forEach((m) => {
		if (m.source && m.target) obj[m.source] = m.target;
	});
	updateField("input_mapping", obj);
}

// -- Output Mappings Logic --
watch(
	() => props.node.data?.output_mapping,
	(val) => {
		if (val) {
			try {
				const obj = typeof val === "string" ? JSON.parse(val) : val;
				outputMappings.value = Object.entries(obj).map(([source, target]) => ({
					source,
					target,
				}));
			} catch (e) {
				outputMappings.value = [];
			}
		} else {
			outputMappings.value = [];
		}
	},
	{ immediate: true }
);

function addOutputMapping() {
	outputMappings.value.push({ source: "", target: "" });
}

function removeOutputMapping(idx) {
	outputMappings.value.splice(idx, 1);
	saveOutputMappings();
}

function saveOutputMappings() {
	const obj = {};
	outputMappings.value.forEach((m) => {
		if (m.source && m.target) obj[m.source] = m.target;
	});
	updateField("output_mapping", obj);
}

// -- Shared Logic --
function updateField(fieldname, value) {
	if (props.node.data) {
		props.node.data[fieldname] = value;
		store.mark_dirty();
	}
}

async function refreshVariables() {
	if (!props.node?.id) return;
	try {
		availableVariables.value = await store.getAvailableVariables(props.node.id);
	} catch (e) {
		availableVariables.value = [];
	}
}

function getVariableOptions() {
	return availableVariables.value.map((v) => ({ label: v.label, value: v.value }));
}

onMounted(() => {
	refreshVariables();
});

function validate() {
	const errors = [];
	inputMappings.value.forEach((m, idx) => {
		if ((m.source && !m.target) || (!m.source && m.target)) {
			errors.push(__("Input Mapping #{0} is incomplete", [idx + 1]));
		}
	});
	outputMappings.value.forEach((m, idx) => {
		if ((m.source && !m.target) || (!m.source && m.target)) {
			errors.push(__("Variable Assignment #{0} is incomplete", [idx + 1]));
		}
	});
	return errors.length ? { valid: false, errors } : { valid: true };
}

defineExpose({ validate });
</script>

<style scoped>
.output-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: #fff;
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
}

.section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 8px;
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
	background: #f1f5f9;
	margin: 0;
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
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	background: #f8fafc;
	transition: border-color 0.2s;
}

.mapping-inputs:focus-within {
	border-color: var(--primary);
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
	color: #94a3b8;
	font-size: 11px;
	background: #f8fafc;
	border: 1px dashed #e2e8f0;
	border-radius: 8px;
}

.extra-small {
	font-size: 10px;
}

.input-xs {
	height: 24px !important;
	padding: 0 4px !important;
	font-size: 11px !important;
}

.keys-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
}

.key-tag {
	font-size: 10px;
	font-weight: 600;
	padding: 2px 8px;
	background: #f1f5f9;
	color: #475569;
	border-radius: 4px;
	border: 1px solid #e2e8f0;
}

:deep(.control-factory) {
	margin-bottom: 0;
}
</style>
