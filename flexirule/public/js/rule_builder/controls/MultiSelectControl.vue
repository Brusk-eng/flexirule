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
                    // MultiSelect returns comma-separated string. We should emit Array/List.
                    // Split, trim, and filter text.
                    const arr = val ? val.split(',').map(s => s.trim()).filter(Boolean) : [];
                    emit("update:modelValue", arr); 
                },
                get_data: props.df.get_data // Pass through get_data if defined
            },
            render_input: true,
        });
        
        // Convert Array to comma-separated string for Frappe Control
        const strValue = Array.isArray(initialValue) ? initialValue.join(', ') : (initialValue || '');

        if (strValue) {
            control.value.set_value(strValue);
        }
        
        // Robust listener
        if (control.value.$input) {
            control.value.$input.on('change input awesomplete-selectcomplete', () => {
                const val = control.value.get_value();
                const arr = val ? val.split(',').map(s => s.trim()).filter(Boolean) : [];
                emit("update:modelValue", arr);
            });
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
    
    let currentVal = control.value.get_value(); // String from control
    let newValStr = Array.isArray(val) ? val.join(', ') : (val || '');
    
    // Normalize comparison (strings)
    if (currentVal !== newValStr) {
        control.value.set_value(newValStr);
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

<!--
@deprecated
Reason: Superseded by standard controls. Imported but unused in ControlFactory.
Replaced by: flexirule.ui.ConfigurableAction
Removal Target: v2.0
-->
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
