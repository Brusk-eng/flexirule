<template>
	<div class="output-fields-editor">
		<div v-if="!rows.length" class="output-fields-empty">
			<i class="fa fa-list-ul"></i>
			<span>{{
				__("No output fields yet. Add a field or child selection to get started.")
			}}</span>
		</div>

		<div class="output-fields-list">
			<div
				v-for="(row, index) in rows"
				:key="row.id"
				class="output-field-row"
				:class="{ 'is-editing': row.isEditing }"
			>
				<div class="output-field-row-heading">
					<div class="output-field-row-title">
						<span class="output-field-index">{{ index + 1 }}</span>
						<div class="output-field-row-copy">
							<strong :title="rowTitle(row)">{{ rowTitle(row) }}</strong>
							<p :title="rowDescription(row)">{{ rowDescription(row) }}</p>
						</div>
					</div>

					<div class="output-field-row-actions">
						<button
							v-if="!readOnly"
							type="button"
							class="output-field-action"
							:class="{ 'is-active': row.isEditing }"
							:title="
								row.isEditing
									? __('Finish editing output field')
									: __('Edit output field')
							"
							:aria-label="
								row.isEditing
									? __('Finish editing output field')
									: __('Edit output field')
							"
							:aria-expanded="String(row.isEditing)"
							@click="toggleEdit(row)"
						>
							<i :class="row.isEditing ? 'fa fa-check' : 'fa fa-pencil'"></i>
						</button>
						<button
							v-if="!readOnly"
							type="button"
							class="output-field-action"
							:disabled="index === 0"
							:title="__('Move output field up')"
							:aria-label="__('Move output field up')"
							@click="moveRow(index, -1)"
						>
							<i class="fa fa-chevron-up"></i>
						</button>
						<button
							v-if="!readOnly"
							type="button"
							class="output-field-action"
							:disabled="index === rows.length - 1"
							:title="__('Move output field down')"
							:aria-label="__('Move output field down')"
							@click="moveRow(index, 1)"
						>
							<i class="fa fa-chevron-down"></i>
						</button>
						<button
							v-if="!readOnly"
							type="button"
							class="output-field-action is-danger"
							:title="__('Remove output field')"
							:aria-label="__('Remove output field')"
							@click="removeRow(index)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>

				<div v-if="row.isEditing" class="output-field-edit">
					<div v-if="row.kind === 'field'" class="output-field-controls">
						<OutputFieldPicker
							:doctype="doctype"
							:modelValue="row.field"
							:readOnly="readOnly"
							:label="__('Field')"
							@update:modelValue="updateRowValue(row, 'field', $event)"
						/>
						<input
							class="form-control output-field-alias"
							:value="row.alias"
							:disabled="readOnly"
							:placeholder="__('Output alias (optional)')"
							:aria-label="__('Output alias (optional)')"
							@input="normalizeAlias(row, $event.target.value)"
						/>
					</div>

					<div
						v-else-if="row.kind === 'function'"
						class="output-field-controls output-function-controls"
					>
						<SelectControl
							class="form-control output-function-select"
							:df="{
								fieldtype: 'Select',
								label: '',
								options: aggregateFunctions,
								reqd: 1,
							}"
							:modelValue="row.functionName"
							:read_only="readOnly"
							:hideLabel="true"
							:aria-label="__('Aggregate function')"
							@update:modelValue="
								(value) => updateRowValue(row, 'functionName', value)
							"
						/>
						<OutputFieldPicker
							:doctype="doctype"
							:modelValue="row.field"
							:readOnly="readOnly"
							:rootOnly="true"
							:label="__('Source field')"
							@update:modelValue="updateRowValue(row, 'field', $event)"
						/>
						<input
							class="form-control output-field-alias"
							:value="row.alias"
							:disabled="readOnly"
							:placeholder="__('Required output alias')"
							:aria-label="__('Required output alias')"
							@input="updateRowValue(row, 'alias', $event.target.value)"
						/>
					</div>

					<div v-else-if="row.kind === 'child'" class="output-child-controls">
						<div class="output-child-table">
							<label class="output-field-label">{{ __("Child table") }}</label>
							<SelectControl
								class="form-control"
								:df="{ fieldtype: 'Select', label: '', options: childTableOptions }"
								:modelValue="row.tableField"
								:read_only="readOnly"
								:hideLabel="true"
								@update:modelValue="(value) => changeChildTable(row, value)"
							/>
						</div>
						<div class="output-child-fields">
							<label class="output-field-label">{{ __("Child fields") }}</label>
							<MultiSelectList
								:df="{
									label: '',
									fieldname: 'child_fields',
									placeholder: __('Select child fields...'),
								}"
								:options="row.childFieldOptions || []"
								:modelValue="row.fields || []"
								:read_only="readOnly || !row.tableField"
								:hideLabel="true"
								@update:modelValue="updateRowValue(row, 'fields', $event)"
							/>
						</div>
					</div>

					<div v-else class="output-field-controls">
						<textarea
							class="form-control output-field-raw"
							:value="row.expression"
							:disabled="readOnly"
							:placeholder="
								__('Advanced native field expression or JSON field descriptor')
							"
							:aria-label="
								__('Advanced native field expression or JSON field descriptor')
							"
							rows="2"
							@input="updateRaw(row, $event.target.value)"
						></textarea>
					</div>
				</div>
			</div>
		</div>

		<div v-if="!readOnly" class="output-fields-add-actions">
			<button type="button" class="output-fields-add-btn" @click="addField">
				<i class="fa fa-plus"></i>{{ __("Add output field") }}
			</button>
			<button type="button" class="output-fields-add-btn" @click="addFunction">
				<i class="fa fa-calculator"></i>{{ __("Add function") }}
			</button>
			<button
				v-if="shape === 'embedded_children'"
				type="button"
				class="output-fields-add-btn"
				@click="addChild"
			>
				<i class="fa fa-sitemap"></i>{{ __("Add child selection") }}
			</button>
		</div>

		<p v-if="requiresGroupBy" class="output-fields-warning">
			<i class="fa fa-info-circle mr-1"></i>
			{{
				__(
					"When aggregates and regular fields are combined, set Group By in Result limit and grouping. Otherwise, use aggregate-only output fields."
				)
			}}
		</p>

		<p v-if="shape === 'embedded_children'" class="output-fields-hint">
			{{
				__(
					"Child selections return nested arrays for each parent record. Use dotted paths only when you want flat joined rows."
				)
			}}
		</p>
		<p class="output-fields-hint">
			{{
				__(
					"Functions use Frappe-style field syntax. Aggregate functions currently support fields on the selected DocType, not linked or child-table paths."
				)
			}}
		</p>

		<div v-if="showValidation && validationErrors.length" class="output-fields-errors">
			<div v-for="error in validationErrors" :key="error">
				<i class="fa fa-exclamation-circle mr-1"></i>{{ error }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import MultiSelectList from "../../../../controls/MultiSelectList.vue";
import SelectControl from "../../../../controls/SelectControl.vue";
import { useMetaStore } from "../../../../stores/useMetaStore";
import {
	AGGREGATE_FUNCTIONS,
	scrubOutputAlias,
	parseOutputFields,
	serializeOutputFields,
	validateOutputFields,
} from "./output_fields_model.js";
import OutputFieldPicker from "./OutputFieldPicker.vue";

const props = defineProps({
	modelValue: { type: [Array, String], default: () => [] },
	doctype: { type: String, required: true },
	shape: { type: String, required: true },
	groupBy: { type: String, default: "" },
	readOnly: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);
const metaStore = useMetaStore();
const rows = ref(
	parseOutputFields(props.modelValue).map((row) => ({
		...row,
		isEditing: false,
		childFieldOptions: [],
	}))
);
const validationErrors = ref([]);
const requiresGroupBy = computed(
	() =>
		rows.value.some((row) => row.kind === "function") &&
		rows.value.some((row) => ["field", "raw"].includes(row.kind)) &&
		!String(props.groupBy || "").trim()
);
const aggregateFunctions = AGGREGATE_FUNCTIONS.map((value) => ({
	value,
	label: value.toUpperCase(),
}));

const parentFields = computed(() => metaStore.doc_meta[props.doctype] || []);
const childTableOptions = computed(() =>
	parentFields.value
		.filter(
			(field) => ["Table", "Table MultiSelect"].includes(field.fieldtype) && field.options
		)
		.map((field) => ({
			value: field.fieldname,
			label:
				(field.original_label || field.label || field.fieldname) +
				" (" +
				field.fieldname +
				")",
			doctype: field.options,
		}))
);

function newId() {
	return "output-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
}

function fieldInfo(fieldPath) {
	const path = String(fieldPath || "").trim();
	if (!path) return { label: "", fieldname: "" };
	const parts = path.split(".");
	const rootField = parentFields.value.find((field) => field.fieldname === parts[0]);
	if (parts.length > 1 && rootField?.options) {
		const relatedFields = metaStore.doc_meta[rootField.options] || [];
		const relatedField = relatedFields.find((field) => field.fieldname === parts[1]);
		if (relatedField) {
			return {
				...relatedField,
				label: (rootField.label || rootField.fieldname) + ": " +
					(relatedField.original_label || relatedField.label || relatedField.fieldname),
				fieldname: path,
			};
		}
	}
	if (rootField) return rootField;
	const systemLabels = {
		name: "ID (name)",
		owner: "Created By (owner)",
		creation: "Created On (creation)",
		modified: "Modified On (modified)",
		modified_by: "Modified By (modified_by)",
		docstatus: "Document Status (docstatus)",
	};
	return { fieldname: path, label: systemLabels[path] || path, fieldtype: "Data" };
}

function humanizeAlias(alias) {
	return String(alias || "")
		.split("_")
		.filter(Boolean)
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(" ");
}

function rowTitle(row) {
	if (row.kind === "field") {
		return fieldInfo(row.field).label || row.alias || row.field || __("Output field");
	}
	if (row.kind === "function") {
		const fn = (row.functionName || "count").toUpperCase();
		return row.alias ? humanizeAlias(row.alias) + " (" + fn + ")" : fn + "(" + (fieldInfo(row.field).label || row.field || "?") + ")";
	}
	if (row.kind === "child") {
		return fieldInfo(row.tableField).label || __("Embedded child selection");
	}
	return row.expression || __("Advanced field expression");
}

function rowDescription(row) {
	if (row.kind === "field") {
		const source = row.field
			? (row.field.includes(".") ? __("Related field") : __("Parent field")) +
			  " · " + (fieldInfo(row.field).label || row.field) + " (" + row.field + ")"
			: __("Choose a field");
		return row.alias ? source + " · " + __("Output alias") + ": " + row.alias : source;
	}
	if (row.kind === "function") {
		const fn = (row.functionName || "count").toUpperCase();
		const source = fieldInfo(row.field).label || row.field || "?";
		return __("Function") + " · " + fn + "(" + source + ")" +
			(row.field ? " (" + row.field + ")" : "") +
			(row.alias ? " · " + __("Output alias") + ": " + row.alias : "");
	}
	if (row.kind === "child") {
		const fields = Array.isArray(row.fields)
			? row.fields.map((field) => fieldInfo(row.tableField + "." + field).label || field).join(", ")
			: "";
		return fields ? __("Child fields") + " · " + fields : __("Select child fields");
	}
	return __("Advanced native field expression");
}

function toggleEdit(row) {
	if (props.readOnly) return;
	row.isEditing = !row.isEditing;
}

function emitRows() {
	validationErrors.value = [];
	emit("update:modelValue", serializeOutputFields(rows.value));
}

function updateRowValue(row, key, value) {
	if (props.readOnly) return;
	row[key] = key === "alias" ? scrubOutputAlias(value) : value;
	if (key === "field" && String(value || "").includes(".")) {
		ensureMetadataForPath(value);
	}
	emitRows();
}

function normalizeAlias(row, value) {
	if (props.readOnly) return;
	row.alias = scrubOutputAlias(value);
	emitRows();
}

async function ensureMetadataForPath(fieldPath) {
	const rootName = String(fieldPath || "").split(".")[0];
	const rootField = parentFields.value.find((field) => field.fieldname === rootName);
	if (!rootField?.options) return;
	try {
		await metaStore.fetch_metadata(rootField.options);
	} catch (error) {
		console.warn("OutputFieldsEditor: failed to load related field metadata", error);
	}
}

function updateRaw(row, value) {
	if (props.readOnly) return;
	row.expression = value;
	row.dirty = true;
	emitRows();
}

function addField() {
	if (props.readOnly) return;
	rows.value.push({
		id: newId(),
		kind: "field",
		field: "",
		alias: "",
		fields: [],
		isEditing: true,
		childFieldOptions: [],
	});
	emitRows();
}

function addFunction() {
	if (props.readOnly) return;
	rows.value.push({
		id: newId(),
		kind: "function",
		functionName: "count",
		field: "",
		alias: "",
		fields: [],
		isEditing: true,
		childFieldOptions: [],
	});
	emitRows();
}

function addChild() {
	if (props.readOnly) return;
	rows.value.push({
		id: newId(),
		kind: "child",
		tableField: "",
		fields: [],
		isEditing: true,
		childFieldOptions: [],
	});
	emitRows();
}

function removeRow(index) {
	if (props.readOnly) return;
	rows.value.splice(index, 1);
	emitRows();
}

function moveRow(index, direction) {
	if (props.readOnly) return;
	const nextIndex = index + direction;
	if (nextIndex < 0 || nextIndex >= rows.value.length) return;
	const [row] = rows.value.splice(index, 1);
	rows.value.splice(nextIndex, 0, row);
	emitRows();
}

async function loadChildFieldOptions(row, filterExisting = false) {
	const option = childTableOptions.value.find((item) => item.value === row.tableField);
	if (!option) {
		row.childFieldOptions = [];
		return;
	}
	try {
		await metaStore.fetch_metadata(option.doctype);
		const fields = metaStore.doc_meta[option.doctype] || [];
		row.childFieldOptions = fields
			.filter((field) => field.fieldname && !field.hidden)
			.map((field) => ({
				value: field.fieldname,
				label:
					(field.original_label || field.label || field.fieldname) +
					" (" +
					field.fieldname +
					")",
			}));
		if (filterExisting) {
			const allowed = new Set(row.childFieldOptions.map((field) => field.value));
			row.fields = (row.fields || []).filter((field) => allowed.has(field));
		}
	} catch (error) {
		console.warn("OutputFieldsEditor: failed to load child DocType fields", error);
		row.childFieldOptions = [];
	}
}

async function refreshMetadata() {
	if (!props.doctype) return;
	try {
		await metaStore.fetch_metadata(props.doctype);
		for (const row of rows.value) {
			if (row.kind === "child") {
				await loadChildFieldOptions(row);
				continue;
			}
			if (row.field && String(row.field).includes(".")) {
				await ensureMetadataForPath(row.field);
			}
		}
	} catch (error) {
		console.warn("OutputFieldsEditor: failed to load DocType fields", error);
	}
}

async function changeChildTable(row, tableField) {
	if (props.readOnly) return;
	row.tableField = tableField;
	row.fields = [];
	await loadChildFieldOptions(row);
	emitRows();
}

async function validate() {
	const errors = validateOutputFields(rows.value, props.shape, props.groupBy);
	for (const row of rows.value) {
		if (row.kind !== "child" || !row.tableField) continue;
		if (!childTableOptions.value.some((option) => option.value === row.tableField)) {
			errors.push("Child selection references a field that is not a child table.");
			continue;
		}
		if (
			row.fields.some(
				(field) => !row.childFieldOptions.some((option) => option.value === field)
			)
		) {
			errors.push(
				"Child selection contains a field that is not available in the selected child DocType."
			);
		}
	}
	validationErrors.value = errors;
	return { valid: errors.length === 0, errors };
}

watch(
	() => props.modelValue,
	(value) => {
		if (JSON.stringify(serializeOutputFields(rows.value)) === JSON.stringify(value)) return;
		rows.value = parseOutputFields(value).map((row) => ({
			...row,
			isEditing: false,
			childFieldOptions: [],
		}));
		refreshMetadata();
	},
	{ deep: true }
);
watch(() => props.doctype, refreshMetadata);
onMounted(refreshMetadata);
defineExpose({ validate });
</script>

<style scoped>
.output-fields-editor {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2, var(--spacing-xs));
	color: var(--fxr-text);
}

.output-fields-list {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	background: var(--fxr-surface);
	overflow: hidden;
}

.output-field-row {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2, var(--spacing-xs));
	padding: var(--fxr-space-3, var(--spacing-sm)) var(--fxr-space-4, var(--spacing-md));
	border-bottom: 1px solid var(--fxr-border-subtle);
	background: transparent;
	transition: background-color var(--fxr-transition-fast);
}

