<template>
	<div class="create-docs-config">
		<!-- Flow Header -->
		<div class="flow-steps mb-4">
			<div :class="['flow-step', { active: step === 1 }]" @click="step = 1">
				<span class="step-num">1</span>
				<span class="step-txt">{{ __("Reference") }}</span>
			</div>
			<div class="flow-arrow"><i class="fa fa-chevron-right"></i></div>
			<div :class="['flow-step', { active: step === 2, disabled: !node.data.reference_doctype }]" @click="node.data.reference_doctype && (step = 2)">
				<span class="step-num">2</span>
				<span class="step-txt">{{ __("Mappings") }}</span>
			</div>
			<div class="flow-arrow"><i class="fa fa-chevron-right"></i></div>
			<div :class="['flow-step', { active: step === 3 }]" @click="step = 3">
				<span class="step-num">3</span>
				<span class="step-txt">{{ __("Mutation") }}</span>
			</div>
		</div>

		<!-- Step 1: Base Config -->
		<div v-if="step === 1" class="step-content">
			<div class="row">
				<div class="col-7">
					<ControlFactory
						:df="{
							fieldname: 'reference_doctype',
							label: __('Target DocType'),
							fieldtype: 'Link',
							options: 'DocType',
							reqd: 1,
							description: __('Which DocType do you want to create or update?')
						}"
						:modelValue="node.data.reference_doctype"
						@update:modelValue="updateField('reference_doctype', $event)"
					/>
				</div>
				<div class="col-5">
					<ControlFactory
						:df="{
							fieldname: 'operation',
							label: __('Mode'),
							fieldtype: 'Select',
							options: 'Create New\nUpdate Existing',
							reqd: 1
						}"
						:modelValue="node.data.operation"
						@update:modelValue="updateField('operation', $event)"
					/>
				</div>
			</div>
			
			<div class="mt-4 p-4 bg-light rounded text-center" v-if="!node.data.reference_doctype">
				<i class="fa fa-info-circle text-primary fa-2x mb-2"></i>
				<p>{{ __("Please select a Target DocType to proceed to mapping.") }}</p>
			</div>
			<div class="mt-4 d-flex justify-content-end" v-else>
				<button class="btn btn-primary btn-sm" @click="step = 2">
					{{ __("Continue to Mappings") }} <i class="fa fa-arrow-right ml-1"></i>
				</button>
			</div>
		</div>

		<!-- Step 2: Field Mappings -->
		<div v-if="step === 2" class="step-content">
			<div class="mapping-toolbar mb-3 d-flex justify-content-between align-items-center">
				<div class="mapping-info">
					<strong>{{ __("Target:") }}</strong> {{ node.data.reference_doctype }}
				</div>
				<button 
					class="btn btn-xs btn-outline-primary"
					@click="addMappingRow"
					v-if="!readOnly"
				>
					<i class="fa fa-plus"></i> {{ __("Add Field Mapping") }}
				</button>
			</div>

			<div class="mapping-table-wrapper">
				<table class="table table-sm table-mapping">
					<thead>
						<tr>
							<th width="40%">{{ __("Target Field") }}</th>
							<th width="50%">{{ __("Source (Variable or Template)") }}</th>
							<th v-if="!readOnly" width="10%"></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(m, idx) in mappings" :key="idx">
							<td>
								<ControlFactory
									:df="{ fieldname: 'tf', fieldtype: 'Autocomplete' }"
									:modelValue="m.target"
									:get_options="getTargetFields"
									@update:modelValue="updateMappingRow(idx, 'target', $event)"
									hideLabel
								/>
							</td>
							<td>
								<div class="source-input-group">
									<input 
										type="text" 
										v-model="m.source" 
										class="form-control form-control-sm"
										:placeholder="__('e.g. {{ doc.name }} or vars.x')"
										@input="syncMapping"
										:disabled="readOnly"
									/>
									<div class="source-hint" v-if="m.source && m.source.includes('{{')">
										<i class="fa fa-magic"></i> {{ __("Jinja Template") }}
									</div>
								</div>
							</td>
							<td v-if="!readOnly" class="text-right">
								<button class="btn btn-xs btn-link text-danger" @click="removeMappingRow(idx)">
									<i class="fa fa-trash"></i>
								</button>
							</td>
						</tr>
						<tr v-if="!mappings.length">
							<td colspan="3" class="text-center p-4 text-muted">
								{{ __("No fields mapped. Node will fail if mandatory fields are missing.") }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>

		<!-- Step 3: Post-Execution -->
		<div v-if="step === 3" class="step-content">
			<div class="section-container border rounded p-4 bg-white">
				<div class="row align-items-center">
					<div class="col-8">
						<h5 class="mb-1">{{ __("Mutation & Persistence") }}</h5>
						<p class="text-muted small">
							{{ __("Control how the created/updated document interacts with your current context.") }}
						</p>
					</div>
					<div class="col-4 text-right">
						<i class="fa fa-database fa-3x text-light"></i>
					</div>
				</div>
				
				<hr />

				<div class="row mt-3">
					<div class="col-6">
						<ControlFactory
							:df="{
								fieldname: 'mutation_mode',
								label: __('After Save Action'),
								fieldtype: 'Select',
								options: 'None\nSet Doc Field\nSet Context Variable',
								description: __('What to do with the result?')
							}"
							:modelValue="node.data.mutation_mode"
							@update:modelValue="updateField('mutation_mode', $event)"
						/>
					</div>
					<div class="col-6" v-if="node.data.mutation_mode && node.data.mutation_mode !== 'None'">
						<ControlFactory
							:df="{
								fieldname: 'return_variable',
								label: __('Variable Name'),
								fieldtype: 'Data',
								reqd: 1,
								description: __('Name of the field/key to store the document reference.')
							}"
							:modelValue="node.data.return_variable"
							@update:modelValue="updateField('return_variable', $event)"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from "vue";
