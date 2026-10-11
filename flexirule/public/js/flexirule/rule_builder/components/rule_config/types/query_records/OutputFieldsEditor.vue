<template>
	<div class="output-fields-editor">
		<div v-if="!rows.length" class="output-fields-empty">
			<i class="fa fa-list-ul"></i>
			<span>{{ __("No output fields yet. Add a field or child selection to get started.") }}</span>
		</div>

		<div v-for="(row, index) in rows" :key="row.id" class="output-field-row">
			<div class="output-field-row-heading">
				<div class="output-field-row-title">
					<span class="output-field-index">{{ index + 1 }}</span>
					<div class="output-field-row-copy">
						<strong>{{ rowTitle(row) }}</strong>
						<p>{{ rowDescription(row) }}</p>
					</div>
				</div>
				<div class="output-field-row-actions">
					<button type="button" class="btn btn-xs btn-default" :disabled="readOnly || index === 0" :title="__('Move output field up')" :aria-label="__('Move output field up')" @click="moveRow(index, -1)">
						<i class="fa fa-arrow-up"></i>
					</button>
					<button type="button" class="btn btn-xs btn-default" :disabled="readOnly || index === rows.length - 1" :title="__('Move output field down')" :aria-label="__('Move output field down')" @click="moveRow(index, 1)">
						<i class="fa fa-arrow-down"></i>
					</button>
					<button type="button" class="btn btn-xs btn-link text-danger" :disabled="readOnly" :title="__('Remove output field')" :aria-label="__('Remove output field')" @click="removeRow(index)">
						<i class="fa fa-trash"></i>
					</button>
				</div>
			</div>

			<div v-if="row.kind === 'field'" class="output-field-controls">
				<OutputFieldPicker :doctype="doctype" :modelValue="row.field" :readOnly="readOnly" :label="__('Field')" @update:modelValue="updateRowValue(row, 'field', $event)" />
				<input class="form-control output-field-alias" :value="row.alias" :disabled="readOnly" :placeholder="__('Output alias (optional)')" :aria-label="__('Output alias (optional)')" @input="updateRowValue(row, 'alias', $event.target.value)" />
			</div>

			<div v-else-if="row.kind === 'function'" class="output-field-controls output-function-controls">
				<select class="form-control output-function-select" :value="row.functionName" :disabled="readOnly" :aria-label="__('Aggregate function')" @change="updateRowValue(row, 'functionName', $event.target.value)">
					<option v-for="fn in aggregateFunctions" :key="fn.value" :value="fn.value">{{ fn.label }}</option>
				</select>
				<OutputFieldPicker :doctype="doctype" :modelValue="row.field" :readOnly="readOnly" :rootOnly="true" :label="__('Source field')" @update:modelValue="updateRowValue(row, 'field', $event)" />
				<input class="form-control output-field-alias" :value="row.alias" :disabled="readOnly" :placeholder="__('Required output alias')" :aria-label="__('Required output alias')" @input="updateRowValue(row, 'alias', $event.target.value)" />
			</div>

			<div v-else-if="row.kind === 'child'" class="output-child-controls">
				<label class="output-field-label">{{ __("Child table") }}</label>
				<select class="form-control" :value="row.tableField" :disabled="readOnly" @change="changeChildTable(row, $event.target.value)">
					<option value="">{{ __("Select a child table...") }}</option>
					<option v-for="option in childTableOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
				</select>
				<label class="output-field-label">{{ __("Child fields") }}</label>
				<MultiSelectList
					:df="{ label: '', fieldname: 'child_fields', placeholder: __('Select child fields...') }"
					:options="row.childFieldOptions || []"
					:modelValue="row.fields || []"
					:read_only="readOnly || !row.tableField"
					:hideLabel="true"
					@update:modelValue="updateRowValue(row, 'fields', $event)"
				/>
			</div>

			<div v-else class="output-field-controls">
				<textarea class="form-control output-field-raw" :value="row.expression" :disabled="readOnly" :placeholder="__('Advanced native field expression or JSON field descriptor')" :aria-label="__('Advanced native field expression or JSON field descriptor')" rows="2" @input="updateRaw(row, $event.target.value)"></textarea>
			</div>
		</div>

		<div class="output-fields-add-actions" v-if="!readOnly">
			<button type="button" class="btn btn-xs btn-link p-0 text-primary" @click="addField"><i class="fa fa-plus-circle mr-1"></i>{{ __("Add output field") }}</button>
			<button type="button" class="btn btn-xs btn-link p-0 text-primary" @click="addFunction"><i class="fa fa-calculator mr-1"></i>{{ __("Add aggregate function") }}</button>
			<button v-if="shape === 'embedded_children'" type="button" class="btn btn-xs btn-link p-0 text-primary" @click="addChild"><i class="fa fa-sitemap mr-1"></i>{{ __("Add embedded child selection") }}</button>
		</div>

		<p v-if="shape === 'embedded_children'" class="output-fields-hint">
			{{ __("Child selections are serialized as nested arrays. Use dotted child paths only when you intentionally want flat joined rows.") }}
		</p>
		<p class="output-fields-hint">
			{{ __("Function expressions use native Frappe field syntax. Aggregate functions over child/link paths are not supported by the current backend contract.") }}
		</p>

		<div v-if="showValidation && validationErrors.length" class="output-fields-errors">
			<div v-for="error in validationErrors" :key="error"><i class="fa fa-exclamation-circle mr-1"></i>{{ error }}</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import MultiSelectList from "../../../../controls/MultiSelectList.vue";
