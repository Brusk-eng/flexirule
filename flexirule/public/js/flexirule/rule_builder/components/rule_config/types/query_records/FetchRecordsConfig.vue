<template>
	<div class="fetch-records-config">
		<div class="sub-section section-subcard" v-fxr-fieldname="'config.filters'">
			<div class="section-heading">
				<div>
					<h6>{{ __("Filters") }}</h6>
					<p class="section-description">
						{{
							__(
								"Build nested AND/OR filters. Groups are compiled as query criteria at runtime."
							)
						}}
					</p>
				</div>
			</div>
			<QueryFilterTree
				ref="filterTreeRef"
				:doctype="doctype"
				:modelValue="localConfig.filters || []"
				:readOnly="readOnly"
				:showValidation="showValidation"
				:nodeId="nodeId"
				:variableOptions="variableOptions"
				@update:modelValue="updateConfig('filters', $event)"
			/>
		</div>

		<div class="sub-section section-subcard">
			<div class="section-heading result-shape-heading">
				<div>
					<h6>{{ __("1. Result shape") }}</h6>
					<p class="section-description">
						{{
							__(
								"Choose the structure returned by Fetch Records. Output fields are configurable only for custom field shapes."
							)
						}}
					</p>
				</div>
			</div>
			<SelectControl
				fieldname="result_shape"
				:df="resultShapeField"
				:modelValue="localConfig.result_shape"
				:read_only="readOnly"
				:showValidation="showValidation"
				@update:modelValue="selectResultShape"
			/>
		</div>

		<div
			v-if="isCustomResultShape(localConfig.result_shape)"
			class="sub-section section-subcard"
		>
			<div class="section-heading">
				<div>
					<h6>{{ __("2. Output Fields") }}</h6>
					<p class="section-description">
						{{
							__(
								"Each row defines one output value. Fields, aliases, aggregate functions, and nested child selections are serialized into Frappe Query Builder field syntax."
							)
						}}
					</p>
				</div>
				<span class="output-fields-badge">{{ __("Syntax-aware editor") }}</span>
			</div>
			<OutputFieldsEditor
				ref="outputFieldsRef"
				:doctype="doctype"
				:modelValue="localConfig.fields || []"
				:shape="localConfig.result_shape"
				:groupBy="localConfig.group_by"
				:readOnly="readOnly"
				:showValidation="showValidation"
				@update:modelValue="updateConfig('fields', $event)"
			/>
		</div>
		<div class="sub-section section-subcard">
			<h6>{{ __("Order By") }}</h6>
			<div class="table-rows">
				<div v-for="(row, index) in orderRows" :key="row.id" class="order-row">
					<ComboBoxControl
						:df="{ label: '', fieldtype: 'FieldPicker' }"
						:options="navigableFields.currentFields.value"
						:doctype="doctype"
						:modelValue="row.field"
						:read_only="readOnly"
						:trigger="'button'"
						:hideLabel="true"
						:navigable="true"
						:navStack="navigableFields.navStack.value"
						@navigate="navigableFields.handleNavigate"
						@back="navigableFields.handleBack"
						class="flex-1"
						@update:modelValue="
							(value) => {
								row.field = value;
								navigableFields.resetStack();
								syncOrderBy();
							}
						"
					/>
					<select
						v-model="row.direction"
						class="form-control direction-select"
						:disabled="readOnly"
						@change="syncOrderBy"
					>
						<option value="asc">{{ __("ASC") }}</option>
						<option value="desc">{{ __("DESC") }}</option>
					</select>
					<button
						v-if="!readOnly"
						type="button"
						class="btn btn-xs btn-link text-danger remove-sort-btn"
						:title="__('Remove sort criteria')"
						@click="removeOrder(index)"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
				<button
					v-if="!readOnly"
					type="button"
					class="btn btn-xs btn-link p-0 text-primary align-self-start"
					@click="addOrder"
				>
					<i class="fa fa-plus mr-1"></i>{{ __("Add Sort Criteria") }}
				</button>
			</div>
		</div>

		<div class="sub-section section-subcard">
			<h6>{{ __("Retrieval Settings") }}</h6>
			<p class="section-description">
				{{ __("Choose how many matching rows to return. Large or unlimited result sets can increase query time and memory use.") }}
			</p>
			<div class="query-doc-grid">
				<div class="grid-item">
					<SelectControl
						:df="limitModeField"
						:modelValue="localConfig.limit_mode"
						:read_only="readOnly"
						:showValidation="showValidation"
						@update:modelValue="selectLimitMode"
					/>
				</div>
				<div v-if="localConfig.limit_mode === 'custom'" class="grid-item">
					<ControlFactory
						:df="limitField"
						:modelValue="localConfig.limit"
						:showValidation="showValidation"
						@update:modelValue="updateConfig('limit', $event)"
					/>
				</div>
				<div v-if="localConfig.limit_mode !== 'first_match'" class="grid-item">
					<ControlFactory
						:df="offsetField"
						:modelValue="localConfig.offset"
						:showValidation="showValidation"
						@update:modelValue="updateConfig('offset', $event)"
					/>
				</div>
				<div v-if="showGroupBy" class="grid-item">
					<ComboBoxControl
						:df="groupByField"
						:options="groupByNavigableFields.currentFields.value"
						:doctype="doctype"
						:modelValue="localConfig.group_by"
						:get_query="getGroupByOptions"
						:read_only="readOnly"
						:showValidation="showValidation"
						:showOnFocus="true"
						:navigable="true"
						:navStack="groupByNavigableFields.navStack.value"
						@navigate="groupByNavigableFields.handleNavigate"
						@back="groupByNavigableFields.handleBack"
						@update:modelValue="updateConfig('group_by', $event)"
					/>
				</div>
			</div>
			<ControlFactory
				:df="distinctField"
				:modelValue="localConfig.distinct"
				@update:modelValue="updateConfig('distinct', $event)"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import ControlFactory from "../../../../controls/ControlFactory.vue";
