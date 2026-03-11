<template>
	<div class="create-docs-config">
		<div class="config-section">
			<h5>{{ __("Create Docs") }}</h5>
			<p class="text-muted small">
				{{ __("Configure document creation or update mapping.") }}
			</p>
		</div>

		<div class="config-section">
			<ControlFactory
				:df="modeField"
				:modelValue="mode"
				:hideDescription="true"
				@update:modelValue="updateMode"
			/>
		</div>

		<div class="config-section">
			<h6 class="text-muted">{{ __("Action Settings") }}</h6>
			<ControlFactory
				:df="withReadOnly(referenceDoctypeField)"
				:modelValue="props.node?.data?.reference_doctype"
				@update:modelValue="(val) => updateActionField('reference_doctype', val)"
			/>
			<ControlFactory
				v-if="mode === 'Update Existing'"
				:df="withReadOnly(referenceDocnameField)"
				:modelValue="props.node?.data?.reference_docname"
				@update:modelValue="(val) => updateActionField('reference_docname', val)"
			/>
			<ControlFactory
				:df="withReadOnly(inputSourceField)"
				:modelValue="props.node?.data?.input_source"
				@update:modelValue="(val) => updateActionField('input_source', val)"
			/>
			<ControlFactory
				:df="withReadOnly(mutationModeField)"
				:modelValue="props.node?.data?.mutation_mode"
				@update:modelValue="(val) => updateActionField('mutation_mode', val)"
			/>
		</div>

		<div v-if="!mode" class="alert alert-warning mt-3">
			{{ __("Select a mode to configure parameters.") }}
		</div>

		<div v-else class="config-section">
			<template v-if="mode === 'Update Existing'">
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

			<div class="sub-section">
				<h6>{{ __("Static Values") }}</h6>
				<div class="table-rows">
					<div v-for="(row, idx) in staticRows" :key="idx" class="row-item">
						<input
							class="form-control input-xs"
							v-model="row.key"
							:placeholder="__('Field')"
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
							@click="removeStatic(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addStatic">
						<i class="fa fa-plus"></i> {{ __("Add Value") }}
					</button>
				</div>
			</div>

			<div class="sub-section">
				<h6>{{ __("Field Mappings") }}</h6>
				<div class="table-rows">
					<div v-for="(row, idx) in mappingRows" :key="idx" class="row-item mappings">
						<input
							class="form-control input-xs"
							v-model="row.source"
							:placeholder="__('Source expression')"
							:disabled="readOnly"
							@change="syncConfig"
						/>
						<input
							class="form-control input-xs"
							v-model="row.target"
							:placeholder="__('Target field')"
							:disabled="readOnly"
							@change="syncConfig"
						/>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link text-danger"
							@click="removeMapping(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addMapping">
						<i class="fa fa-plus"></i> {{ __("Add Mapping") }}
					</button>
				</div>
			</div>
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
const staticRows = ref([]);
const mappingRows = ref([]);

const mode = computed(() => props.node?.data?.operation || "");

const valueTypes = ["Value", "Number", "Boolean", "Expression"];

const modeField = computed(() => ({
	fieldname: "operation",
	fieldtype: "Select",
	label: __("Mode"),
	options: "Create New\nUpdate Existing",
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

function withReadOnly(field) {
	return { ...field, read_only: props.readOnly };
}

function updateMode(value) {
	if (!props.node?.data) return;
	props.node.data.operation = value;
	store.mark_dirty();
}

function updateActionField(fieldname, value) {
	if (!props.node?.data) return;
	props.node.data[fieldname] = value;
	store.mark_dirty();
}

function updateConfigKey(key, value) {
	config[key] = value;
	syncConfig();
}

function addStatic() {
	staticRows.value.push({ key: "", value: "", value_type: "Value" });
}

function removeStatic(idx) {
	staticRows.value.splice(idx, 1);
	syncConfig();
}

function addMapping() {
	mappingRows.value.push({ source: "", target: "" });
}

function removeMapping(idx) {
	mappingRows.value.splice(idx, 1);
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

function buildStaticValues() {
	const values = {};
	staticRows.value.forEach((row) => {
		if (!row.key) return;
		values[row.key] = encodeValue(row);
	});
	return values;
}

function buildMappings() {
	return mappingRows.value
		.filter((r) => r.source && r.target)
		.map((r) => ({ source: r.source, target: r.target }));
}

function syncConfig() {
	const newConfig = {};
	Object.keys(config).forEach((k) => {
		const val = config[k];
		if (val !== undefined && val !== null && val !== "") newConfig[k] = val;
	});

	const staticValues = buildStaticValues();
	if (Object.keys(staticValues).length) newConfig.static_values = staticValues;

	const mappings = buildMappings();
	if (mappings.length) newConfig.field_mappings = mappings;

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

	const staticValues = parsed.static_values || {};
	staticRows.value = Object.entries(staticValues).map(([key, value]) => ({
		key,
		value: stripExpression(value),
		value_type: parseValueType(value),
	}));

	const mappings = parsed.field_mappings || [];
	mappingRows.value = Array.isArray(mappings)
		? mappings.map((m) => ({ source: m.source || "", target: m.target || "" }))
		: [];
}

watch(
	() => props.node?.data?.config,
	(val) => loadConfig(val),
	{ immediate: true }
);

watch(
	() => [staticRows.value, mappingRows.value, config],
	() => {
		syncConfig();
	},
	{ deep: true }
);

function validate() {
	return { valid: true };
}

defineExpose({ validate });
</script>

<style scoped>
.create-docs-config {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.config-section {
	display: flex;
	flex-direction: column;
	gap: 12px;
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
	grid-template-columns: 1.2fr 1.2fr 0.8fr auto;
	gap: 6px;
	align-items: center;
}

.row-item.mappings {
	grid-template-columns: 1.4fr 1.2fr auto;
}
</style>
