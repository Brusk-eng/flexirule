<script setup>
/**
 * MultiSelectListControl - Wrapper for Frappe's MultiSelectList control
 * Commonly used in reports for filtering multiple values with a dropdown checklist.
 */
import { ref, onMounted, watch, onBeforeUnmount, nextTick } from "vue";

const props = defineProps({
	df: Object,
	modelValue: [Array, String],
	read_only: Boolean,
	get_data: { type: Function, default: null },
});

const emit = defineEmits(["update:modelValue"]);

const wrapper = ref(null);
const control = ref(null);
let is_setting_value = false;

async function make_control() {
	if (!wrapper.value) return;
	wrapper.value.innerHTML = "";

	try {
		const control_df = {
			...props.df,
			fieldtype: "MultiSelectList",
			label: props.df.label,
			read_only: props.read_only,
			get_data: props.get_data || props.df.get_data,
			change: () => {
				if (control.value && !is_setting_value) {
					const val = control.value.get_value();
					emit("update:modelValue", val || []);
				}
			},
		};

		const ControlClass = frappe.ui.form.ControlMultiSelectList;
		control.value = new ControlClass({
			df: control_df,
			parent: $(wrapper.value),
			render_input: true,
			only_input: true,
		});
		control.value.make();

		// Set initial value
		if (props.modelValue) {
			sync_value(props.modelValue);
		}
	} catch (e) {
		console.error("Failed to create MultiSelectList control", e);
		wrapper.value.innerHTML = `<div class="text-danger small">${__("Error loading control")}: ${
			e.message
		}</div>`;
	}
}

function sync_value(val) {
	if (!control.value) return;

	// ControlMultiSelectList expects an array or string
	const normalizedValue = Array.isArray(val) ? val : val ? [val] : [];

	// Simple check to avoid circular updates
	const currentVal = control.value.get_value() || [];
	if (JSON.stringify(currentVal) !== JSON.stringify(normalizedValue)) {
		is_setting_value = true;
		control.value.set_value(normalizedValue);
		setTimeout(() => {
			is_setting_value = false;
		}, 50);
	}
}

onMounted(() => {
	nextTick(() => {
		make_control();
	});
});

watch(
	() => props.modelValue,
	(val) => {
		sync_value(val);
	},
	{ deep: true }
);

watch(
	() => [props.df?.options, props.read_only],
	() => {
		make_control();
	}
);

onBeforeUnmount(() => {
	if (control.value && control.value.destroy) {
		// control.value.destroy();
	}
});
</script>

<template>
	<div class="control-wrapper" ref="wrapper"></div>
</template>

<script>
export default {
	name: "MultiSelectListControl",
};
</script>

<style scoped>
.control-wrapper {
	min-height: 35px;
}
:deep(.form-group) {
	margin-bottom: 0 !important;
}
:deep(.dropdown-menu) {
	z-index: 1050;
	max-height: 300px;
	overflow-y: auto;
}
</style>
