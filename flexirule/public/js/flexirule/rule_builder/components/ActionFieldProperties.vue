<!--
  ActionFieldProperties - DocField-driven property panel for Rule Action nodes
  
  Renders fields dynamically from Rule Action DocType metadata, respecting:
   - depends_on
   - mandatory_depends_on  
   - read_only_depends_on
   - hidden
   
  Follows Frappe Form Builder patterns.
-->
<script setup>
import { computed, ref, watch, onMounted } from "vue";
import { useStore } from "../store";
import AutocompleteControl from "../controls/AutocompleteControl.vue";
import ControlFactory from "../controls/ControlFactory.vue";

const props = defineProps({
	nodeData: Object,
});

const emit = defineEmits(["update:field", "open:conditions", "open:config"]);

const store = useStore();

// Fields to exclude from rendering
const EXCLUDED_FIELDS = [
	"action_id", // Auto-generated
	"position_x", // Visual metadata
	"position_y", // Visual metadata
	"config", // Managed by V2 modal
	"condition_json", // Managed by V2 modal
	"input_mapping", // Managed by V2 modal
	"output_mapping" // Managed by V2 modal
];

// Layout fields to skip
const LAYOUT_FIELDS = ["Section Break", "Column Break", "Tab Break"];

// Get Rule Action DocType meta
const rule_action_meta = computed(() => {
	return frappe.get_meta("Rule Action");
});

// Get fields from meta, filtering hidden and layout fields
const doc_fields = computed(() => {
	if (!rule_action_meta.value?.fields) return [];

	return rule_action_meta.value.fields.filter((df) => {
		// Skip layout fields
		if (LAYOUT_FIELDS.includes(df.fieldtype)) return false;

		// Skip excluded fields
		if (EXCLUDED_FIELDS.includes(df.fieldname)) return false;

		// Skip always hidden fields
		if (df.hidden) return false;

		return true;
	});
});

// Filter visible fields based on depends_on evaluation
const visible_fields = computed(() => {
	return doc_fields.value.filter((df) => {
		return evaluate_depends_on(df.depends_on);
	});
});

// Evaluate depends_on expression
function evaluate_depends_on(expression) {
	if (!expression) return true;

	const doc = props.nodeData;
	if (!doc) return true;

	if (typeof expression === "boolean") {
		return expression;
	}

	if (expression.startsWith("eval:")) {
		try {
			const parent = store.rule_doc;
			return frappe.utils.eval(expression.substr(5), { doc, parent });
		} catch (e) {
			console.warn("Failed to evaluate depends_on:", expression, e);
			return true;
		}
	}

	// Simple fieldname reference
	const value = doc[expression];
	if (Array.isArray(value)) {
		return !!value.length;
	}
	return !!value;
}

// Evaluate mandatory_depends_on
function is_mandatory(df) {
	// Special enforcement for return_variable
	if (df.fieldname === 'return_variable' && operation_metadata.value) {
		const op = operation_metadata.value;
		// Mandatory if operation writes to Context or declares output variables
		if (op.writes_to === 'Context' || 
			(op.writes_vars && JSON.stringify(op.writes_vars) !== '[]') ||
			op.output_schema
		) {
			return true;
		}
	}

	if (df.reqd) return true;
	if (!df.mandatory_depends_on) return false;
	return evaluate_depends_on(df.mandatory_depends_on);
}

// Evaluate read_only_depends_on
function is_read_only(df) {
	if (df.read_only) return true;
	if (!df.read_only_depends_on) return false;
	return evaluate_depends_on(df.read_only_depends_on);
}

// Get field value from node data
function get_value(fieldname) {
	return props.nodeData?.[fieldname];
}

// Update field value
function update_value(fieldname, value) {
	emit("update:field", fieldname, value);
}

// Get options for Autocomplete fields
async function get_autocomplete_options(df) {
	const options_ref = df.options;

	// operation field - get from process adapter
	if (df.fieldname === "operation" && props.nodeData?.process_name) {
		const operations = await store.get_process_operations(props.nodeData.process_name);
		return operations.map((op) => ({
			value: op.func_name,
			label: op.label || op.func_name,
			description: op.description,
		}));
	}

	// next_step_if_true / next_step_if_false - get available action nodes
	if (options_ref === "action_id") {
		return get_action_node_options();
	}

	return [];
}

// Get available action nodes for next step selection
function get_action_node_options() {
	const current_id = props.nodeData?.action_id;

	return (store.nodes || [])
		.filter((el) => el.id !== current_id && el.id !== "start")
		.map((el) => ({
			value: el.id,
			label: el.label || el.data?.action_label || el.id,
		}));
}

