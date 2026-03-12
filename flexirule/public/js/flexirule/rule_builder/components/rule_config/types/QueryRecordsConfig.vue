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
				<div v-if="reportFilters.length || loading" class="sub-section">
					<div class="section-header">
						<h6>{{ __("Report Filters") }}</h6>
						<div
							v-if="loading"
							class="spinner-border spinner-border-sm text-muted"
						></div>
					</div>
					<div class="table-rows report-filter-table">
						<div
							v-for="df in visibleFilters"
							:key="df.fieldname"
							class="row-item report-filter-row"
						>
							<div class="filter-label-group">
								<label class="filter-label">{{ df.label }}</label>
								<div class="filter-type-toggle">
									<button
										class="btn btn-xs btn-link p-0"
										:class="{
											active:
												reportFilterTypes[df.fieldname] === 'Expression',
										}"
										@click="toggleReportFilterType(df.fieldname)"
										:title="__('Toggle Expression')"
									>
										<span class="extra-small font-weight-bold">{{
											reportFilterTypes[df.fieldname] === "Expression"
												? "{ }"
												: "abc"
										}}</span>
									</button>
								</div>
							</div>

							<div class="filter-input-wrapper">
								<template v-if="reportFilterTypes[df.fieldname] === 'Expression'">
									<div class="expression-input-group">
										<span class="expr-prefix">{</span>
										<AutocompleteControl
											:df="{
												fieldtype: 'Autocomplete',
												label: '',
												read_only: readOnly,
											}"
											:modelValue="
												stripExpression(reportFilterValues[df.fieldname])
											"
											:get_options="getVariableOptions"
											:placeholder="__('variable')"
											:read_only="readOnly"
											@update:modelValue="
												reportFilterValues[df.fieldname] = `{${$event}}`;
												syncConfig();
											"
										/>
										<span class="expr-suffix">}</span>
									</div>
								</template>
								<template v-else>
									<ControlFactory
										:df="{ ...withReadOnly(df), label: '' }"
										:modelValue="reportFilterValues[df.fieldname]"
										@update:modelValue="
											updateReportFilter(df.fieldname, $event)
										"
									/>
								</template>
							</div>
						</div>
					</div>
				</div>
				<div v-else class="text-muted small p-4 text-center border-dashed rounded">
					<i class="fa fa-info-circle mb-2 d-block opacity-50"></i>
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
			<button
				class="btn btn-xs btn-primary shadow-sm"
				@click="testQuery"
				:disabled="readOnly"
			>
				<i class="fa fa-flask mr-1"></i> {{ __("Refresh Schema (Test Query)") }}
			</button>
			<span v-if="testStatus" class="ml-2 text-muted font-weight-bold">{{ testStatus }}</span>
		</div>
	</div>
</template>

<script setup>
import { reactive, ref, computed, watch } from "vue";
import { useStore } from "../../../store";
import ControlFactory from "../../../controls/ControlFactory.vue";
import AutocompleteControl from "../../../controls/AutocompleteControl.vue";
import FieldPickerControl from "../../../controls/FieldPickerControl.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();
const config = reactive({});
const testStatus = ref("");
const loading = ref(false);

const filterRows = ref([]);
const fieldRows = ref([]);
const argRows = ref([]);
const doctypeFields = ref([]);

// Shim for frappe.query_report to support report JS scripts that use it
if (!window.frappe.query_report) {
	window.frappe.query_report = {
		get_filter_value: (name) => reportFilterValues[name] || "",
		set_filter_value: (name, val) => {
			reportFilterValues[name] = val;
			syncConfig();
		},
	};
}

const reportFilters = ref([]);
const reportFilterValues = reactive({});
const reportFilterTypes = reactive({});

function evaluateDependsOn(expression, values) {
	if (!expression) return true;
	if (typeof expression === "boolean") return expression;

	if (typeof expression === "string" && expression.startsWith("eval:")) {
		try {
			// Use new Function instead of direct eval for better performance and to satisfy bundlers
			const fn = new Function("doc", "values", `return ${expression.substring(5)}`);
			return fn(values, values);
		} catch (e) {
			return true;
		}
	} else if (typeof expression === "string") {
		return !!values[expression];
	}
	return true;
}

const visibleFilters = computed(() => {
	return reportFilters.value.filter((df) => {
		// Hide layout breaks and fields without labels
		if (!df.label || df.fieldtype?.includes("Break") || df.hidden) return false;

		// Evaluate depends_on if present
		if (df.depends_on) {
			return evaluateDependsOn(df.depends_on, reportFilterValues);
		}
		return true;
	});
});

