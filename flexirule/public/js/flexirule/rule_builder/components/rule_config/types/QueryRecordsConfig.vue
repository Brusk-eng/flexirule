<template>
	<div class="query-records-config">
		<!-- Summary Header -->
		<div class="config-summary mb-4">
			<div class="summary-item">
				<span class="label" v-if="node.data.operation === 'Query Report'">{{ __("Report") }}</span>
				<span class="label" v-else>{{ __("Target Doctype") }}</span>
				<span class="value">{{ node.data.reference_doctype || node.data.reference_docname || '--' }}</span>
			</div>
			<div class="summary-item">
				<span class="label">{{ __("Mode") }}</span>
				<span class="value badge">{{ node.data.operation || 'Query List' }}</span>
			</div>
		</div>

		<!-- Mode Selection -->
		<div class="section-container mb-4">
			<label class="section-title">{{ __("Select Query Mode") }}</label>
			<div class="mode-cards">
				<div 
					v-for="mode in modes" 
					:key="mode.value"
					:class="['mode-card', { active: node.data.operation === mode.value }]"
					@click="updateField('operation', mode.value)"
				>
					<i :class="mode.icon"></i>
					<div class="mode-text">
						<div class="mode-name">{{ __(mode.label) }}</div>
						<div class="mode-desc">{{ __(mode.description) }}</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Primary Config -->
		<div class="section-container mb-4">
			<div class="row">
				<div class="col-6" v-if="node.data.operation !== 'Query Report'">
					<ControlFactory
						:df="{
							fieldname: 'reference_doctype',
							label: __('Target DocType'),
							fieldtype: 'Link',
							options: 'DocType',
							placeholder: __('Select Doctype...'),
							reqd: 1
						}"
						:modelValue="node.data.reference_doctype"
						@update:modelValue="updateField('reference_doctype', $event)"
					/>
				</div>
				<div class="col-6" v-if="node.data.operation === 'Query Doc'">
					<ControlFactory
						:df="{
							fieldname: 'reference_docname',
							label: __('Document Name'),
							fieldtype: 'Dynamic Link',
							options: 'reference_doctype',
							placeholder: __('Select Record...'),
							reqd: 1
						}"
						:modelValue="node.data.reference_docname"
						:doc="node.data"
						@update:modelValue="updateField('reference_docname', $event)"
					/>
				</div>
				<div class="col-12" v-if="node.data.operation === 'Query Report'">
					<ControlFactory
						:df="{
							fieldname: 'reference_docname',
							label: __('Select Report'),
							fieldtype: 'Link',
							options: 'Report',
							placeholder: __('Select Report...'),
							reqd: 1
						}"
						:modelValue="node.data.reference_docname"
						@update:modelValue="updateField('reference_docname', $event)"
					/>
				</div>
			</div>
		</div>

		<!-- Filter Builder (simplified version) -->
		<div class="section-container mb-4" v-if="showFilters">
			<label class="section-title d-flex justify-content-between">
				<span>{{ __("Filters") }}</span>
				<button class="btn btn-xs btn-default" @click="addFilter" v-if="!readOnly">
					<i class="fa fa-plus"></i> {{ __("Add Filter") }}
				</button>
			</label>
			
			<div class="filters-list" v-if="filterRows.length">
				<div v-for="(f, idx) in filterRows" :key="idx" class="filter-row">
					<div class="filter-field">
						<ControlFactory
							:df="{
								fieldname: 'field',
								label: '',
								fieldtype: 'Autocomplete',
								placeholder: __('Field...')
							}"
							:modelValue="f.field"
							:get_options="getFields"
							@update:modelValue="updateFilter(idx, 'field', $event)"
							hideLabel
						/>
					</div>
					<div class="filter-op">
						<select 
							v-model="f.op" 
							class="form-control form-control-sm"
							@change="syncConfig"
							:disabled="readOnly"
						>
							<option value="=">=</option>
							<option value="!=">!=</option>
							<option value=">">&gt;</option>
							<option value="<">&lt;</option>
							<option value=">=">&gt;=</option>
							<option value="<=">&lt;=</option>
							<option value="like">like</option>
							<option value="in">in</option>
						</select>
					</div>
					<div class="filter-value">
						<input 
							type="text" 
							v-model="f.value" 
							class="form-control form-control-sm"
							:placeholder="__('Value...')"
							@input="syncConfig"
							:disabled="readOnly"
						>
					</div>
					<button class="btn-remove" @click="removeFilter(idx)" v-if="!readOnly">×</button>
				</div>
			</div>
			<div v-else class="empty-filters p-4 text-center text-muted">
				{{ __("No filters defined. All records will be matched.") }}
			</div>
		</div>

		<!-- Meta Settings: Limit and Ignore Permissions -->
		<div class="section-container mb-4" v-if="showMetaSettings">
			<div class="row align-items-end">
				<div class="col-6" v-if="showLimit">
					<ControlFactory
						:df="{
							fieldname: 'limit',
							label: __('Limit Results'),
							fieldtype: 'Int',
							placeholder: __('All')
						}"
						:modelValue="config.limit"
						@update:modelValue="updateConfig('limit', $event)"
					/>
				</div>
				<div class="col-6">
					<ControlFactory
						:df="{
							fieldname: 'ignore_permissions',
							label: __('Ignore Permissions'),
							fieldtype: 'Check'
						}"
						:modelValue="config.ignore_permissions"
						@update:modelValue="updateConfig('ignore_permissions', $event)"
					/>
				</div>
			</div>
		</div>

		<!-- Fields / Columns Selection (Moved to End) -->
		<div class="section-container mb-4" v-if="showFieldSelection">
			<label class="section-title">{{ node.data.operation === 'Query Report' ? __("Columns to Fetch") : __("Fields to Fetch") }}</label>
			<div class="field-selection-wrapper">
				<ControlFactory
					:df="{
						fieldname: 'fields',
						label: '',
						fieldtype: 'MultiSelect',
						placeholder: node.data.operation === 'Query Report' ? __('Add columns...') : __('Add fields...')
					}"
					:modelValue="config.fields"
					:get_data="getFieldsForMultiSelect"
					@update:modelValue="updateConfig('fields', $event)"
				/>
				<p class="text-muted small mt-1" v-if="node.data.operation !== 'Query Report'">
					{{ __("Leave empty to fetch all fields.") }}
				</p>
			</div>
		</div>

		<!-- Advanced Settings (JSON) -->
		<div class="section-container">
			<div class="d-flex justify-content-between align-items-center mb-2">
				<label class="section-title mb-0">{{ __("Advanced JSON Config") }}</label>
				<button 
					class="btn btn-xs btn-link" 
					@click="showJson = !showJson"
				>
					{{ showJson ? __('Hide') : __('Edit Raw JSON') }}
				</button>
			</div>
			<div v-if="showJson" class="json-editor">
				<ControlFactory
					:df="{
						fieldname: 'config',
						label: '',
						fieldtype: 'Code',
						options: 'JSON'
					}"
					:modelValue="node.data.config"
					@update:modelValue="updateField('config', $event)"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useStore } from "../../../store";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();