.output-field-row:last-child {
	border-bottom: 0;
}

.output-field-row.is-editing {
	background: var(--fxr-surface-soft);
}

.output-field-row-heading,
.output-field-row-title,
.output-field-row-actions {
	display: flex;
	align-items: center;
	min-width: 0;
}

.output-field-row-heading {
	justify-content: space-between;
	gap: var(--fxr-space-3, var(--spacing-sm));
	min-height: 28px;
}

.output-field-row-title {
	flex: 1;
	gap: var(--fxr-space-3, var(--spacing-sm));
	overflow: hidden;
}

.output-field-index {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 20px;
	height: 20px;
	flex: 0 0 20px;
	border-radius: var(--fxr-radius-sm, 4px);
	background: var(--fxr-surface-soft);
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-xs);
	font-weight: var(--fxr-weight-medium);
}

.output-field-row-copy {
	min-width: 0;
	flex: 1;
}

.output-field-row-copy strong {
	display: block;
	overflow: hidden;
	color: var(--fxr-text);
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-medium);
	text-overflow: ellipsis;
	white-space: nowrap;
}

.output-field-row-copy p {
	margin: 1px 0 0;
	overflow: hidden;
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-xs);
	line-height: 1.35;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.output-field-row-actions {
	flex: 0 0 auto;
	gap: var(--fxr-space-1, 4px);
}