import { useStore } from "../../../store";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();
const step = ref(1);
const mappings = reactive([]);

function parseConfig() {
	let config = {};
	try {
		config = JSON.parse(props.node.data.config || "{}");
	} catch (e) { config = {}; }
	
	const map = config.mapping || {};
	mappings.splice(0);
	Object.entries(map).forEach(([target, source]) => {
		mappings.push({ target, source });
	});
}

function syncMapping() {
	if (props.readOnly) return;
	let config = {};
	try {
		config = JSON.parse(props.node.data.config || "{}");
	} catch (e) { config = {}; }

	const mapObj = {};
	mappings.forEach(m => {
		if (m.target) mapObj[m.target] = m.source;
	});
	
	config.mapping = mapObj;
	props.node.data.config = JSON.stringify(config);
	store.mark_dirty();
}

function updateField(f, v) {
	if (props.readOnly) return;
	props.node.data[f] = v;
	store.mark_dirty();
}

function addMappingRow() {
	mappings.push({ target: "", source: "" });
}

function removeMappingRow(idx) {
	mappings.splice(idx, 1);
	syncMapping();
}

function updateMappingRow(idx, key, val) {
	mappings[idx][key] = val;
	syncMapping();
}

async function getTargetFields() {
	if (!props.node.data.reference_doctype) return [];
	await frappe.model.with_doctype(props.node.data.reference_doctype);
	const meta = frappe.get_meta(props.node.data.reference_doctype);
	return meta?.fields?.map(f => ({ value: f.fieldname, label: f.label })) || [];
}

onMounted(() => {
	if (!props.node.data.operation) updateField('operation', 'Create New');
	parseConfig();
});

</script>

<style scoped>
.flow-steps { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 10px; background: #fff; border-bottom: 3px solid #f1f5f9; border-radius: 12px 12px 0 0; }
.flow-step { display: flex; align-items: center; gap: 8px; cursor: pointer; opacity: 0.5; transition: 0.2s; padding: 6px 12px; border-radius: 20px; }
.flow-step.active { opacity: 1; background: #eff6ff; color: #2563eb; font-weight: 700; transform: scale(1.05); }
.flow-step.disabled { cursor: not-allowed; pointer-events: none; }
.step-num { width: 22px; height: 22px; border-radius: 50%; background: #94a3b8; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 11px; }
.flow-step.active .step-num { background: #2563eb; }
.step-txt { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }

.step-content { padding: 20px; animation: slideIn 0.3s ease-out; }
@keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.mapping-table-wrapper { border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }
.table-mapping { margin-bottom: 0; }
.table-mapping th { background: #f8fafc; border-top: none; font-size: 11px; font-weight: 700; color: #64748b; padding: 8px 12px; }
.table-mapping td { vertical-align: middle; padding: 8px 12px; }

.source-input-group { position: relative; }
.source-hint { position: absolute; right: 8px; top: 4px; font-size: 9px; color: var(--primary); font-weight: 600; font-family: monospace; }

.btn-link { font-size: 12px; font-weight: 600; text-decoration: none !important; }
</style>
