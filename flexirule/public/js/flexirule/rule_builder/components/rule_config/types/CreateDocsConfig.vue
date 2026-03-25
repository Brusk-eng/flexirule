<template>
	<div class="create-docs-config">
		<div v-if="!mode" class="empty-mode-state text-center p-5">
			<i class="fa fa-plus-circle fa-3x text-muted mb-3 opacity-20"></i>
			<p class="text-muted">
				{{ __("Please select a Creation Mode in the Setup panel to proceed.") }}
			</p>
		</div>

		<div v-else class="config-container">
			<template v-if="mode === 'Create ToDo'">
				<ControlFactory
					:df="with_read_only(assignedToField)"
					:modelValue="config.assigned_to"
					@update:modelValue="(val) => update_config_key('assigned_to', val)"
				/>
				<ControlFactory
					:df="with_read_only(todoDescriptionField)"
					:modelValue="config.description"
					@update:modelValue="(val) => update_config_key('description', val)"
				/>
				<ControlFactory
					:df="with_read_only(todoPriorityField)"
					:modelValue="config.priority"
					@update:modelValue="(val) => update_config_key('priority', val)"
				/>
			</template>

			<template v-else-if="mode === 'Add Comment'">
				<ControlFactory
					:df="with_read_only(commentTypeField)"
					:modelValue="config.comment_type"
					@update:modelValue="(val) => update_config_key('comment_type', val)"
				/>
				<ControlFactory
					:df="with_read_only(commentTextField)"
					:modelValue="config.comment_text"
					@update:modelValue="(val) => update_config_key('comment_text', val)"
				/>
			</template>

			<template v-else-if="mode === 'Update Existing'">
				<ControlFactory
					:df="with_read_only(docnameExprField)"
					:modelValue="config.docname_expression"
					@update:modelValue="(val) => update_config_key('docname_expression', val)"
				/>
				<div class="alert alert-info py-2 px-3 small mt-2">
					<i class="fa fa-info-circle"></i>
					{{ __("Reference DocName is managed in the Setup & Input panel.") }}
				</div>
			</template>

			<div
				v-if="!['Create ToDo', 'Add Comment'].includes(mode)"
				class="sub-section section-subcard"
			>
				<h6>{{ __("Static Values") }}</h6>
				<div class="table-rows">
					<div v-for="(row, idx) in static_rows" :key="idx" class="row-item">
						<FieldPickerControl
							:df="{ label: '' }"
							:fields="doctype_fields"
							:documentType="reference_doctype"
							:modelValue="row.key"
							:read_only="readOnly"
							@update:modelValue="(val) => (row.key = val)"
						/>
						<div class="value-cell">
							<template v-if="row.value_type === 'Variable'">
								<AutocompleteControl
									:df="{ fieldtype: 'Autocomplete', label: '' }"
									:options="variable_options"
									:modelValue="row.value"
									:read_only="readOnly"
									:hideLabel="true"
									@update:modelValue="(val) => (row.value = val)"
								/>
							</template>
							<template v-else-if="row.value_type === 'Expression'">
								<input
									class="form-control input-xs"
									v-model="row.value"
									:placeholder="__('Expression')"
									:disabled="readOnly"
									@change="sync_local_config"
								/>
							</template>
							<template v-else>
								<ControlFactory
									:df="value_field_df(row)"
									:modelValue="row.value"
									:hideLabel="true"
									:hideDescription="true"
									@update:modelValue="(val) => (row.value = val)"
								/>
							</template>
						</div>
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
							@click="remove_static(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="add_static">
						<i class="fa fa-plus"></i> {{ __("Add Value") }}
					</button>
				</div>
			</div>

			<div
				v-if="!['Create ToDo', 'Add Comment'].includes(mode)"
				class="sub-section section-subcard"
			>
				<h6>{{ __("Field Mappings") }}</h6>
				<div class="table-rows">
					<div v-for="(row, idx) in mapping_rows" :key="idx" class="row-item mappings">
						<AutocompleteControl
							:df="{ fieldtype: 'Autocomplete', label: '' }"
							:options="variable_options"
							:modelValue="row.source"
							:read_only="readOnly"
							:hideLabel="true"
							@update:modelValue="(val) => (row.source = val)"
						/>
						<FieldPickerControl
							:df="{ label: '' }"
							:fields="doctype_fields"
							:documentType="reference_doctype"
							:modelValue="row.target"
							:read_only="readOnly"
							@update:modelValue="(val) => (row.target = val)"
						/>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link text-danger"
							@click="remove_mapping(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="add_mapping">
						<i class="fa fa-plus"></i> {{ __("Add Mapping") }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { reactive, ref, computed, watch } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import AutocompleteControl from "../../../controls/AutocompleteControl.vue";
import FieldPickerControl from "../../../controls/FieldPickerControl.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const {
	store,
	config,
	doctype_fields,
	variable_options,
	mode,
	reference_doctype,
	with_read_only,
	strip_expression,
	encode_value,
	parse_value_type,
	sync_config,
} = useActionConfig(props);