.output-field-action {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 26px;
	height: 26px;
	padding: 0;
	border: 1px solid transparent;
	border-radius: var(--fxr-radius-sm, 4px);
	background: transparent;
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-xs);
	cursor: pointer;
	transition: color var(--fxr-transition-fast), background-color var(--fxr-transition-fast),
		border-color var(--fxr-transition-fast);
}

.output-field-action:hover:not(:disabled) {
	border-color: var(--fxr-border-subtle);
	background: var(--fxr-surface-soft);
	color: var(--fxr-text);
}

.output-field-action.is-active {
	border-color: var(--fxr-border-focus);
	background: var(--fxr-surface-soft);
	color: var(--fxr-accent);
}

.output-field-action.is-danger:hover:not(:disabled) {
	border-color: var(--fxr-border-danger, #ef4444);
	color: var(--fxr-text-danger, #ef4444);
}

.output-field-action:disabled {
	opacity: 0.35;
	cursor: default;
}

.output-field-edit {
	padding: var(--fxr-space-3, var(--spacing-sm)) 0 var(--fxr-space-2, var(--spacing-xs)) 32px;
}

.output-field-controls {
	display: grid;
	grid-template-columns: minmax(0, 2fr) minmax(130px, 1fr);
	gap: var(--fxr-space-2, var(--spacing-xs));
	align-items: start;
}

.output-function-controls {
	grid-template-columns: 76px minmax(0, 2fr) minmax(130px, 1fr);
}

.output-function-select,
.output-field-alias {
	min-width: 0;
}

.output-child-controls {
	display: grid;
	grid-template-columns: minmax(130px, 0.8fr) minmax(0, 1.2fr);
	gap: var(--fxr-space-3, var(--spacing-sm));
	align-items: start;
}

.output-child-table,
.output-child-fields {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-1, 4px);
	min-width: 0;
}

.output-field-label {
	margin: 0;
	color: var(--fxr-text-secondary);
	font-size: var(--fxr-text-xs);
	font-weight: var(--fxr-weight-medium);
}

.output-field-raw {
	min-width: 0;
	font-family: var(--font-mono);
	font-size: var(--fxr-text-sm);
}

.output-fields-empty {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-2, var(--spacing-xs));
	padding: var(--fxr-space-3, var(--spacing-sm));
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
}

