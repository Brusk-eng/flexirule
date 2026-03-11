<template>
	<div class="query-config">
		<div class="config-section section-card">
			<h5>{{ __("Query Records") }}</h5>
			<p class="text-muted small">
				{{ __("Configure the query mode and parameters.") }}
			</p>
		</div>

		<div class="config-section section-card">
			<ControlFactory
				:df="modeField"
				:modelValue="mode"
				:hideDescription="true"
				@update:modelValue="updateMode"
			/>
		</div>

		<div class="config-section section-card">
			<h6 class="text-muted">{{ __("Action Settings") }}</h6>
			<div class="action-settings-grid">
				<div class="grid-item span-2" v-if="mode !== 'Query Report'">
					<ControlFactory
						:df="withReadOnly(referenceDoctypeField)"
						:modelValue="props.node?.data?.reference_doctype"
						@update:modelValue="(val) => updateActionField('reference_doctype', val)"
					/>
				</div>
				<div class="grid-item span-2" v-if="mode === 'Query Doc'">
					<ControlFactory
						:df="withReadOnly(referenceDocnameField)"
						:modelValue="props.node?.data?.reference_docname"
						@update:modelValue="(val) => updateActionField('reference_docname', val)"
					/>
				</div>
				<div class="grid-item span-2" v-if="mode === 'Query Report'">
					<ControlFactory
						:df="withReadOnly(reportLinkField)"
						:modelValue="props.node?.data?.reference_docname"
						@update:modelValue="(val) => onSelectReport(val)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="withReadOnly(inputSourceField)"
						:modelValue="props.node?.data?.input_source"
						@update:modelValue="(val) => updateActionField('input_source', val)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="withReadOnly(mutationModeField)"
						:modelValue="props.node?.data?.mutation_mode"
						@update:modelValue="(val) => updateActionField('mutation_mode', val)"
					/>
				</div>
			</div>
		</div>

		<div v-if="!mode" class="alert alert-warning mt-3">
			{{ __("Select a query mode to configure its parameters.") }}
		</div>

		<div v-else class="config-section section-card">
			<template v-if="mode === 'Query List'">
				<div class="sub-section section-subcard">
					<h6>{{ __("Filters") }}</h6>
					<div class="table-rows">
						<div v-for="(row, idx) in filterRows" :key="idx" class="row-item">
							<FieldPickerControl
								:df="{ label: '' }"
								:fields="doctypeFields"
								:documentType="referenceDoctype"
								:modelValue="row.field"
								:read_only="readOnly"
								@update:modelValue="(val) => (row.field = val)"
							/>
							<select
								class="form-control input-xs"
								v-model="row.operator"
								:disabled="readOnly"
								@change="syncConfig"
							>
								<option v-for="op in operators" :key="op" :value="op">
									{{ op }}
								</option>
							</select>
							<input
								class="form-control input-xs"
								v-model="row.value"
								:placeholder="__('Value')"
								:disabled="readOnly"
								@change="syncConfig"
							/>
							<select
								class="form-control input-xs"
								v-model="row.value_type"
								:disabled="readOnly"
								@change="syncConfig"
							>
								<option v-for="vt in valueTypes" :key="vt" :value="vt">
									{{ __(vt) }}
								</option>
							</select>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger"
								@click="removeFilter(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addFilter">
							<i class="fa fa-plus"></i> {{ __("Add Filter") }}
						</button>
					</div>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Fields") }}</h6>
					<div class="table-rows">
						<div v-for="(row, idx) in fieldRows" :key="idx" class="row-item">
							<FieldPickerControl
								:df="{ label: '' }"
								:fields="doctypeFields"
								:documentType="referenceDoctype"
								:modelValue="row.field"
								:read_only="readOnly"
								@update:modelValue="(val) => (row.field = val)"
							/>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger"
								@click="removeField(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addField">
							<i class="fa fa-plus"></i> {{ __("Add Field") }}
						</button>
					</div>
				</div>

				<div class="sub-section section-subcard">
					<ControlFactory
						:df="withReadOnly(limitField)"
						:modelValue="config.limit"
						@update:modelValue="(val) => updateConfigKey('limit', val)"
					/>
					<ControlFactory
						:df="withReadOnly(orderByField)"
						:modelValue="config.order_by"
						@update:modelValue="(val) => updateConfigKey('order_by', val)"
					/>
					<FieldPickerControl
						:df="groupByField"
						:fields="doctypeFields"
						:documentType="referenceDoctype"
						:modelValue="config.group_by"
						:read_only="readOnly"
						@update:modelValue="(val) => updateConfigKey('group_by', val)"
					/>
				</div>
			</template>

			<template v-else-if="mode === 'Query Doc'">
				<ControlFactory
					:df="withReadOnly(docnameField)"
					:modelValue="config.docname"
					@update:modelValue="(val) => updateConfigKey('docname', val)"
				/>
				<ControlFactory
					:df="withReadOnly(docnameExprField)"
					:modelValue="config.docname_expression"
					@update:modelValue="(val) => updateConfigKey('docname_expression', val)"
				/>
			</template>

			<template v-else-if="mode === 'Exist Record'">
				<div class="sub-section section-subcard">
					<h6>{{ __("Filters") }}</h6>
					<div class="table-rows">
						<div v-for="(row, idx) in filterRows" :key="idx" class="row-item">
							<FieldPickerControl
								:df="{ label: '' }"
								:fields="doctypeFields"
								:documentType="referenceDoctype"
								:modelValue="row.field"
								:read_only="readOnly"
								@update:modelValue="(val) => (row.field = val)"
							/>
							<select
								class="form-control input-xs"
								v-model="row.operator"
								:disabled="readOnly"
								@change="syncConfig"
							>
								<option v-for="op in operators" :key="op" :value="op">
									{{ op }}
								</option>
							</select>
							<input
								class="form-control input-xs"
								v-model="row.value"
								:placeholder="__('Value')"
								:disabled="readOnly"
								@change="syncConfig"
							/>
							<select
								class="form-control input-xs"
								v-model="row.value_type"
								:disabled="readOnly"
								@change="syncConfig"
							>
								<option v-for="vt in valueTypes" :key="vt" :value="vt">
									{{ __(vt) }}
								</option>
							</select>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger"
								@click="removeFilter(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addFilter">
							<i class="fa fa-plus"></i> {{ __("Add Filter") }}
						</button>
					</div>
				</div>
			</template>

			<template v-else-if="mode === 'Query Report'">
				<div v-if="reportFilters.length" class="sub-section">
					<h6>{{ __("Report Filters") }}</h6>
					<div class="table-rows">
						<div
							v-for="df in reportFilters"
							:key="df.fieldname"
							class="row-item report"
						>
							<ControlFactory
								:df="withReadOnly(df)"
								:modelValue="reportFilterValues[df.fieldname]"
								@update:modelValue="(val) => updateReportFilter(df.fieldname, val)"
							/>
						</div>
					</div>
				</div>
				<div v-else class="text-muted small">
					{{ __("Select a report to load its filters.") }}
				</div>
			</template>

			<template v-else-if="mode === 'Query API'">
				<ControlFactory
					:df="withReadOnly(methodField)"
					:modelValue="config.method"
					@update:modelValue="(val) => updateConfigKey('method', val)"
				/>
				<div class="sub-section section-subcard">
					<h6>{{ __("Arguments") }}</h6>
					<div class="table-rows">
						<div v-for="(row, idx) in argRows" :key="idx" class="row-item">
							<input
								class="form-control input-xs"
								v-model="row.key"
								:placeholder="__('Key')"
								:disabled="readOnly"
								@change="syncConfig"
							/>
							<input
								class="form-control input-xs"
								v-model="row.value"
								:placeholder="__('Value')"
								:disabled="readOnly"
								@change="syncConfig"
							/>
							<select
								class="form-control input-xs"
								v-model="row.value_type"
								:disabled="readOnly"
								@change="syncConfig"
							>
								<option v-for="vt in valueTypes" :key="vt" :value="vt">
									{{ __(vt) }}
								</option>
							</select>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger"
								@click="removeArg(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addArg">
							<i class="fa fa-plus"></i> {{ __("Add Argument") }}
						</button>
					</div>
				</div>
			</template>
		</div>

		<div class="config-section section-card test-section">
			<button class="btn btn-xs btn-default" @click="testQuery" :disabled="readOnly">
				<i class="fa fa-flask"></i> {{ __("Test Query") }}
			</button>
			<span v-if="testStatus" class="ml-2 text-muted">{{ testStatus }}</span>
		</div>

		<div v-if="detectedKeys.length" class="config-section section-card">
			<h6>{{ __("Detected Return Keys") }}</h6>
			<ul class="small text-muted">
				<li v-for="k in detectedKeys" :key="k.key">{{ k.key }}</li>
			</ul>
		</div>
	</div>
