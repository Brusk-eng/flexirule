<template>
	<div class="aggregate-records-config">
		<!-- Summary Header -->
		<div class="config-summary mb-4">
			<div class="summary-item">
				<span class="label">{{ __("Target Doctype") }}</span>
				<span class="value">{{ node.data.reference_doctype || '--' }}</span>
			</div>
			<div class="summary-item">
				<span class="label">{{ __("Function") }}</span>
				<span class="value badge secondary">{{ node.data.operation || 'count' }}</span>
			</div>
		</div>

		<!-- Operation Selection -->
		<div class="section-container mb-4">
			<label class="section-title">{{ __("Select Aggregation") }}</label>
			<div class="agg-types">
				<div 
					v-for="op in operations" 
					:key="op.value"
					:class="['agg-card', { active: node.data.operation === op.value }]"
					@click="updateField('operation', op.value)"
				>
					<div class="agg-icon">
						<i :class="op.icon"></i>
					</div>
					<div class="agg-label">{{ __(op.label) }}</div>
				</div>
			</div>
		</div>

		<!-- Configuration Grid -->
		<div class="config-grid mb-4">
			<div class="field-group">
				<ControlFactory
					:df="{
						fieldname: 'reference_doctype',
						label: __('Select DocType'),
						fieldtype: 'Link',
						options: 'DocType',
						reqd: 1
					}"
					:modelValue="node.data.reference_doctype"
					@update:modelValue="updateField('reference_doctype', $event)"
				/>
			</div>

			<div class="field-group" v-if="needsField">
				<ControlFactory
					:df="{
						fieldname: 'agg_field',
						label: __('Target Field'),
						fieldtype: 'Autocomplete',
						reqd: 1
					}"
					:modelValue="config.field"
					:get_options="getFields"
					@update:modelValue="updateConfig('field', $event)"
				/>
			</div>
		</div>

		<!-- Group By Specifics -->
		<div class="section-container mb-4 p-3 bg-light rounded border" v-if="node.data.operation === 'group_by'">
			<div class="row">
				<div class="col-6">
					<ControlFactory
						:df="{
							fieldname: 'group_by_field',
							label: __('Group By Field'),
							fieldtype: 'Autocomplete',
							reqd: 1
						}"
						:modelValue="config.group_by_field"
						:get_options="getFields"
						@update:modelValue="updateConfig('group_by_field', $event)"
					/>
				</div>
				<div class="col-6">
					<ControlFactory
						:df="{
							fieldname: 'agg_function',
							label: __('Value Function'),
							fieldtype: 'Select',
							options: 'count\nsum\navg\nmin\nmax',
							reqd: 1
						}"
						:modelValue="config.agg_function"
						@update:modelValue="updateConfig('agg_function', $event)"
					/>
				</div>
			</div>
		</div>

		<!-- Filters Interface -->
		<div class="section-container">
			<label class="section-title d-flex justify-content-between">
				<span>{{ __("Data Filters") }}</span>
				<button class="btn btn-xs btn-default" @click="addFilter" v-if="!readOnly">
					<i class="fa fa-filter"></i> {{ __("Add Filter") }}
				</button>
			</label>
			
			<div class="filter-box" v-if="filterRows.length">
				<div v-for="(f, idx) in filterRows" :key="idx" class="filter-item">
					<div class="f-col-field">
						<ControlFactory
							:df="{ fieldname: 'f', fieldtype: 'Autocomplete', placeholder: 'Field' }"
							:modelValue="f.field"
							:get_options="getFields"
							@update:modelValue="updateFilterRow(idx, 'field', $event)"
							hideLabel
						/>
					</div>
					<div class="f-col-op">
						<select v-model="f.op" @change="syncConfig" :disabled="readOnly">
							<option value="=">=</option>
							<option value="!=">!=</option>
							<option value=">">&gt;</option>
							<option value="<">&lt;</option>
						</select>
					</div>
					<div class="f-col-val">
						<input type="text" v-model="f.value" @input="syncConfig" placeholder="Value" :disabled="readOnly">
					</div>
					<button class="btn-del" @click="removeFilter(idx)" v-if="!readOnly">×</button>
				</div>
			</div>
			<div v-else class="empty-state p-3 text-center text-muted border rounded-sm dashed">
				{{ __("Calculating over all records (no filters).") }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, watch, onMounted } from "vue";
import { useStore } from "../../../store";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();