function toggleReportFilterType(fieldname) {
	const current = reportFilterTypes[fieldname];
	const newState = current === "Expression" ? "Value" : "Expression";
	reportFilterTypes[fieldname] = newState;

	// Reset value to empty when switching to avoid weird state but keep logic
	if (newState === "Expression") {
		reportFilterValues[fieldname] = "{}";
	} else {
		reportFilterValues[fieldname] = "";
	}
	syncConfig();
}

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
		Object.keys(reportFilterTypes).forEach((k) => delete reportFilterTypes[k]);
		return;
	}
	try {
		loading.value = true;
		// 1. Try to get script and DB filters via desk API
		const res = await frappe.call({
			method: "frappe.desk.query_report.get_script",
			args: { report_name: reportName },
		});

		let filters = res.message?.filters || [];

		// Filter out breaks (Section Break, Column Break, etc.)
		filters = filters.filter((f) => !f.fieldtype?.includes("Break"));
		if (res.message?.script) {
			try {
				// Execute script to populate frappe.query_reports[reportName]
				frappe.dom.eval(res.message.script);

				// Wait for potential async registrations (frappe.after_ajax is often used internally)
				await new Promise((resolve) => setTimeout(resolve, 100));

				const reportSettings = frappe.query_reports[reportName] || {};
				if (reportSettings.filters && reportSettings.filters.length) {
					// Merge JS filters with DB filters, prioritizing JS
					const filterMap = new Map();
					filters.forEach((f) => filterMap.set(f.fieldname, f));
					reportSettings.filters.forEach((f) => filterMap.set(f.fieldname, f));
					filters = Array.from(filterMap.values());
				}
			} catch (e) {
				console.warn("Failed to extract filters from report script", e);
			}
		}

		// 3. Fallback: Check Report document directly if still empty
		if (!filters.length) {
			const report_doc = await frappe.db.get_doc("Report", reportName);
			if (report_doc.filters && report_doc.filters.length) {
				filters = report_doc.filters;
			} else if (report_doc.json) {
				try {
					const data = JSON.parse(report_doc.json);
					filters = data.filters || [];
				} catch (e) {}
			}
		}

		reportFilters.value = filters.map((f) => ({
			...f,
			fieldname: f.fieldname,
			fieldtype: f.fieldtype || "Data",
			label: f.label || f.fieldname,
		}));

		// Preserve existing values if they are already in config
		const existingFilters = config.filters || {};

		reportFilters.value.forEach((df) => {
			const val = existingFilters[df.fieldname];
			if (val !== undefined) {
				reportFilterValues[df.fieldname] = val;
				reportFilterTypes[df.fieldname] =
					parseValueType(val) === "Expression" ? "Expression" : "Value";
			} else {
				if (df.default !== undefined) {
					reportFilterValues[df.fieldname] = df.default;
				}
				reportFilterTypes[df.fieldname] = "Value";
			}
		});

		syncConfig();
	} catch (e) {
		console.error("Failed to load report filters", e);
		reportFilters.value = [];
	} finally {
		loading.value = false;
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
	() => props.node?.data?.reference_docname,
	(val) => {
		if (mode.value === "Query Report" && val) {
			loadReportFilters(val);
		}
	},
	{ immediate: true }
);

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

	try {
		testStatus.value = __("Running...");

		// Prepare overrides from current UI state
		const overrides = {
			operation: mode.value,
			reference_doctype: referenceDoctype.value,
			reference_docname: props.node.data.reference_docname,
			input_source: props.node.data.input_source,
			mutation_mode: props.node.data.mutation_mode,
			config: {
				...config,
			},
		};

		// For Query Report, ensure report_name is in config
		if (mode.value === "Query Report") {
			overrides.config.report_name = props.node.data.reference_docname || config.report_name;
			overrides.config.filters = { ...reportFilterValues };
		}

		const res = await frappe.call({
			method: "flexirule.ruleflow.api.test_action_query",
			args: {
				rule_name: store.rule_doc.name,
				action_id: props.node.data.action_id,
				overrides: overrides,
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

.row-item.report-filter-row {
	grid-template-columns: 140px 1fr;
	align-items: center;
	padding: 4px 10px;
	background: #fff;
	border-bottom: 1px solid #f1f5f9;
}

.filter-label-group {
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: space-between;
	padding-right: 8px;
}

.filter-label {
	font-size: 11px;
	font-weight: 600;
	margin: 0;
	color: #64748b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.filter-type-toggle .btn {
	padding: 0;
	opacity: 0.4;
}

.filter-type-toggle .btn.active {
	opacity: 1;
	color: var(--primary);
}

.filter-input-wrapper {
	width: 100%;
}

.expression-input-group {
	display: flex;
	align-items: center;
	background: #fff;
	border: 1px solid var(--primary);
	border-radius: 6px;
	padding: 0 8px;
	height: 30px;
}

.expr-prefix,
.expr-suffix {
	font-family: monospace;
	font-weight: 700;
	color: var(--primary);
	padding: 0 4px;
}

.border-dashed {
	border: 1px dashed #cbd5e1;
}

.extra-small {
	font-size: 10px;
}

.test-section {
	display: flex;
	align-items: center;
	gap: 8px;
}
</style>