// Get current operation's metadata for side-effect warnings
const operation_metadata = computed(() => {
	if (!props.nodeData?.process_name || !props.nodeData?.operation) {
		return null;
	}
	const process = store.processes.find((p) => p.name === props.nodeData.process_name);
	if (!process?.operations) return null;

	return process.operations.find((op) => op.func_name === props.nodeData.operation);
});

// Compute side-effect warning message based on writes_to
const side_effect_warning = computed(() => {
	if (!operation_metadata.value) return null;

	const writes_to = operation_metadata.value.writes_to;
	if (writes_to === "Database") {
		return {
			type: "danger",
			icon: "fa-database",
			message: __("This operation writes directly to the database. Side-effects cannot be rolled back."),
		};
	} else if (writes_to === "Document") {
		return {
			type: "warning",
			icon: "fa-file-text",
			message: __("This operation modifies the document. Ensure this is intentional."),
		};
	}
	return null;
});

// Handle button field clicks
function handle_button_click(df) {
	if (df.fieldname === "configure_operation" || df.fieldname === "configures") {
		emit("open:config");
	} else if (df.fieldname === "set_conditions") {
		emit("open:conditions");
	}
}

// Check if field is a button type
function is_button_field(df) {
	return df.fieldtype === "Button";
}

// Check if field needs autocomplete with dynamic options
function needs_autocomplete(df) {
	return (
		df.fieldtype === "Autocomplete" ||
		df.options === "action_id" ||
		(df.options === "process_name" && df.fieldname === "operation")
	);
}

// Ensure Rule Action meta is loaded
onMounted(async () => {
	if (!frappe.get_meta("Rule Action")) {
		await frappe.model.with_doctype("Rule Action");
	}
});
</script>

<template>
	<div class="action-field-properties">
		<!-- Side-effect Warning Badge -->
		<div v-if="side_effect_warning" :class="['side-effect-warning', 'alert-' + side_effect_warning.type]">
			<i :class="['fa', side_effect_warning.icon]"></i>
			<span>{{ side_effect_warning.message }}</span>
		</div>

		<div v-for="df in visible_fields" :key="df.fieldname" class="field-wrapper">
			<!-- Button fields (configures, set_conditions) -->
			<template v-if="is_button_field(df)">
				<button
					class="btn btn-default btn-sm w-100"
					@click="handle_button_click(df)"
					:disabled="is_read_only(df)"
				>
					<i v-if="df.fieldname === 'configure_operation' || df.fieldname === 'configures'" class="fa fa-cog"></i>
					<i v-else-if="df.fieldname === 'set_conditions'" class="fa fa-code-fork"></i>
					{{ __(df.label) }}
				</button>
			</template>

			<!-- Autocomplete fields (operation, next_step_*) -->
			<template v-else-if="needs_autocomplete(df)">
				<AutocompleteControl
					:df="{
						...df,
						reqd: is_mandatory(df),
						read_only: is_read_only(df),
					}"
					:modelValue="get_value(df.fieldname)"
					:get_options="() => get_autocomplete_options(df)"
					:doc="nodeData"
					:read_only="is_read_only(df)"
					@update:modelValue="update_value(df.fieldname, $event)"
				/>
			</template>

			<!-- Standard fields via ControlFactory -->
			<template v-else>
				<ControlFactory
					:df="{
						...df,
						reqd: is_mandatory(df),
						read_only: is_read_only(df),
					}"
					:modelValue="get_value(df.fieldname)"
					:read_only="is_read_only(df)"
					:doc="nodeData"
					@update:modelValue="update_value(df.fieldname, $event)"
				/>
			</template>
		</div>
	</div>
</template>

<style scoped>
.action-field-properties {
	display: flex;
	flex-direction: column;
	/* Removed gap: 12px as controls have their own margins */
}

.side-effect-warning {
	display: flex;
	align-items: flex-start;
	gap: 8px;
	padding: 8px 10px;
	border-radius: 4px;
	font-size: 11px;
	margin-bottom: 12px;
}

.side-effect-warning.alert-danger {
	background-color: var(--red-50, #fef2f2);
	border: 1px solid var(--red-200, #fecaca);
	color: var(--red-700, #b91c1c);
}

.side-effect-warning.alert-warning {
	background-color: var(--yellow-50, #fffbeb);
	border: 1px solid var(--yellow-200, #fde68a);
	color: var(--yellow-700, #a16207);
}

.side-effect-warning i {
	margin-top: 2px;
}

.field-wrapper {
	margin-bottom: 12px;
}

.control-label {
	font-size: 11px;
	font-weight: 500;
	margin-bottom: 4px;
	color: var(--text-muted);
	display: block;
}

.control-label.reqd::after {
	content: " *";
	color: var(--red-500);
}

.description {
	font-size: 10px;
}

.btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
}

.w-100 {
	width: 100%;
}
</style>
