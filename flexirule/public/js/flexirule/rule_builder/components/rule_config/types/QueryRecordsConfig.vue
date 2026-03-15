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
				@update:modelValue="update_mode"
			/>
		</div>

		<div v-if="mode === 'Query Report'" class="config-section section-card">
			<ControlFactory
				:df="with_read_only(reportLinkField)"
				:modelValue="props.node?.data?.reference_docname"
				@update:modelValue="(val) => on_select_report(val)"
			/>
		</div>

		<div v-if="!mode" class="alert alert-warning mt-3">
			{{ __("Select a query mode to configure its parameters.") }}
		</div>

		<div v-else class="config-section section-card">
			<template v-if="mode === 'Query List'">
				<div class="sub-section section-subcard">
					<ControlFactory
						:df="with_read_only(referenceDoctypeField)"
						:modelValue="props.node?.data?.reference_doctype"
						@update:modelValue="(val) => update_action_field('reference_doctype', val)"
					/>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
						:nodeId="node?.id"
						@update:modelValue="(val) => update_config_key('filters', val)"
					/>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Fields") }}</h6>
					<div class="table-rows">
						<div v-for="(row, idx) in field_rows" :key="idx" class="row-item field-row">
							<div class="field-picker-container">
								<FieldPickerControl
									:df="{ label: '' }"
									:fields="doctype_fields"
									:documentType="reference_doctype"
									:modelValue="row.field"
									:read_only="readOnly"
									:class="{
										'border-warning': !is_field_valid(
											row.field,
											doctype_fields
										),
									}"
									@update:modelValue="(val) => (row.field = val)"
								/>
								<i
									v-if="row.field && !is_field_valid(row.field, doctype_fields)"
									class="fa fa-warning text-warning field-warning-icon"
									:title="__('Field not found in DocType')"
								></i>
							</div>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger"
								@click="remove_field(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link" @click="add_field">
							<i class="fa fa-plus"></i> {{ __("Add Field") }}
						</button>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link text-primary"
							@click="show_field_selector = !show_field_selector"
						>
							<i class="fa fa-list"></i>
							{{
								show_field_selector
									? __("Hide Field Selector")
									: __("Select Fields")
							}}
						</button>
					</div>

					<!-- Inline Field Selector -->
					<div
						v-if="show_field_selector"
						class="field-selector-inline mt-2 p-2 border rounded bg-white"
					>
						<div class="d-flex align-items-center mb-2 gap-2">
							<input
								type="text"
								class="form-control input-xs"
								:placeholder="__('Search fields...')"
								v-model="field_search_query"
							/>
							<button
								class="btn btn-xs btn-default"
								@click="toggle_all_visible_fields"
							>
								{{
									is_all_visible_selected ? __("Unselect All") : __("Select All")
								}}
							</button>
						</div>
						<div
							class="fields-list-scrollable"
							style="max-height: 250px; overflow-y: auto"
						>
							<div
								v-for="f in filtered_selector_fields"
								:key="f.value"
								class="field-option-item d-flex align-items-center p-1"
							>
								<input
									type="checkbox"
									:checked="is_field_selected(f.value)"
									@change="toggle_field_selection(f.value)"
									class="mr-2"
								/>
								<span class="small">{{ f.label }}</span>
								<span class="extra-small text-muted ml-1">({{ f.value }})</span>
							</div>
							<div
								v-if="!filtered_selector_fields.length"
								class="text-center p-2 text-muted small"
							>
								{{ __("No fields found") }}
							</div>
						</div>
					</div>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Order By") }}</h6>
					<div class="table-rows">
						<div
							v-for="(row, idx) in order_by_rows"
							:key="idx"
							class="row-item field-row"
						>
							<FieldPickerControl
								:df="{ label: '' }"
								:fields="doctype_fields"
								:documentType="reference_doctype"
								:modelValue="row.field"
								:read_only="readOnly"
								class="flex-1"
								:class="{
									'border-warning':
										row.field && !is_field_valid(row.field, doctype_fields),
								}"
								@update:modelValue="(val) => (row.field = val)"
							/>
							<select
								class="form-control input-xs ml-2"
								style="width: 80px"
								v-model="row.direction"
								:disabled="readOnly"
							>
								<option value="asc">{{ __("ASC") }}</option>
								<option value="desc">{{ __("DESC") }}</option>
							</select>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger"
								@click="remove_order_by(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link" @click="add_order_by">
							<i class="fa fa-plus"></i> {{ __("Add Sort Criteria") }}
						</button>
					</div>
				</div>

				<div class="sub-section section-subcard">
					<ControlFactory
						:df="with_read_only(limitField)"
						:modelValue="config.limit"
						@update:modelValue="(val) => update_config_key('limit', val)"
					/>
					<div class="sub-section">
						<label class="control-label small">{{ __("Group By") }}</label>
						<AutocompleteControl
							:df="{ label: '', fieldtype: 'Autocomplete' }"
							:modelValue="config.group_by"
							:get_options="get_group_by_options"
							:read_only="readOnly"
							:showOnFocus="true"
							@update:modelValue="update_config_key('group_by', $event)"
						/>
					</div>
				</div>
			</template>

			<template v-else-if="mode === 'Query Doc'">
				<ControlFactory
					:df="with_read_only(docnameField)"
					:modelValue="config.docname"
					@update:modelValue="(val) => update_config_key('docname', val)"
				/>
				<ControlFactory
					:df="with_read_only(docnameExprField)"
					:modelValue="config.docname_expression"
					@update:modelValue="(val) => update_config_key('docname_expression', val)"
				/>
			</template>

			<template v-else-if="mode === 'Exist Record'">
				<div class="sub-section section-subcard">
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
						:nodeId="node?.id"
						@update:modelValue="(val) => update_config_key('filters', val)"
					/>
				</div>
			</template>

			<template v-else-if="mode === 'Query Report'">
				<div v-if="report_filters.length || loading" class="sub-section">
					<div class="section-header">
						<h6>{{ __("Report Filters") }}</h6>
						<div
							v-if="loading"
							class="spinner-border spinner-border-sm text-muted"
						></div>
					</div>
					<div class="table-rows report-filter-table">
						<div
							v-for="df in visible_filters"
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
												report_filter_types[df.fieldname] === 'Expression',
										}"
										@click="toggle_report_filter_type(df.fieldname)"
										:title="__('Toggle Expression')"
									>
										<span class="extra-small font-weight-bold">{{
											report_filter_types[df.fieldname] === "Expression"
												? "{ }"
												: "abc"
										}}</span>
									</button>
								</div>
							</div>

							<div class="filter-input-wrapper">
								<template v-if="report_filter_types[df.fieldname] === 'Expression'">
									<div class="expression-input-group">
										<span class="expr-prefix">{</span>
										<AutocompleteControl
											:df="{
												fieldtype: 'Autocomplete',
												label: '',
												read_only: readOnly,
											}"
											:modelValue="
												strip_expression(report_filter_values[df.fieldname])
											"
											:get_options="get_variable_options"
											:placeholder="__('variable')"
											:read_only="readOnly"
											@update:modelValue="
												report_filter_values[df.fieldname] = `{${$event}}`;
												sync_local_config();
											"
										/>
										<span class="expr-suffix">}</span>
									</div>
								</template>
								<template v-else>
									<ControlFactory
										:df="{ ...with_read_only(df), label: '' }"
										:modelValue="report_filter_values[df.fieldname]"
										@update:modelValue="
											update_report_filter(df.fieldname, $event)
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
					:df="with_read_only(methodField)"
					:modelValue="config.method"
					@update:modelValue="(val) => update_config_key('method', val)"
				/>
				<div class="sub-section section-subcard">
					<h6>{{ __("Arguments") }}</h6>
					<div class="table-rows">
						<div v-for="(row, idx) in arg_rows" :key="idx" class="row-item">
							<input
								class="form-control input-xs"
								v-model="row.key"
								:placeholder="__('Key')"
								:disabled="readOnly"
								@change="sync_local_config"
							/>
							<input
								class="form-control input-xs"
								v-model="row.value"
								:placeholder="__('Value')"
								:disabled="readOnly"
								@change="sync_local_config"
							/>
							<select
								class="form-control input-xs"
								v-model="row.value_type"
								:disabled="readOnly"
								@change="sync_local_config"
							>
								<option v-for="vt in value_types" :key="vt" :value="vt">
									{{ __(vt) }}
								</option>
							</select>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger"
								@click="remove_arg(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link" @click="add_arg">
							<i class="fa fa-plus"></i> {{ __("Add Argument") }}
						</button>
					</div>
				</div>
			</template>
		</div>

		<div class="config-section section-card test-section">
			<button
				class="btn btn-xs btn-primary shadow-sm"
				@click="test_query"
				:disabled="readOnly"
			>
				<i class="fa fa-flask mr-1"></i> {{ __("Refresh Schema (Test Query)") }}
			</button>
			<span v-if="test_status" class="ml-2 text-muted font-weight-bold">{{
				test_status
			}}</span>
		</div>
	</div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import AutocompleteControl from "../../../controls/AutocompleteControl.vue";
