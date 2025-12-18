<template>
    <div class="context-picker">
        <input 
            type="text" 
            class="form-control form-control-sm" 
            :value="modelValue"
            @input="$emit('update:modelValue', $event.target.value)"
            list="context-vars-list"
            placeholder="doc.field or vars.name"
        />
        <datalist id="context-vars-list">
            <option v-for="opt in suggestions" :key="opt.value" :value="opt.value">
                {{ opt.label || opt.value }}
            </option>
        </datalist>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useStore } from '../store';

const props = defineProps(['modelValue']);
const emit = defineEmits(['update:modelValue']);
const store = useStore();

const metaFields = ref([]);

// Common variables that are always available
const commonVars = [
    { value: 'vars.previous_result', label: 'Previous Result' },
    { value: 'vars.parent_doc', label: 'Parent Document' }
];

const suggestions = computed(() => {
    // 1. Doc fields
    const docOptions = metaFields.value.map(f => ({
        value: `doc.${f.fieldname}`,
        label: `doc.${f.fieldname} (${f.label})`
    }));
    
    // 2. Common vars
    return [...docOptions, ...commonVars];
});

onMounted(() => {
    fetchMeta();
});

function fetchMeta() {
    const doctype = store.rule_doc?.document_type;
    if (!doctype) return;
    
    frappe.model.with_doctype(doctype, () => {
        const meta = frappe.get_meta(doctype);
        metaFields.value = meta.fields || [];
    });
}
</script>

<style scoped>
.context-picker input {
    font-family: monospace;
    color: var(--primary);
    background-color: var(--bg-light-gray);
}
</style>
