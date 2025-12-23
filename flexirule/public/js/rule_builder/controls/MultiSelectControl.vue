<script setup>
/**
 * MultiSelectControl - Wrapper for Frappe's MultiSelect control
 * Supports both static options (Select) and dynamic links (Link)
 */
import { onMounted, ref, watch, onBeforeUnmount } from "vue";

const props = defineProps({
    df: Object,
    modelValue: [Array, String],
    read_only: Boolean
});

const emit = defineEmits(["update:modelValue"]);

let wrapper = ref(null);
let control = ref(null);

function make_control() {
    if (!wrapper.value) return;
    wrapper.value.innerHTML = "";

    // Parse value: standardizing to array for MultiSelect
    let initialValue = [];
    if (Array.isArray(props.modelValue)) {
        initialValue = props.modelValue;
    } else if (typeof props.modelValue === 'string' && props.modelValue) {
         try {
             const parsed = JSON.parse(props.modelValue);
             initialValue = Array.isArray(parsed) ? parsed : [props.modelValue]; 
         } catch {
             initialValue = props.modelValue.split(',').map(s => s.trim()).filter(Boolean);
         }
    }

    try {
        control.value = frappe.ui.form.make_control({
            parent: wrapper.value,
            df: {
                ...props.df,
                fieldtype: "MultiSelect", // Force MultiSelect
                label: props.df.label, 
                options: props.df.options, // DocType for Link or Options for Select
                read_only: props.read_only,
                change: () => {
                    const val = control.value.get_value();
                    // Emit array or string? SimpleCondition usually works with strings or lists.
                    // Let's emit array, MappingWrapper can handle it or we serialize if needed.
                    // But SimpleCondition logic for 'in' usually expects a list/tuple in python.
                    // Storing as JSON string is safer for text fields.
                    emit("update:modelValue", val); 
                },
                get_data: props.df.get_data // Pass through get_data if defined
            },
            render_input: true,
        });
        
        if (initialValue && initialValue.length) {
            control.value.set_value(initialValue);
        }
    } catch(e) {
        console.error("Failed to create MultiSelect control", e);
        wrapper.value.innerHTML = `<div class="text-danger">Error loading control</div>`;
    }
}

onMounted(() => {
    make_control();
});

watch(() => props.modelValue, (val) => {
    // Sync external changes to control
    if (!control.value) return;
    
    let currentVal = control.value.get_value();
    // Normalize comparison (arrays)
    if (JSON.stringify(currentVal) !== JSON.stringify(val)) {
        control.value.set_value(val);
    }
});

watch(() => props.df, () => {
    make_control();
}, { deep: true });

onBeforeUnmount(() => {
    if (control.value && control.value.destroy) {
        // control.value.destroy(); // Frappe controls might not have destroy, mostly DOM removal is enough
    }
});
</script>

<template>
    <div class="control-wrapper" ref="wrapper"></div>
</template>

<style scoped>
.control-wrapper {
    min-height: 35px;
}
:deep(.form-group) {
    margin-bottom: 0 !important;
}
</style>