</template>

<script setup>
import { reactive, ref, computed, watch } from "vue";
import { useStore } from "../../../store";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();
const config = reactive({});
const testStatus = ref("");

const filterRows = ref([]);
const fieldRows = ref([]);
const argRows = ref([]);
const doctypeFields = ref([]);

const reportFilters = ref([]);
const reportFilterValues = reactive({});

const mode = computed(() => props.node?.data?.operation || "");
const referenceDoctype = computed(() => props.node?.data?.reference_doctype || "");

const operators = ["=", "!=", ">", ">=", "<", "<=", "in", "not in"];
const valueTypes = ["Value", "Number", "Boolean", "Expression"];

const modeField = computed(() => ({
	fieldname: "operation",
	fieldtype: "Select",
	label: __("Mode"),
	options: "Query List\nQuery Doc\nExist Record\nQuery Report\nQuery API",
	read_only: props.readOnly,
}));

const referenceDoctypeField = {
	fieldname: "reference_doctype",
	fieldtype: "Link",
	label: __("Reference DocType"),
	options: "DocType",
	reqd: 1,
};

const referenceDocnameField = {
	fieldname: "reference_docname",
	fieldtype: "Data",
	label: __("Reference Document"),
	description: __("Optional static document name."),
};

const reportLinkField = {
	fieldname: "reference_docname",
	fieldtype: "Link",
	label: __("Report"),
	options: "Report",
};