import ComboBoxControl from "../../../../controls/ComboBoxControl.vue";
import SelectControl from "../../../../controls/SelectControl.vue";
import { useNavigableFields } from "../../../../composables/useNavigableFields";
import QueryFilterTree from "../../query_filters/QueryFilterTree.vue";
import OutputFieldsEditor from "./OutputFieldsEditor.vue";
import {
	inferResultShape,
	isCustomResultShape,
	parseOutputFields,
	serializeOutputFields,
} from "./output_fields_model.js";

const props = defineProps({
	modelValue: { type: Object, default: () => ({}) },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
});

const emit = defineEmits(["update:modelValue", "change"]);
const filterTreeRef = ref(null);

const localConfig = reactive(normalizeConfig(props.modelValue));
const outputFieldsRef = ref(null);
function getEditableFieldDraft(value) {
	if (Array.isArray(value)) return clone(value);
	if (typeof value === "string" && value.trim() && value.trim() !== "*") {
		return serializeOutputFields(parseOutputFields(value));
	}
	return [];
}

const customFieldsDraft = ref({
	selected_fields:
		localConfig.result_shape === "selected_fields"
			? getEditableFieldDraft(localConfig.fields)
			: [],
	embedded_children:
		localConfig.result_shape === "embedded_children"
			? getEditableFieldDraft(localConfig.fields)
			: [],
});
const resultShapes = [
	{
		value: "document_names",
		label: __("Document names"),
		description: __("Return each matching record as a row containing only its document name."),
		icon: "fa fa-list-ol",
	},
	{
		value: "whole_documents",
		label: __("Whole documents"),
		description: __("Return every field from each parent document. Use this when downstream steps need the full record."),
		icon: "fa fa-file-text-o",
	},
	{
		value: "selected_fields",
		label: __("Selected fields"),
		description: __("Return only the fields you select, with optional aliases and supported aggregate functions."),
		icon: "fa fa-columns",
	},
	{
		value: "embedded_children",
		label: __("Embedded children"),
		description: __("Return selected child-table fields as nested arrays inside each parent result."),
		icon: "fa fa-sitemap",
	},
];
const limitModes = [
	{
		value: "first_match",
		label: __("First match (1 record)"),
		description: __("Return only the first matching record."),
		icon: "fa fa-bullseye",
	},
	{
		value: "first_20",
		label: __("First 20 records"),
		description: __("Return up to the first 20 matching records."),
		icon: "fa fa-list-ol",
	},
	{
		value: "first_1000",
		label: __("First 1,000 records"),
		description: __("Return up to 1,000 matching records."),
		icon: "fa fa-list",
	},
	{
		value: "all",
		label: __("All matching records"),
		description: __("Do not apply a result limit. Large result sets may take longer and use more memory."),
		icon: "fa fa-infinity",
	},
	{
		value: "custom",
		label: __("Custom limit"),
		description: __("Set a specific maximum number of matching records."),
		icon: "fa fa-sliders",
	},
];
const orderRows = ref(parseOrderBy(localConfig.order_by));
const navigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => orderRows.value[0]?.field || ""
);
const currentGroupByPath = computed(() => {
	const parts = String(localConfig.group_by || "")
		.split(",")
		.map((part) => part.trim())
		.filter(Boolean);
	return parts[parts.length - 1] || "";
});
const groupByNavigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => currentGroupByPath.value
);
const outputFieldRows = computed(() => parseOutputFields(localConfig.fields));
const hasAggregateOutput = computed(() =>
	outputFieldRows.value.some((row) => row.kind === "function")
);
const hasRegularOutput = computed(() =>
	outputFieldRows.value.some((row) => ["field", "raw"].includes(row.kind))
);
const showGroupBy = computed(() => isCustomResultShape(localConfig.result_shape) && hasAggregateOutput.value);
const groupByRequired = computed(() => showGroupBy.value && hasRegularOutput.value && !String(localConfig.group_by || "").trim());