const showJson = ref(false);

const modes = [
	{ 
		value: "Query List", 
		label: "Query List", 
		icon: "fa fa-list", 
		description: "Fetch multiple records matching filters." 
	},
	{ 
		value: "Query Doc", 
		label: "Query Doc", 
		icon: "fa fa-file-text-o", 
		description: "Fetch a specific record by name or filter." 
	},
	{ 
		value: "Exist Record", 
		label: "Exist Record", 
		icon: "fa fa-check-square-o", 
		description: "Check if any record matches given filters." 
	},
	{ 
		value: "Query Report", 
		label: "Query Report", 
		icon: "fa fa-table", 
		description: "Execute a Frappe Report and fetch results." 
	},
	{ 
		value: "Query API", 
		label: "Query API", 
		icon: "fa fa-exchange", 
		description: "Call a whitelisted server-side method." 
	}
];

const showFilters = computed(() => {
	return ["Query List", "Query Doc", "Exist Record"].includes(props.node.data.operation);
});

const showFieldSelection = computed(() => {
	return ["Query List", "Query Doc", "Query Report"].includes(props.node.data.operation);
});

const showMetaSettings = computed(() => {
	return ["Query List", "Query Doc", "Exist Record", "Query Report"].includes(props.node.data.operation);
});

const showLimit = computed(() => {
	return ["Query List", "Query Report"].includes(props.node.data.operation);
});

// Flat filter array for UI
const filterRows = reactive([]);
const config = reactive({
	fields: [],
	limit: 0,
	ignore_permissions: 0
});

// Cache for suggestions
const cached_fields = ref([]);
const cached_report_columns = ref([]);

function parseInitalConfig() {
	let rawConfig = {};
	try {
		rawConfig = JSON.parse(props.node.data.config || "{}");
	} catch (e) { rawConfig = {}; }

	config.fields = rawConfig.fields || [];
	config.limit = rawConfig.limit || 0;
	config.ignore_permissions = rawConfig.ignore_permissions || 0;

	const filters = rawConfig.filters || {};
	filterRows.splice(0);
	
	Object.entries(filters).forEach(([field, val]) => {
		if (Array.isArray(val) && val.length === 2) {
			filterRows.push({ field, op: val[0], value: val[1] });
		} else {
			filterRows.push({ field, op: "=", value: val });
		}
	});
}

function syncConfig() {
	if (props.readOnly) return;
	
	let rawConfig = {};
	try {
		rawConfig = JSON.parse(props.node.data.config || "{}");
	} catch (e) { rawConfig = {}; }

	const activeFilters = {};
	filterRows.forEach(f => {
		if (f.field) {
			if (f.op === "=") activeFilters[f.field] = f.value;
			else activeFilters[f.field] = [f.op, f.value];
		}
	});

	rawConfig.filters = activeFilters;
	rawConfig.fields = config.fields;
	rawConfig.limit = config.limit;
	rawConfig.ignore_permissions = config.ignore_permissions;
	
	props.node.data.config = JSON.stringify(rawConfig);
	store.mark_dirty();
}

