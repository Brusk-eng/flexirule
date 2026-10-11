<template>
	<ComboBoxControl
		:df="{ label: label || __('Select field'), fieldtype: 'FieldPicker' }"
		:options="navigableFields.currentFields.value"
		:doctype="doctype"
		:modelValue="modelValue"
		:read_only="readOnly"
		:trigger="'button'"
		:hideLabel="true"
		:navigable="!rootOnly"
		:navStack="navigableFields.navStack.value"
		@navigate="navigableFields.handleNavigate"
		@back="navigableFields.handleBack"
		@update:modelValue="onUpdate"
	/>
</template>

<script setup>
import { computed } from "vue";
import ComboBoxControl from "../../../../controls/ComboBoxControl.vue";
import { useNavigableFields } from "../../../../composables/useNavigableFields";

const props = defineProps({
	doctype: { type: String, required: true },
	modelValue: { type: String, default: "" },
	readOnly: { type: Boolean, default: false },
	rootOnly: { type: Boolean, default: false },
	label: { type: String, default: "" },
});
const emit = defineEmits(["update:modelValue"]);

const navigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => (props.rootOnly ? "" : props.modelValue)
);

function onUpdate(value) {
	emit("update:modelValue", value);
	navigableFields.resetStack();
}
</script>