const resultShapeField = computed(() => ({
	fieldname: "result_shape",
	fieldtype: "Select",
	label: __("Result Shape"),
	reqd: 1,
	read_only: props.readOnly,
	options: resultShapes,
	description: resultShapes.find((option) => option.value === localConfig.result_shape)?.description || __("Choose the structure returned by Fetch Records."),
}));
const limitModeField = computed(() => ({
	fieldname: "limit_mode",
	fieldtype: "Select",
	label: __("Return Limit"),
	reqd: 1,
	read_only: props.readOnly,
	options: limitModes,
	description: limitModes.find((option) => option.value === localConfig.limit_mode)?.description || __("Choose how many matching rows to return."),
}));
const limitField = computed(() => ({
	fieldname: "limit",
	fieldtype: "Int",
	label: __("Custom Limit"),
	reqd: localConfig.limit_mode === "custom" ? 1 : 0,
	read_only: props.readOnly,
	description: __("Maximum number of matching records to return. Enter a non-negative integer or a supported dynamic value."),
}));

const offsetField = computed(() => ({
	fieldname: "offset",
	fieldtype: "Int",
	label: __("Offset"),
	reqd: 0,
	read_only: props.readOnly,
	description: __("Skip this many matching records before applying the selected limit. Hidden for First Match."),
}));
const groupByField = computed(() => ({
	fieldname: "group_by",
	fieldtype: "FieldPicker",
	label: __("Group By"),
	reqd: groupByRequired.value ? 1 : 0,
	read_only: props.readOnly,
	description: groupByRequired.value
		? __("Required when aggregate functions are mixed with regular output fields.")
		: __("Group aggregate results by one or more fields. Only available for custom field result shapes with aggregate functions."),
}));

const distinctField = computed(() => ({
	fieldname: "distinct",
	fieldtype: "Check",
	label: __("Deduplicate Rows (DISTINCT)"),
	read_only: props.readOnly,
	description: __("Return unique rows after joins and child-table traversal."),
}));

function normalizeConfig(value) {
	const source = value && typeof value === "object" ? value : {};
	return {
		...source,
		filters: source.filters || [],
		fields:
			typeof source.fields === "string"
				? source.fields
				: Array.isArray(source.fields)
				? source.fields
				: [],
		result_shape: inferResultShape(source.fields, source.result_shape),
		order_by: source.order_by || "",
		group_by: source.group_by || "",
		limit: source.limit ?? "",
		limit_mode: inferLimitMode(source),
		offset: source.offset ?? "",
		distinct: !!source.distinct,
	};
}

function inferLimitMode(source) {
	const knownModes = new Set(limitModes.map((option) => option.value));
	if (knownModes.has(source.limit_mode)) return source.limit_mode;

	const limit = source.limit;
	if (limit === null || limit === undefined || limit === "") return "all";
	if (typeof limit === "string" && (limit.trim().startsWith("{") || limit.trim().startsWith("@"))) {
		return "custom";
	}
	const numericLimit = Number(limit);
	if (!Number.isInteger(numericLimit) || numericLimit < 0) return "custom";
	if (numericLimit === 1) return "first_match";
	if (numericLimit === 20) return "first_20";
	if (numericLimit === 1000) return "first_1000";
	return "custom";
}

function clone(value) {
	return JSON.parse(JSON.stringify(value));
}

function parseOrderBy(value) {
	if (!value || typeof value !== "string") return [];
	return value
		.split(",")
		.map((part) => part.trim())
		.filter(Boolean)
		.map((part, index) => {
			const tokens = part.split(/\s+/);
			return {
				id: "sort-" + index + "-" + Math.random().toString(36).slice(2, 8),
				field: tokens[0] || "",
				direction: (tokens[1] || "asc").toLowerCase() === "desc" ? "desc" : "asc",
			};
		});
}