const inputSourceField = {
	fieldname: "input_source",
	fieldtype: "Select",
	label: __("Input Source"),
	options: "Context Doc\nContext Variable\nBoth",
};

const mutationModeField = {
	fieldname: "mutation_mode",
	fieldtype: "Select",
	label: __("Mutation Mode"),
	options:
		"Set Doc Field\nUpdate Doc Field\nSet Context Variable\nUpdate Context Variable\nAppend to Context Variable\nBatch Database Set",
};

const limitField = {
	fieldname: "limit",
	fieldtype: "Int",
	label: __("Limit"),
	description: __("Max rows to return."),
};

const orderByField = {
	fieldname: "order_by",
	fieldtype: "Data",
	label: __("Order By"),
	description: __("Example: modified desc"),
};

const groupByField = {
	fieldname: "group_by",
	fieldtype: "Data",
	label: __("Group By"),
	description: __("Optional group by field."),
};

const docnameField = {
	fieldname: "docname",
	fieldtype: "Data",
	label: __("Document Name"),
};

const docnameExprField = {
	fieldname: "docname_expression",
	fieldtype: "Code",
	label: __("Docname Expression"),
	options: "PythonExpression",
};

const methodField = {
	fieldname: "method",
	fieldtype: "Data",
	label: __("Whitelisted Method"),
};

const detectedKeys = computed(() => props.node?.data?.resolved_output_schema || []);

function withReadOnly(field) {
	return { ...field, read_only: props.readOnly };
}

function updateMode(value) {
	if (!props.node?.data) return;
	props.node.data.operation = value;
	if (value === "Query Report") {
		props.node.data.reference_doctype = "Report";
	}
	store.mark_dirty();
}

function updateActionField(fieldname, value) {
	if (!props.node?.data) return;
	props.node.data[fieldname] = value;
	store.mark_dirty();
}

async function loadDoctypeFields(doctype) {
	if (!doctype) {
		doctypeFields.value = [];
		return;
	}
	try {
		doctypeFields.value = await flexirule.utils.get_doctype_fields(doctype);
	} catch (e) {
		doctypeFields.value = [];
	}
}