import FieldPickerControl from "../../../controls/FieldPickerControl.vue";
import FilterGroup from "../FilterGroup.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const {
	store,
	config,
	docMeta,
	doctype_fields,
	variable_options,
	loading,
	mode,
	reference_doctype,
	with_read_only,
	loadDocMeta,
	load_doctype_fields,
	strip_expression,
	encode_value,
	parse_value_type,
	sync_config,
	is_field_valid,
	refresh_variables,
} = useActionConfig(props);

const test_status = ref("");

// Initialize local config
onMounted(async () => {
	load_local_config(props.node?.data?.config);
	if (reference_doctype.value) {
		await loadDocMeta(reference_doctype.value);
	}
	await refresh_variables();
	update_resolved_schema();
});

// Watch for external config changes
watch(
	() => props.node?.data?.config,
	(val) => load_local_config(val)
);

// Watch for doctype changes to reload meta
watch(
	() => reference_doctype.value,
	async (val) => {
		if (val) {
			await loadDocMeta(val);
			await load_doctype_fields(val);
			sync_local_config();
		}
	}
);

// Sync local config changes back to node
watch(
	() => config,
	(val) => sync_config({ ...val }),
	{ deep: true }
);

const field_rows = ref([]);
const order_by_rows = ref([]);
const arg_rows = ref([]);