function syncOrderBy() {
	localConfig.order_by = orderRows.value
		.filter((row) => row.field)
		.map((row) => `${row.field} ${row.direction || "asc"}`)
		.join(", ");
	emitConfig();
}

function addOrder() {
	if (props.readOnly) return;
	orderRows.value.push({
		id: "sort-" + Date.now() + "-" + Math.random().toString(36).slice(2, 7),
		field: "",
		direction: "asc",
	});
}

function removeOrder(index) {
	if (props.readOnly) return;
	orderRows.value.splice(index, 1);
	syncOrderBy();
}

function getGroupByOptions() {
	const current = localConfig.group_by || "";
	const parts = current
		.split(",")
		.map((part) => part.trim())
		.filter(Boolean);
	const prefix = parts.length > 1 ? parts.slice(0, -1).join(", ") + ", " : "";
	return groupByNavigableFields.currentFields.value.map((field) => ({
		...field,
		label: prefix + field.label,
		value: prefix + field.value,
	}));
}

function updateConfig(key, value) {
	localConfig[key] = clone(value);
	if (key === "fields" && isCustomResultShape(localConfig.result_shape)) {
		customFieldsDraft.value[localConfig.result_shape] = getEditableFieldDraft(value);
	}
	emitConfig();
}

function selectLimitMode(mode) {
	if (props.readOnly || !limitModes.some((option) => option.value === mode)) return;
	localConfig.limit_mode = mode;
	switch (mode) {
		case "first_match":
			localConfig.limit = 1;
			localConfig.offset = "";
			break;
		case "first_20":
			localConfig.limit = 20;
			break;
		case "first_1000":
			localConfig.limit = 1000;
			break;
		case "all":
			localConfig.limit = "";
			break;
		case "custom":
			// Keep the previous numeric value as a useful starting point when switching to Custom.
			break;
		default:
			return;
	}
	emitConfig();
}

function selectResultShape(shape) {
	if (props.readOnly || shape === localConfig.result_shape) return;
	if (isCustomResultShape(localConfig.result_shape)) {
		customFieldsDraft.value[localConfig.result_shape] = getEditableFieldDraft(
			localConfig.fields
		);
	}

	localConfig.result_shape = shape;
	if (shape === "document_names") {
		localConfig.fields = ["name"];
		localConfig.group_by = "";
	} else if (shape === "whole_documents") {
		localConfig.fields = "*";
		localConfig.group_by = "";
	} else {
		const draft = customFieldsDraft.value[shape];
		localConfig.fields = Array.isArray(draft) ? clone(draft) : [];
		customFieldsDraft.value[shape] = clone(localConfig.fields);
	}
	// result_shape is UI metadata; the backend receives only the compiled fields argument.
	emitConfig();
}

function emitConfig() {
	const next = { ...clone(localConfig) };
	const filters = next.filters;
	const hasFilters = Array.isArray(filters)
		? filters.length > 0
		: !!(
				filters &&
				typeof filters === "object" &&
				(Array.isArray(filters.children) ? filters.children.length > 0 : true)
		  );
	if (!hasFilters) delete next.filters;
	if (!next.fields?.length) delete next.fields;
	if (!next.order_by) delete next.order_by;
	if (!next.group_by) delete next.group_by;
	if (next.limit === "" || next.limit === null || next.limit === undefined) delete next.limit;
	if (next.offset === "" || next.offset === null || next.offset === undefined) delete next.offset;
	if (!next.limit_mode) next.limit_mode = "all";
	if (!next.distinct) delete next.distinct;
	emit("update:modelValue", next);
	emit("change", next);
}

watch(
	() => props.modelValue,
	(value) => {
		const next = normalizeConfig(value);
		if (JSON.stringify(next) === JSON.stringify(localConfig)) return;
		Object.keys(localConfig).forEach((key) => delete localConfig[key]);
		Object.assign(localConfig, next);
		orderRows.value = parseOrderBy(next.order_by);
		if (isCustomResultShape(next.result_shape)) {
			customFieldsDraft.value[next.result_shape] = getEditableFieldDraft(next.fields);
		}
	},
	{ deep: true }
);