import { useMetaStore } from "../../../../stores/useMetaStore";
import {
	AGGREGATE_FUNCTIONS,
	parseOutputFields,
	serializeOutputFields,
	validateOutputFields,
} from "./output_fields_model.js";
import OutputFieldPicker from "./OutputFieldPicker.vue";

const props = defineProps({
	modelValue: { type: [Array, String], default: () => [] },
	doctype: { type: String, required: true },
	shape: { type: String, required: true },
	readOnly: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);
const metaStore = useMetaStore();
const rows = ref(parseOutputFields(props.modelValue).map((row) => ({ ...row, childFieldOptions: [] })));
const validationErrors = ref([]);
const aggregateFunctions = AGGREGATE_FUNCTIONS.map((value) => ({ value, label: value.toUpperCase() }));

const parentFields = computed(() => metaStore.doc_meta[props.doctype] || []);
const childTableOptions = computed(() =>
	parentFields.value
		.filter((field) => ["Table", "Table MultiSelect"].includes(field.fieldtype) && field.options)
		.map((field) => ({
			value: field.fieldname,
			label: (field.original_label || field.label || field.fieldname) + " (" + field.fieldname + ")",
			doctype: field.options,
		}))
);

function newId() {
	return "output-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
}
function rowTitle(row) {
	if (row.kind === "field") return row.alias || row.field || __("Output field");
	if (row.kind === "function") return (row.functionName || "count").toUpperCase() + "(" + (row.field || "?") + ")" + (row.alias ? " as " + row.alias : "");
	if (row.kind === "child") return row.tableField || __("Embedded child selection");
	return __("Advanced field expression");
}
function rowDescription(row) {
	if (row.kind === "field") return row.field ? __("Field") + " · " + row.field : __("Choose the field to return");
	if (row.kind === "function") return __("Aggregate function") + (row.alias ? " · " + row.alias : "");
	if (row.kind === "child") return __("Nested child array") + " · " + (row.fields || []).length + " " + __("selected fields");
	return __("Native field syntax is preserved until you edit this expression");
}
function emitRows() {
	validationErrors.value = [];
	emit("update:modelValue", serializeOutputFields(rows.value));
}
function updateRowValue(row, key, value) {
	if (props.readOnly) return;
	row[key] = value;
	emitRows();
}
function updateRaw(row, value) {
	if (props.readOnly) return;
	row.expression = value;
	row.dirty = true;
	emitRows();
}
function addField() {
	if (props.readOnly) return;
	rows.value.push({ id: newId(), kind: "field", field: "", alias: "", fields: [], childFieldOptions: [] });
	emitRows();
}
function addFunction() {
	if (props.readOnly) return;
	rows.value.push({ id: newId(), kind: "function", functionName: "count", field: "", alias: "", fields: [], childFieldOptions: [] });
	emitRows();
}
function addChild() {
	if (props.readOnly) return;
	rows.value.push({ id: newId(), kind: "child", tableField: "", fields: [], childFieldOptions: [] });
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
				label: (field.original_label || field.label || field.fieldname) + " (" + field.fieldname + ")",
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
			if (row.kind === "child") await loadChildFieldOptions(row);
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
	const errors = validateOutputFields(rows.value, props.shape);
	for (const row of rows.value) {
		if (row.kind !== "child" || !row.tableField) continue;
		if (!childTableOptions.value.some((option) => option.value === row.tableField)) {
			errors.push("Child selection references a field that is not a child table.");
			continue;
		}
		if (row.fields.some((field) => !row.childFieldOptions.some((option) => option.value === field))) {
			errors.push("Child selection contains a field that is not available in the selected child DocType.");
		}
	}
	validationErrors.value = errors;
	return { valid: errors.length === 0, errors };
}

watch(
	() => props.modelValue,
	(value) => {
		if (JSON.stringify(serializeOutputFields(rows.value)) === JSON.stringify(value)) return;
		rows.value = parseOutputFields(value).map((row) => ({ ...row, childFieldOptions: [] }));
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
	gap: var(--spacing-sm);
}
.output-fields-empty {
	display: flex;
	align-items: center;
	gap: var(--spacing-sm);
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
	padding: var(--spacing-sm) 0;
}
.output-field-row {
	border: 1px solid var(--fxr-border, var(--border-color));
	border-radius: var(--border-radius-md, 8px);
	padding: var(--spacing-sm);
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}
.output-field-row-heading,
.output-field-row-title,
.output-field-row-actions {
	display: flex;
	align-items: center;
	gap: var(--spacing-sm);
}
.output-field-row-heading {
	justify-content: space-between;
}
.output-field-row-title {
	min-width: 0;
	flex: 1;
}
.output-field-index {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 24px;
	height: 24px;
	border-radius: 50%;
	background: var(--fxr-bg-subtle);
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-xs);
	flex: 0 0 auto;
}
.output-field-row-copy {
	min-width: 0;
}
.output-field-row-copy strong {
	display: block;
	overflow-wrap: anywhere;
	font-size: var(--fxr-text-sm);
	font-weight: 600;
}
.output-field-row-copy p {
	margin: 2px 0 0;
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-xs);
	overflow-wrap: anywhere;
}
.output-field-row-actions {
	flex: 0 0 auto;
}
.output-field-controls {
	display: grid;
	grid-template-columns: minmax(0, 2fr) minmax(160px, 1fr);
	gap: var(--spacing-sm);
	align-items: start;
}
.output-function-controls {
	grid-template-columns: 100px minmax(0, 2fr) minmax(160px, 1fr);
}
.output-function-select,
.output-field-alias {
	min-width: 0;
}
.output-child-controls {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-xs);
}
.output-field-label {
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
	margin: 0;
}
.output-field-raw {
	min-width: 0;
	font-family: var(--font-mono);
	font-size: var(--fxr-text-sm);
}
.output-fields-add-actions {
	display: flex;
	flex-wrap: wrap;
	gap: var(--spacing-md);
	padding-top: var(--spacing-xs);
}
.output-fields-hint {
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-xs);
	margin: 0;
}
.output-fields-errors {
	color: var(--red-600, #b91c1c);
	font-size: var(--fxr-text-sm);
	display: flex;
	flex-direction: column;
	gap: 4px;
}
@media (max-width: 700px) {
	.output-field-controls,
	.output-function-controls {
		grid-template-columns: minmax(0, 1fr);
	}
	.output-field-row-heading {
		align-items: flex-start;
	}
	.output-field-row-actions {
		gap: 2px;
	}
}
</style>