async function onSelectReport(val) {
	if (!props.node?.data) return;
	props.node.data.reference_doctype = "Report";
	props.node.data.reference_docname = val;
	store.mark_dirty();
	await loadReportFilters(val);
}

function updateConfigKey(key, value) {
	config[key] = value;
	syncConfig();
}

function addFilter() {
	filterRows.value.push({ field: "", operator: "=", value: "", value_type: "Value" });
}

function removeFilter(idx) {
	filterRows.value.splice(idx, 1);
	syncConfig();
}

function addField() {
	fieldRows.value.push({ field: "" });
}

function removeField(idx) {
	fieldRows.value.splice(idx, 1);
	syncConfig();
}

function addArg() {
	argRows.value.push({ key: "", value: "", value_type: "Value" });
}

function removeArg(idx) {
	argRows.value.splice(idx, 1);
	syncConfig();
}

function parseValueType(val) {
	if (typeof val === "number") return "Number";
	if (typeof val === "boolean") return "Boolean";
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
		return "Expression";
	}
	return "Value";
}

function stripExpression(val) {
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
		return val.slice(1, -1);
	}
	return val;
}

function encodeValue(row) {
	let val = row.value;
	if (row.value_type === "Number") {
		const num = Number(val);
		if (!Number.isNaN(num)) return num;
		return val;
	}
	if (row.value_type === "Boolean") {
		if (val === true || val === "true" || val === 1 || val === "1") return true;
		if (val === false || val === "false" || val === 0 || val === "0") return false;
		return Boolean(val);
	}
	if (row.value_type === "Expression") {
		return `{${val}}`;
	}
	return val;
}

function buildFilters() {
	const filters = {};
	filterRows.value.forEach((row) => {
		if (!row.field) return;
		let val = encodeValue(row);
		if (["in", "not in"].includes(row.operator) && typeof val === "string") {
			val = val
				.split(",")
				.map((v) => v.trim())
				.filter((v) => v);
		}
		if (row.operator && row.operator !== "=") {
			filters[row.field] = [row.operator, val];
		} else {
			filters[row.field] = val;
		}
	});
	return filters;
}

function buildFields() {
	return fieldRows.value.map((r) => r.field).filter((f) => f);
}

function buildArgs() {
	const args = {};
	argRows.value.forEach((row) => {
		if (!row.key) return;
		args[row.key] = encodeValue(row);
	});
	return args;
}

function syncConfig() {
	const newConfig = {};
	Object.keys(config).forEach((k) => {
		const val = config[k];
		if (val !== undefined && val !== null && val !== "") newConfig[k] = val;
	});

	if (["Query List", "Exist Record"].includes(mode.value)) {
		const filters = buildFilters();
		if (Object.keys(filters).length) newConfig.filters = filters;
	}

	if (mode.value === "Query List") {
		const fields = buildFields();
		if (fields.length) newConfig.fields = fields;
	}

	if (mode.value === "Query API") {
		const args = buildArgs();
		if (Object.keys(args).length) newConfig.args = args;
	}

	if (mode.value === "Query Report") {
		const reportName = props.node?.data?.reference_docname || config.report_name;
		if (reportName) newConfig.report_name = reportName;
		const filters = { ...reportFilterValues };
		if (Object.keys(filters).length) newConfig.filters = filters;
	}

	assignConfig(newConfig);
}

function assignConfig(newConfig) {
	if (!props.node?.data) return;
	let current = props.node.data.config || {};
	if (typeof current === "string") {
		try {
			current = JSON.parse(current);
		} catch (e) {
			current = {};
		}
	}
	const currentStr = JSON.stringify(current || {});
	const nextStr = JSON.stringify(newConfig || {});
	if (currentStr !== nextStr) {
		props.node.data.config = newConfig;
		store.mark_dirty();
	}
}

async function loadReportFilters(reportName) {
	if (!reportName) {
		reportFilters.value = [];
		Object.keys(reportFilterValues).forEach((k) => delete reportFilterValues[k]);
		return;
	}
	try {
		const res = await frappe.call({
			method: "frappe.desk.query_report.get_script",
			args: { report_name: reportName },
		});
		const filters = res.message?.filters || [];
		reportFilters.value = filters.map((f) => ({
			fieldname: f.fieldname,
			fieldtype: f.fieldtype || "Data",
			label: f.label || f.fieldname,
			options: f.options,
			reqd: f.reqd || 0,
			default: f.default,
		}));
		Object.keys(reportFilterValues).forEach((k) => delete reportFilterValues[k]);
		reportFilters.value.forEach((df) => {
			if (df.default !== undefined) reportFilterValues[df.fieldname] = df.default;
		});
		syncConfig();
	} catch (e) {
		console.error("Failed to load report filters", e);
		reportFilters.value = [];
	}
}