.output-fields-add-actions {
	display: flex;
	flex-wrap: wrap;
	gap: var(--fxr-space-2, var(--spacing-xs));
	align-items: center;
	padding-top: var(--fxr-space-1, 4px);
}

.output-fields-add-btn {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-2, var(--spacing-xs));
	min-height: var(--fxr-input-height, 30px);
	padding: 0 var(--fxr-space-3, var(--spacing-sm));
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	background: var(--fxr-surface);
	color: var(--fxr-text-secondary);
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-medium);
	cursor: pointer;
	transition: background-color var(--fxr-transition-fast), border-color var(--fxr-transition-fast),
		color var(--fxr-transition-fast);
}

.output-fields-add-btn:hover {
	border-color: var(--fxr-border-focus);
	background: var(--fxr-surface-soft);
	color: var(--fxr-accent);
}

.output-fields-add-btn:focus-visible,
.output-field-action:focus-visible {
	outline: none;
	border-color: var(--fxr-border-focus);
	box-shadow: var(--fxr-shadow-focus);
}

.output-fields-hint,
.output-fields-warning {
	margin: 0;
	font-size: var(--fxr-text-xs);
	line-height: 1.4;
}

.output-fields-hint {
	color: var(--fxr-text-muted);
}

.output-fields-warning {
	color: var(--fxr-text-warning, #b45309);
}

.output-fields-errors {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-1, 4px);
	color: var(--fxr-text-danger, #ef4444);
	font-size: var(--fxr-text-xs);
}

:deep(.field-picker-control),
:deep(.control.frappe-control) {
	margin-bottom: 0 !important;
}

:deep(.form-control),
:deep(input.form-control),
:deep(select.form-control) {
	height: var(--fxr-input-height, 32px) !important;
	padding: var(--fxr-input-padding-y, 5px) var(--fxr-input-padding-x, 8px) !important;
	border: 1px solid var(--fxr-border) !important;
	border-radius: var(--fxr-radius-md) !important;
	background-color: var(--fxr-bg-input) !important;
	color: var(--fxr-text) !important;
	font-size: var(--fxr-input-font-size, var(--fxr-text-sm)) !important;
	transition: border-color var(--fxr-transition-fast), box-shadow var(--fxr-transition-fast);
}

:deep(.form-control:focus) {
	border-color: var(--fxr-border-focus) !important;
	box-shadow: var(--fxr-shadow-focus) !important;
}

@media (max-width: 700px) {
	.output-field-row {
		padding: var(--fxr-space-3, var(--spacing-sm));
	}

	.output-field-edit {
		padding-left: 0;
	}

	.output-field-controls,
	.output-function-controls,
	.output-child-controls {
		grid-template-columns: minmax(0, 1fr);
	}

	.output-field-row-actions {
		gap: 0;
	}
}
</style>