const show_field_selector = ref(false);
const field_search_query = ref("");

const filtered_selector_fields = computed(() => {
	const query = field_search_query.value.toLowerCase();
	return doctype_fields.value.filter(
		(f) => f.label.toLowerCase().includes(query) || f.value.toLowerCase().includes(query)
	);
});

const is_all_visible_selected = computed(() => {
	if (!filtered_selector_fields.value.length) return false;
	return filtered_selector_fields.value.every((f) => is_field_selected(f.value));
});

function is_field_selected(f) {
	return field_rows.value.some((r) => r.field === f);
}

function toggle_field_selection(f) {
	const idx = field_rows.value.findIndex((r) => r.field === f);
	if (idx > -1) {
		field_rows.value.splice(idx, 1);
	} else {
		field_rows.value.push({ field: f });
	}
	sync_local_config();
}

function toggle_all_visible_fields() {
	const select = !is_all_visible_selected.value;
	filtered_selector_fields.value.forEach((f) => {
		const selected = is_field_selected(f.value);
		if (select && !selected) {
			field_rows.value.push({ field: f.value });
		} else if (!select && selected) {
			const idx = field_rows.value.findIndex((r) => r.field === f.value);
			if (idx > -1) field_rows.value.splice(idx, 1);
		}
	});
	sync_local_config();
}

