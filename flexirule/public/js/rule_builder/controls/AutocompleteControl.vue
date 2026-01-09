<!--
  AutocompleteControl - Simplified autocomplete using Frappe's ControlAutocomplete
-->
<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";

const props = defineProps({
	df: Object,
	modelValue: [String, Number],
	read_only: Boolean,
	options: { type: Array, default: null },
	get_options: { type: Function, default: null },
	doc: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue"]);

const wrapper_ref = ref(null);
let frappe_control = null;

onMounted(async () => {
	await nextTick();
	await init_control();
});

onUnmounted(() => {
	if (frappe_control?.awesomplete) {
		try {
			frappe_control.awesomplete.destroy();
		} catch (e) {}
	}
	frappe_control = null;
});

async function init_control() {
	if (!wrapper_ref.value) return;

	// Clear previous content
	wrapper_ref.value.innerHTML = "";

	// Build df
	const control_df = {
		...props.df,
		fieldtype: "Autocomplete",
		hidden: 0,
		ignore_validation: true,
		change: () => {
			if (frappe_control) {
				const value = frappe_control.get_value();
				emit("update:modelValue", value);
			}
		},
	};

	// Create the Frappe Autocomplete control
	frappe_control = frappe.ui.form.make_control({
		df: control_df,
		parent: $(wrapper_ref.value),
		render_input: true,
		only_input: true, // We render our own label
	});

	// Set initial options
	await set_options();

	// Set initial value
	if (props.modelValue) {
		frappe_control.set_value(props.modelValue);
	}

	// Additional event binding for awesomplete selection
	if (frappe_control.$input) {
		frappe_control.$input.on("awesomplete-selectcomplete", () => {
			const value = frappe_control.get_value();
			emit("update:modelValue", value);
		});
	}
}

async function set_options() {
	if (!frappe_control) return;

	let opts = [];

	// Priority: get_options function > options prop > df.options
	if (typeof props.get_options === "function") {
		try {
			opts = await props.get_options(props.doc);
		} catch (e) {
			console.warn("AutocompleteControl: get_options failed", e);
			opts = [];
		}
	} else if (props.options && Array.isArray(props.options)) {
		opts = props.options;
	} else if (props.df?.options && typeof props.df.options === "string") {
		if (props.df.options.includes("\n")) {
			opts = props.df.options
				.split("\n")
				.filter(Boolean)
				.map((o) => ({
					value: o.trim(),
					label: o.trim(),
				}));
		}
	}

	if (opts.length && frappe_control.set_data) {
		frappe_control.set_data(opts);
	}
}

// Watch for options changes
watch(
	() => props.options,
	async () => {
		await set_options();
	},
	{ deep: true }
);

// Watch for value changes from parent
watch(
	() => props.modelValue,
	(newVal) => {
		if (frappe_control && frappe_control.get_value() !== newVal) {
			frappe_control.set_value(newVal || "");
		}
	}
);

// Watch for doc changes (context for get_options)
watch(
	() => props.doc,
	async () => {
		await set_options();
	},
	{ deep: true }
);
</script>

<template>
	<div class="control frappe-control">
		<div v-if="df?.label" class="control-label label" :class="{ reqd: df.reqd }">
			{{ __(df.label) }}
		</div>
		<div ref="wrapper_ref" class="autocomplete-input-wrapper"></div>
		<div v-if="df?.description" class="description text-muted">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style scoped>
.control-label {
	font-size: 11px;
	font-weight: 500;
	margin-bottom: 4px;
	color: var(--text-muted);
}

.control-label.reqd::after {
	content: " *";
	color: var(--red-500);
}

.autocomplete-input-wrapper {
	position: relative;
}

.autocomplete-input-wrapper :deep(.form-control) {
	font-size: 13px;
	padding: 6px 10px;
	width: 100%;
}

.autocomplete-input-wrapper :deep(.awesomplete) {
	width: 100%;
	display: block;
}

.autocomplete-input-wrapper :deep(.awesomplete > ul) {
	z-index: 1050;
	max-height: 200px;
	overflow-y: auto;
}

.description {
	font-size: 10px;
	margin-top: 4px;
}
</style>