async function validate() {
	const result = (await filterTreeRef.value?.validate?.()) || { valid: true, errors: [] };
	const errors = [...(result.errors || [])];
	if (isCustomResultShape(localConfig.result_shape) && outputFieldsRef.value?.validate) {
		const outputResult = await outputFieldsRef.value.validate();
		if (!outputResult.valid) errors.push(...outputResult.errors);
	}

	if (!limitModes.some((option) => option.value === localConfig.limit_mode)) {
		errors.push(__("Choose a valid result limit option."));
	}
	if (localConfig.limit_mode === "custom") {
		const value = localConfig.limit;
		if (value === "" || value === null || value === undefined) {
			errors.push(__("Custom Limit is required when Return Limit is set to Custom."));
		} else if (
			typeof value !== "string" ||
			!(value.trim().startsWith("{") || value.trim().startsWith("@"))
		) {
			const parsed = Number(value);
			if (!Number.isInteger(parsed) || parsed < 0) {
				errors.push(__("Custom Limit must be a non-negative integer or a supported dynamic value."));
			}
		}
	}
	const offsetValue = localConfig.offset;
	if (localConfig.limit_mode !== "first_match" && offsetValue !== "" && offsetValue !== null && offsetValue !== undefined) {
		if (
			typeof offsetValue === "string" &&
			(offsetValue.trim().startsWith("{") || offsetValue.trim().startsWith("@"))
		) {
			// Dynamic offsets are checked again after server-side resolution.
		} else {
			const parsed = Number(offsetValue);
			if (!Number.isInteger(parsed) || parsed < 0) {
				errors.push(__("Offset must be a non-negative integer or a supported dynamic value."));
			}
		}
	}
	if (groupByRequired.value && !String(localConfig.group_by || "").trim()) {
		errors.push(__("Group By is required when aggregate functions are mixed with regular output fields."));
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.result-shape-heading {
	margin-bottom: var(--spacing-xs);
}
.result-shape-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: var(--spacing-sm);
}
.result-shape-card {
	display: flex;
	align-items: flex-start;
	gap: var(--spacing-sm);
	width: 100%;
	min-width: 0;
	min-height: 66px;
	padding: var(--spacing-md);
	text-align: left;
	color: var(--fxr-text, var(--text-color));
	background: var(--fxr-bg, var(--card-bg));
	border: 1px solid var(--fxr-border, var(--border-color));
	border-radius: var(--border-radius-md, 8px);
	transition: border-color 120ms ease, background-color 120ms ease;
}
.result-shape-card:hover:not(:disabled) {
	border-color: var(--fxr-accent, var(--primary));
}
.result-shape-card.is-selected {
	border-color: var(--fxr-accent, var(--primary));
	box-shadow: inset 0 0 0 1px var(--fxr-accent, var(--primary));
	background: var(--fxr-bg-subtle, var(--control-bg));
}
.result-shape-card:disabled {
	cursor: default;
	opacity: 0.85;
}
.result-shape-icon {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 24px;
	height: 24px;
	flex: 0 0 auto;
	color: var(--fxr-text-muted, var(--text-muted));
}
.result-shape-card.is-selected .result-shape-icon,
.result-shape-check {
	color: var(--fxr-accent, var(--primary));
}
.result-shape-copy {
	display: flex;
	flex-direction: column;
	gap: 3px;
	min-width: 0;
}
.result-shape-copy strong {
	font-size: var(--fxr-text-sm);
	font-weight: 600;
}
.result-shape-copy small {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted, var(--text-muted));
	line-height: 1.4;
}
.result-shape-check {
	margin-left: auto;
	flex: 0 0 auto;
	padding-top: 2px;
}
.output-fields-badge {
	flex: 0 0 auto;
	padding: 2px 7px;
	border-radius: 999px;
	background: var(--fxr-bg-subtle);
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-xs);
	white-space: nowrap;
}
@media (max-width: 600px) {
	.result-shape-grid {
		grid-template-columns: minmax(0, 1fr);
	}
	.output-fields-badge {
		display: none;
	}
}

.fetch-records-config {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.section-heading {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: var(--spacing-md);
}

.section-description {
	margin: 2px 0 0;
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
}

.table-rows {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

.order-row {
	display: flex;
	align-items: center;
	gap: var(--spacing-md);
	width: 100%;
}

.direction-select {
	width: 100px !important;
	flex-shrink: 0;
}

.remove-sort-btn {
	width: 32px;
	height: 32px;
	padding: 0;
	flex-shrink: 0;
}

.query-doc-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: var(--spacing-md);
	align-items: start;
}

.grid-item {
	min-width: 0;
}

:deep(.filter-group-wrapper) {
	margin: 0;
}
</style>