const operations = [
	{ value: "count", label: "Count", icon: "fa fa-hashtag" },
	{ value: "sum", label: "Sum", icon: "fa fa-plus" },
	{ value: "avg", label: "Average", icon: "fa fa-percent" },
	{ value: "min", label: "Minimum", icon: "fa fa-arrow-down" },
	{ value: "max", label: "Maximum", icon: "fa fa-arrow-up" },
	{ value: "group_by", label: "Group By", icon: "fa fa-th-large" },
];

const config = reactive({
	field: "",
	filters: {},
	group_by_field: "",
	agg_function: "count"
});

const filterRows = reactive([]);

function parseConfig() {
	let raw = {};
	try {
		raw = JSON.parse(props.node.data.config || "{}");
	} catch (e) { raw = {}; }
	
	config.field = raw.field || "";
	config.group_by_field = raw.group_by_field || "";
	config.agg_function = raw.agg_function || "count";
	
	const filters = raw.filters || {};
	filterRows.splice(0);
	Object.entries(filters).forEach(([f, v]) => {
		if (Array.isArray(v)) filterRows.push({ field: f, op: v[0], value: v[1] });
		else filterRows.push({ field: f, op: "=", value: v });
	});
}

function syncConfig() {
	if (props.readOnly) return;
	const activeFilters = {};
	filterRows.forEach(r => {
		if (r.field) {
			if (r.op === "=") activeFilters[r.field] = r.value;
			else activeFilters[r.field] = [r.op, r.value];
		}
	});
	
	const payload = {
		field: config.field,
		group_by_field: config.group_by_field,
		agg_function: config.agg_function,
		filters: activeFilters
	};
	props.node.data.config = JSON.stringify(payload);
	store.mark_dirty();
}

const needsField = computed(() => ["sum", "avg", "min", "max"].includes(props.node.data.operation));

function updateField(f, v) {
	if (props.readOnly) return;
	props.node.data[f] = v;
	syncConfig();
}

function updateConfig(k, v) {
	config[k] = v;
	syncConfig();
}

function addFilter() { filterRows.push({ field: "", op: "=", value: "" }); }
function removeFilter(i) { filterRows.splice(i, 1); syncConfig(); }
function updateFilterRow(i, k, v) { filterRows[i][k] = v; syncConfig(); }

async function getFields() {
	if (!props.node.data.reference_doctype) return [];
	await frappe.model.with_doctype(props.node.data.reference_doctype);
	const meta = frappe.get_meta(props.node.data.reference_doctype);
	return meta?.fields?.map(f => ({ value: f.fieldname, label: f.label })) || [];
}

onMounted(() => {
	if (!props.node.data.operation) updateField('operation', 'count');
	parseConfig();
});

</script>

<style scoped>
.config-summary {
	display: flex; gap: 20px; padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
}
.summary-item { display: flex; flex-direction: column; }
.summary-item .label { font-size: 9px; font-weight: 700; color: #64748b; text-transform: uppercase; }
.summary-item .value { font-size: 13px; font-weight: 600; }

.agg-types { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
.agg-card {
	padding: 12px 6px; border: 1px solid #e2e8f0; border-radius: 10px; text-align: center; cursor: pointer; transition: 0.2s; background: #fff;
}
.agg-card:hover { border-color: var(--primary); background: #f1f5f9; }
.agg-card.active { border-color: var(--primary); background: rgba(var(--primary-rgb), 0.05); color: var(--primary); }
.agg-icon { margin-bottom: 6px; font-size: 16px; opacity: 0.7; }
.agg-card.active .agg-icon { opacity: 1; }
.agg-label { font-size: 10px; font-weight: 600; }

.section-title { font-size: 12px; font-weight: 700; color: #475569; margin-bottom: 10px; }
.filter-box { display: flex; flex-direction: column; gap: 6px; }
.filter-item { display: flex; gap: 8px; align-items: center; padding: 6px; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; }
.f-col-field { flex: 2; }
.f-col-op { width: 60px; }
.f-col-op select { width: 100%; border: 1px solid #e2e8f0; font-size: 12px; border-radius: 4px; padding: 2px; }
.f-col-val { flex: 2; }
.f-col-val input { width: 100%; border: 1px solid #e2e8f0; font-size: 12px; border-radius: 4px; padding: 4px 8px; }

.btn-del { color: #94a3b8; border: none; background: none; font-size: 18px; cursor: pointer; }
.btn-del:hover { color: #ef4444; }
.dashed { border-style: dashed; }
</style>