function updateReportFilter(fieldname, value) {
	reportFilterValues[fieldname] = value;
	syncConfig();
}

function loadConfig(val) {
	let parsed = {};
	if (typeof val === "string") {
		try {
			parsed = JSON.parse(val);
		} catch (e) {
			parsed = {};
		}
	} else if (val && typeof val === "object") {
		parsed = val;
	}

	Object.keys(config).forEach((k) => delete config[k]);
	Object.assign(config, parsed);

	const filters = parsed.filters || {};
	filterRows.value = Object.entries(filters).map(([field, val]) => {
		let operator = "=";
		let value = val;
		if (Array.isArray(val) && val.length === 2) {
			operator = val[0];
			value = val[1];
		}
		const value_type = parseValueType(value);
		return {
			field,
			operator,
			value: stripExpression(value),
			value_type,
		};
	});

	const fields = parsed.fields || [];
	fieldRows.value = Array.isArray(fields) ? fields.map((f) => ({ field: f })) : [];

	const args = parsed.args || {};
	argRows.value = Object.entries(args).map(([key, value]) => ({
		key,
		value: stripExpression(value),
		value_type: parseValueType(value),
	}));

	if (mode.value === "Query Report") {
		const reportName = props.node?.data?.reference_docname || parsed.report_name;
		if (reportName) {
			loadReportFilters(reportName);
			Object.keys(reportFilterValues).forEach((k) => delete reportFilterValues[k]);
			Object.assign(reportFilterValues, parsed.filters || {});
		}
	}
}

watch(
	() => props.node?.data?.config,
	(val) => loadConfig(val),
	{ immediate: true }
);

watch(
	() => referenceDoctype.value,
	(val) => loadDoctypeFields(val),
	{ immediate: true }
);

watch(
	() => [filterRows.value, fieldRows.value, argRows.value, reportFilterValues, config],
	() => {
		syncConfig();
	},
	{ deep: true }
);

async function testQuery() {
	if (!props.node?.data?.action_id || !store.rule_doc?.name) return;
	if (store.is_dirty) {
		frappe.msgprint(__("Please save the rule before testing."));
		return;
	}
	try {
		testStatus.value = __("Running...");
		const res = await frappe.call({
			method: "flexirule.ruleflow.api.test_action_query",
			args: {
				rule_name: store.rule_doc.name,
				action_id: props.node.data.action_id,
			},
		});
		const message = res.message || {};
		if (message.success) {
			props.node.data.resolved_output_schema = message.detected_keys || [];
			store.mark_dirty();
			testStatus.value = __("OK ({0}s)").replace("{0}", message.duration || 0);
		} else {
			testStatus.value = __("Failed");
			frappe.msgprint(message.error || __("Query test failed"));
		}
	} catch (e) {
		testStatus.value = __("Failed");
		frappe.msgprint(e.message || __("Query test failed"));
	}
}

function validate() {
	return { valid: true };
}

defineExpose({ validate });
</script>

<style scoped>
.query-config {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.config-section {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.section-card {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 12px;
	background: var(--bg-light, #fff);
}

.section-subcard {
	border: 1px dashed var(--border-color);
	border-radius: 6px;
	padding: 10px;
}

.sub-section {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.action-settings-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 10px;
}

.grid-item.span-2 {
	grid-column: 1 / -1;
}

.table-rows {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.row-item {
	display: grid;
	grid-template-columns: 1.3fr 0.7fr 1fr 0.8fr auto;
	gap: 6px;
	align-items: center;
}

.row-item .field-picker-control {
	margin-bottom: 0;
}

.row-item.report {
	grid-template-columns: 1fr;
}

.test-section {
	display: flex;
	align-items: center;
	gap: 8px;
}
</style>