const static_rows = ref([]);
const mapping_rows = ref([]);

const value_types = ["Value", "Number", "Boolean", "Variable", "Expression"];

const docnameExprField = {
	fieldname: "docname_expression",
	fieldtype: "Code",
	label: __("Docname Expression"),
	options: "PythonExpression",
};

const assignedToField = {
	fieldname: "assigned_to",
	fieldtype: "Link",
	label: __("Assigned To"),
	options: "User",
	reqd: 1,
};

const todoDescriptionField = {
	fieldname: "description",
	fieldtype: "Code",
	label: __("Description"),
	options: "Jinja",
	reqd: 1,
};

const todoPriorityField = {
	fieldname: "priority",
	fieldtype: "Select",
	label: __("Priority"),
	options: "Low\nMedium\nHigh",
};

const commentTypeField = {
	fieldname: "comment_type",
	fieldtype: "Select",
	label: __("Comment Type"),
	options: "Comment\nInfo\nEdit\nWorkflow",
};

const commentTextField = {
	fieldname: "comment_text",
	fieldtype: "Code",
	label: __("Comment Text"),
	options: "Jinja",
	reqd: 1,
};

const field_map = computed(() => {
	const map = {};
	doctype_fields.value.forEach((f) => {
		map[f.value] = f;
	});
	return map;
});

const variable_set = computed(() => {
	return new Set((variable_options.value || []).map((v) => v.value));
});

function update_config_key(key, value) {
	config[key] = value;
	sync_local_config();
}

function add_static() {
	static_rows.value.push({ key: "", value: "", value_type: "Value" });
}

function remove_static(idx) {
	static_rows.value.splice(idx, 1);
	sync_local_config();
}

function add_mapping() {
	mapping_rows.value.push({ source: "", target: "" });
}

function remove_mapping(idx) {
	mapping_rows.value.splice(idx, 1);
	sync_local_config();
}

function value_field_df(row) {
	let fieldtype = "Data";
	let options = null;
	if (row.value_type === "Number") fieldtype = "Float";
	else if (row.value_type === "Boolean") fieldtype = "Check";
	else if (row.key && field_map.value[row.key]) {
		fieldtype = field_map.value[row.key].fieldtype || "Data";
		options = field_map.value[row.key].options || null;
	}
	return {
		fieldname: "value",
		fieldtype,
		options,
		read_only: props.readOnly,
	};
}

function build_static_values() {
	const values = {};
	static_rows.value.forEach((row) => {
		if (!row.key) return;
		values[row.key] = encode_value(row);
	});
	return values;
}

function build_mappings() {
	return mapping_rows.value
		.filter((r) => r.source && r.target)
		.map((r) => ({ source: r.source, target: r.target }));
}

function sync_local_config() {
	const new_config = {};
	Object.keys(config).forEach((k) => {
		const val = config[k];
		if (val !== undefined && val !== null && val !== "") new_config[k] = val;
	});

	const static_values = build_static_values();
	if (Object.keys(static_values).length) new_config.static_values = static_values;

	const mappings = build_mappings();
	if (mappings.length) new_config.field_mappings = mappings;

	sync_config(new_config);
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

	const static_values = parsed.static_values || {};
	static_rows.value = Object.entries(static_values).map(([key, value]) => ({
		key,
		value: strip_expression(value),
		value_type: parse_value_type(value, variable_set.value),
	}));

	const mappings = parsed.field_mappings || [];
	mapping_rows.value = Array.isArray(mappings)
		? mappings.map((m) => ({ source: m.source || "", target: m.target || "" }))
		: [];
}

watch(
	() => props.node?.data?.config,
	(val) => load_local_config(val),
	{ immediate: true }
);

watch(
	() => [static_rows.value, mapping_rows.value, config],
	() => {
		sync_local_config();
	},
	{ deep: true }
);

defineExpose({
	validate: () => {
		const errors = [];
		if (mode.value === "Create ToDo") {
			if (!config.assigned_to) errors.push(__("Assigned To is required"));
			if (!config.description) errors.push(__("Description is required"));
		}
		if (mode.value === "Add Comment" && !config.comment_text) {
			errors.push(__("Comment Text is required"));
		}
		return { valid: errors.length === 0, errors };
	},
});
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
	grid-template-columns: 1.4fr 1.6fr 0.8fr auto;
	gap: 6px;
	align-items: center;
}

.row-item.mappings {
	grid-template-columns: 1.4fr 1.4fr auto;
}

.value-cell :deep(.control-factory) {
	width: 100%;
}
</style>