// Shim for frappe.query_report to support report JS scripts that use it
if (!window.frappe.query_report) {
	window.frappe.query_report = {
		get_filter_value: (name) => report_filter_values[name] || "",
		set_filter_value: (name, val) => {
			report_filter_values[name] = val;
			sync_local_config();
		},
	};
}

const report_filters = ref([]);
const report_filter_values = reactive({});
const report_filter_types = reactive({});

function evaluate_depends_on(expression, values) {
	if (!expression) return true;
	if (typeof expression === "boolean") return expression;

	if (typeof expression === "string" && expression.startsWith("eval:")) {
		try {
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

const visible_filters = computed(() => {
	return report_filters.value.filter((df) => {
		if (!df.label || df.fieldtype?.includes("Break") || df.hidden) return false;
		if (df.depends_on) {
			return evaluate_depends_on(df.depends_on, report_filter_values);
		}
		return true;
	});
});

function toggle_report_filter_type(fieldname) {
	const current = report_filter_types[fieldname];
	const new_state = current === "Expression" ? "Value" : "Expression";
	report_filter_types[fieldname] = new_state;

	if (new_state === "Expression") {
		report_filter_values[fieldname] = "{}";
	} else {
		report_filter_values[fieldname] = "";
	}
	sync_local_config();
}

const SYSTEM_FIELDS = [
	{ fieldname: "name", label: __("ID (name)"), fieldtype: "Data" },
	{ fieldname: "owner", label: __("Created By (owner)"), fieldtype: "Link", options: "User" },
	{ fieldname: "creation", label: __("Created On (creation)"), fieldtype: "Datetime" },
	{ fieldname: "modified", label: __("Modified On (modified)"), fieldtype: "Datetime" },
	{
		fieldname: "modified_by",
		label: __("Modified By (modified_by)"),
		fieldtype: "Link",
		options: "User",
	},
	{ fieldname: "docstatus", label: __("Document Status (docstatus)"), fieldtype: "Int" },
];

async function update_resolved_schema() {
	if (!props.node?.data) return;

	if (mode.value === "Query List" || mode.value === "Query Doc") {
		const fields = field_rows.value.map((r) => r.field).filter((f) => f);
		if (!fields.length) {
			props.node.data.resolved_output_schema = [];
			return;
		}

		const schema = [];
		const meta = await flexirule.utils.get_doctype_meta(reference_doctype.value);
		if (!meta) return;

		for (const f of fields) {
			if (f.includes(".")) {
				const [table, field] = f.split(".");
				const table_df = meta.fields.find((d) => d.fieldname === table);
				if (table_df && table_df.options) {
					const child_meta = await flexirule.utils.get_doctype_meta(table_df.options);
					const df =
						child_meta.fields.find((d) => d.fieldname === field) ||
						SYSTEM_FIELDS.find((sf) => sf.fieldname === field);
					if (df) {
						schema.push({
							label: `${table_df.label}: ${df.label}`,
							fieldname: f,
							fieldtype: df.fieldtype,
							options: df.options,
						});
					}
				}
			} else {
				const df =
					meta.fields.find((d) => d.fieldname === f) ||
					SYSTEM_FIELDS.find((sf) => sf.fieldname === f);
				if (df) {
					if (["Table", "Table MultiSelect"].includes(df.fieldtype) && df.options) {
						// Expand child table fields
						const child_meta = await flexirule.utils.get_doctype_meta(df.options);
						if (child_meta) {
							child_meta.fields.forEach((cf) => {
								if (!frappe.model.no_value_type.includes(cf.fieldtype)) {
									schema.push({
										label: `${df.label}: ${cf.label}`,
										fieldname: `${df.fieldname}.${cf.fieldname}`,
										fieldtype: cf.fieldtype,
										options: cf.options,
									});
								}
							});
						}
					} else {
						schema.push({
							label: df.label,
							fieldname: f,
							fieldtype: df.fieldtype,
							options: df.options,
						});
					}
				}
			}
		}

		props.node.data.resolved_output_schema = schema;
		store.mark_dirty();
	} else if (mode.value === "Query Report" && props.node?.data?.reference_docname) {
		await update_report_columns();
	}
}

async function update_report_columns() {
	if (mode.value !== "Query Report" || !props.node?.data?.reference_docname) return;

	try {
		const report_name = props.node.data.reference_docname;
		const res = await frappe.call({
			method: "frappe.desk.query_report.run",
			args: {
				report_name: report_name,
				filters: report_filter_values,
				are_default_filters: false,
			},
		});

		if (res.message && res.message.columns) {
			const schema = res.message.columns.map((c) => {
				if (typeof c === "string") {
					const parts = c.split(":");
					let fieldtype = parts[1] || "Data";
					let options = parts[2];

					if (fieldtype.includes("/")) {
						[fieldtype, options] = fieldtype.split("/");
					}

					return {
						label: parts[0],
						fieldname: parts[0],
						fieldtype: fieldtype,
						options: options,
					};
				}
				return {
					label: c.label || c.fieldname,
					fieldname: c.fieldname,
					fieldtype: c.fieldtype || "Data",
					options: c.options,
				};
			});
			props.node.data.resolved_output_schema = schema;
			store.mark_dirty();
		}
	} catch (e) {
		console.warn("Failed to update report columns", e);
	}
}

const operators = ["=", "!=", ">", ">=", "<", "<=", "in", "not in"];

const modeField = computed(() => ({
	fieldname: "operation",
	fieldtype: "Select",
	label: __("Mode"),
	options: "Query List\nQuery Doc\nExist Record\nQuery Report\nQuery API",
	read_only: props.readOnly,
}));

const reportLinkField = computed(() => ({
	fieldname: "reference_docname",
	fieldtype: "Link",
	label: __("Report"),
	options: "Report",
	read_only: props.readOnly,
}));

const referenceDoctypeField = computed(() => ({
	fieldname: "reference_doctype",
	fieldtype: "Link",
	label: __("Reference DocType"),
	options: "DocType",
	default: store.rule_doc?.document_type,
	read_only: props.readOnly,
}));

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

function update_mode(value) {
	if (!props.node?.data) return;
	props.node.data.operation = value;
	if (value === "Query Report") {
		props.node.data.reference_doctype = "Report";
	}
	store.mark_dirty();
}

async function on_select_report(val) {
	if (!props.node?.data) return;
	props.node.data.reference_doctype = "Report";
	props.node.data.reference_docname = val;
	store.mark_dirty();
	// Clear metadata when switching to report
	docMeta.value = null;
	await load_report_filters(val);
}

function update_config_key(key, value) {
	config[key] = value;
	sync_local_config();
}

function add_field() {
	field_rows.value.push({ field: "" });
}

function add_order_by() {
	order_by_rows.value.push({ field: "", direction: "asc" });
}

function remove_order_by(idx) {
	order_by_rows.value.splice(idx, 1);
	sync_local_config();
}

function remove_field(idx) {
	field_rows.value.splice(idx, 1);
	sync_local_config();
}

function add_arg() {
	arg_rows.value.push({ key: "", value: "", value_type: "Value" });
}

function remove_arg(idx) {
	arg_rows.value.splice(idx, 1);
	sync_local_config();
}

function build_fields() {
	return field_rows.value.map((r) => r.field).filter((f) => f);
}

function build_args() {
	const args = {};
	arg_rows.value.forEach((row) => {
		if (!row.key) return;
		args[row.key] = encode_value(row);
	});
	return args;
}

function get_order_by_options() {
	return doctype_fields.value.map((f) => ({ label: f.label, value: f.value }));
}

function get_group_by_options() {
	const current = config.group_by || "";
	const parts = current.split(",").map((p) => p.trim());
	// const last_part = parts[parts.length - 1]; // not used yet but good for logic
	const prefix = parts.length > 1 ? parts.slice(0, -1).join(", ") + ", " : "";

	return doctype_fields.value.map((f) => ({
		label: `${prefix}${f.label}`,
		value: `${prefix}${f.value}`,
	}));
}

function build_order_by() {
	return order_by_rows.value
		.filter((r) => r.field)
		.map((r) => `${r.field} ${r.direction || "asc"}`)
		.join(", ");
}

function sync_local_config() {
	const new_config = {};
	Object.keys(config).forEach((k) => {
		const val = config[k];
		if (val !== undefined && val !== null && val !== "") new_config[k] = val;
	});

	if (mode.value === "Query List") {
		const fields = build_fields();
		if (fields.length) new_config.fields = fields;

		const order_by = build_order_by();
		if (order_by) new_config.order_by = order_by;
	}

	if (mode.value === "Query API") {
		const args = build_args();
		if (Object.keys(args).length) new_config.args = args;
	}

	if (mode.value === "Query Report") {
		const report_name = props.node?.data?.reference_docname || config.report_name;
		if (report_name) new_config.report_name = report_name;
		const filters = { ...report_filter_values };
		if (Object.keys(filters).length) new_config.filters = filters;
	}

	sync_config(new_config);
}

async function load_report_filters(report_name) {
	if (!report_name || mode.value !== "Query Report") {
		report_filters.value = [];
		Object.keys(report_filter_values).forEach((k) => delete report_filter_values[k]);
		Object.keys(report_filter_types).forEach((k) => delete report_filter_types[k]);
		return;
	}
	try {
		loading.value = true;
		const res = await frappe.call({
			method: "frappe.desk.query_report.get_script",
			args: { report_name: report_name },
		});

		let filters = res.message?.filters || [];
		filters = filters.filter((f) => !f.fieldtype?.includes("Break"));

		if (res.message?.script) {
			try {
				frappe.dom.eval(res.message.script);
				await new Promise((resolve) => setTimeout(resolve, 100));
				const settings = frappe.query_reports[report_name] || {};
				if (settings.filters && settings.filters.length) {
					const map = new Map();
					filters.forEach((f) => map.set(f.fieldname, f));
					settings.filters.forEach((f) => map.set(f.fieldname, f));
					filters = Array.from(map.values());
				}
			} catch (e) {
				console.warn("Failed to extract filters from report script", e);
			}
		}

		if (!filters.length) {
			const report_doc = await frappe.db.get_doc("Report", report_name);
			if (report_doc.filters && report_doc.filters.length) {
				filters = report_doc.filters;
			} else if (report_doc.json) {
				try {
					const data = JSON.parse(report_doc.json);
					filters = data.filters || [];
				} catch (e) {}
			}
		}

		report_filters.value = filters.map((f) => ({
			...f,
			fieldname: f.fieldname,
			fieldtype: f.fieldtype || "Data",
			label: f.label || f.fieldname,
		}));

		const cfg = props.node?.data?.config || {};
		const saved_filters = cfg.filters || {};
		report_filters.value.forEach((f) => {
			if (saved_filters[f.fieldname] !== undefined) {
				const val = saved_filters[f.fieldname];
				report_filter_values[f.fieldname] = val;
				report_filter_types[f.fieldname] = parse_value_type(val);
			} else {
				report_filter_values[f.fieldname] = f.default || "";
				report_filter_types[f.fieldname] = "Value";
			}
		});
	} catch (e) {
		console.error("Failed to load report filters", e);
	} finally {
		loading.value = false;
	}
}

function update_report_filter(fieldname, value) {
	report_filter_values[fieldname] = value;
	report_filter_types[fieldname] = parse_value_type(value);
	sync_local_config();
}

async function test_query() {
	if (!props.node?.data) return;
	test_status.value = __("Testing...");
	try {
		const res = await frappe.call({
			method: "flexirule.ruleflow.api.test_action_query",
			args: {
				rule_name: store.rule.name,
				action_id: props.node.id,
				overrides: props.node.data,
			},
		});
		if (res.message) {
			props.node.data.resolved_output_schema = res.message.schema || [];
			test_status.value = __("Success");
			store.mark_dirty();
		}
	} catch (e) {
		test_status.value = __("Failed");
	}
}

function get_variable_options() {
	return variable_options.value;
}

function load_local_config(val) {
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

	if (!config.filters) {
		config.filters = mode.value === "Query Report" ? {} : [];
	}
	if (!config.limit && mode.value === "Query List") config.limit = 20;

	if (mode.value === "Query Report") {
		const r_filters = parsed.filters || {};
		Object.entries(r_filters).forEach(([k, v]) => {
			report_filter_values[k] = v;
			report_filter_types[k] = parse_value_type(v);
		});
	}

	const fields = parsed.fields || [];
	field_rows.value = Array.isArray(fields) ? fields.map((f) => ({ field: f })) : [];

	const order_by = parsed.order_by || "";
	if (order_by) {
		order_by_rows.value = order_by.split(",").map((s) => {
			const parts = s.trim().split(/\s+/);
			return {
				field: parts[0],
				direction: (parts[1] || "asc").toLowerCase(),
			};
		});
	} else {
		order_by_rows.value = [];
	}

	const args = parsed.args || {};
	arg_rows.value = Object.entries(args).map(([key, value]) => ({
		key,
		value: strip_expression(value),
		value_type: parse_value_type(
			value,
			variable_options.value ? new Set(variable_options.value.map((v) => v.value)) : null
		),
	}));
}

watch(
	() => props.node?.data?.reference_docname,
	(val) => {
		if (mode.value === "Query Report" && val) {
			load_report_filters(val);
		}
	},
	{ immediate: true }
);

watch(
	() => [props.node?.data?.config, mode.value],
	([val]) => load_local_config(val),
	{ immediate: true }
);

watch(
	() => [field_rows.value, order_by_rows.value, arg_rows.value, config],
	() => {
		sync_local_config();
		update_resolved_schema();
	},
	{ deep: true }
);

watch(
	() => report_filter_values,
	() => {
		update_resolved_schema();
	},
	{ deep: true }
);

defineExpose({
	validate: () => ({ valid: true }),
});
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

.table-rows {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.row-item {
	display: grid;
	grid-template-columns: 1.4fr 0.8fr 1.6fr 0.8fr auto;
	gap: 6px;
	align-items: center;
}

.row-item.report-filter-row {
	grid-template-columns: 1fr 2fr;
	padding: 4px 0;
	border-bottom: 1px solid var(--border-color-beautified, #f4f5f6);
}

.filter-label-group {
	display: flex;
	align-items: center;
	gap: 8px;
}

.filter-label {
	margin: 0;
	font-size: 12px;
	color: var(--text-muted);
	font-weight: 500;
}

.expression-input-group {
	display: flex;
	align-items: center;
	background: #fff8e1;
	border-radius: 4px;
	padding: 0 8px;
	border: 1px solid #ffe082;
}

.expr-prefix,
.expr-suffix {
	font-weight: bold;
	color: #ffa000;
}
.field-picker-container {
	position: relative;
	flex: 1;
	display: flex;
	align-items: center;
}

.field-warning-icon {
	position: absolute;
	right: 30px;
	z-index: 5;
	pointer-events: all;
	cursor: help;
}

:deep(.border-warning .form-control) {
	border-color: var(--orange-500, #ff9800) !important;
	background-color: #fff8f1 !important;
}

.field-row {
	display: flex;
	align-items: center;
	gap: 8px;
}
</style>