function updateField(fieldname, value) {
	if (props.readOnly) return;
	props.node.data[fieldname] = value;
	if (fieldname === 'operation') {
		syncConfig(); 
	}
	store.mark_dirty();
}

function updateConfig(key, value) {
	if (props.readOnly) return;
	config[key] = value;
	syncConfig();
}

function addFilter() {
	filterRows.push({ field: "", op: "=", value: "" });
}

function removeFilter(idx) {
	filterRows.splice(idx, 1);
	syncConfig();
}

function updateFilter(idx, key, val) {
	filterRows[idx][key] = val;
	syncConfig();
}

async function getFields() {
	if (!props.node.data.reference_doctype) return [];
	await frappe.model.with_doctype(props.node.data.reference_doctype);
	const meta = frappe.get_meta(props.node.data.reference_doctype);
	if (!meta?.fields) return [];
	cached_fields.value = meta.fields
		.filter(df => !frappe.model.layout_fields.includes(df.fieldtype) && !df.hidden)
		.map(df => ({ value: df.fieldname, label: df.label }));
	return cached_fields.value;
}

async function fetchReportColumns() {
	if (props.node.data.operation !== 'Query Report' || !props.node.data.reference_docname) {
		cached_report_columns.value = [];
		return;
	}
	try {
		const res = await frappe.call({
			method: "frappe.desk.query_report.get_script",
			args: { report_name: props.node.data.reference_docname }
		});
		if (res.message && res.message.columns) {
			cached_report_columns.value = res.message.columns.map(col => {
				if (typeof col === 'string') {
					const parts = col.split(':');
					const fieldname = parts[0].trim();
					return { value: fieldname, label: fieldname };
				}
				return { value: col.fieldname, label: col.label || col.fieldname };
			});
		}
	} catch (e) {
		console.warn("Failed to fetch report columns", e);
		cached_report_columns.value = [];
	}
}

function getFieldsForMultiSelect(query) {
	let list = [];
	if (props.node.data.operation === 'Query Report') {
		list = cached_report_columns.value;
	} else {
		list = cached_fields.value;
	}

	if (!query) return list;
	const q = query.toLowerCase();
	return list.filter(f => 
		(f.value || "").toLowerCase().includes(q) || 
		(f.label || "").toLowerCase().includes(q)
	);
}

onMounted(async () => {
	if (!props.node.data.operation) {
		updateField('operation', 'Query List');
	}
	parseInitalConfig();
	if (props.node.data.reference_doctype) await getFields();
	if (props.node.data.operation === 'Query Report' && props.node.data.reference_docname) {
		await fetchReportColumns();
	}
});

watch(() => props.node.data.reference_doctype, async (val) => {
	if (val) await getFields();
});

watch(() => props.node.data.reference_docname, async (val) => {
	if (props.node.data.operation === 'Query Report' && val) {
		await fetchReportColumns();
	}
});

</script>

<style scoped>
.query-records-config {
	font-family: var(--font-stack-sans);
}

.config-summary {
	display: flex;
	gap: 24px;
	padding: 16px;
	background: #f1f5f9;
	border-radius: 12px;
	border: 1px solid #e2e8f0;
}

.summary-item {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.summary-item .label {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	color: #64748b;
}

.summary-item .value {
	font-size: 14px;
	font-weight: 600;
}

.section-title {
	font-size: 13px;
	font-weight: 700;
	color: #334155;
	margin-bottom: 12px;
	display: block;
}

.mode-cards {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
	gap: 12px;
}

.mode-card {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 12px;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 10px;
	cursor: pointer;
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.mode-card:hover {
	border-color: var(--primary);
	background: #f8fafc;
	transform: translateY(-1px);
}

.mode-card.active {
	border-color: var(--primary);
	background: rgba(var(--primary-rgb), 0.04);
	box-shadow: 0 0 0 1px var(--primary);
}

.mode-card i {
	font-size: 18px;
	color: #94a3b8;
	width: 24px;
	text-align: center;
}

.mode-card.active i {
	color: var(--primary);
}

.mode-name {
	font-size: 13px;
	font-weight: 700;
}

.mode-desc {
	font-size: 11px;
	color: #64748b;
}

.filters-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.filter-row {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
}

.filter-field { flex: 1; }
.filter-op { width: 80px; }
.filter-value { flex: 1; }

.btn-remove {
	background: none;
	border: none;
	color: #94a3b8;
	font-size: 18px;
	cursor: pointer;
	padding: 0 4px;
}

.btn-remove:hover { color: #ef4444; }

.empty-filters {
	background: #f8fafc;
	border: 1px dashed #cbd5e1;
	border-radius: 8px;
	font-size: 12px;
}

.json-editor {
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	overflow: hidden;
}

.small { font-size: 11px; }

.field-selection-wrapper {
	padding: 12px;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
}
</style>
