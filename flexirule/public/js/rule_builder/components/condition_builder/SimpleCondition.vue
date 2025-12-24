<script setup>
/**
 * SimpleCondition - Leaf condition editor (left op right)
 * Uses backend-driven operator configuration
 */
import { computed, inject, ref, watch } from 'vue';
import ControlFactory from '../../controls/ControlFactory.vue';
import FieldPickerControl from '../../controls/FieldPickerControl.vue';
import MappingWrapper from '../MappingWrapper.vue';

const props = defineProps({
    node: { type: Object, required: true },
    docFields: { type: Array, default: () => [] }
});

const emit = defineEmits(['remove']);

// Injected operator config from ConditionBuilder
const operatorConfig = inject('operatorConfig', ref({ fieldtype_operators: {}, operator_labels: {} }));

// Dynamic Link State
const dynamicLinkDocType = ref('');

// Find the selected field metadata
const selectedField = computed(() => {
    const ref = props.node.left?.ref;
    if (!ref) return null;
    return props.docFields.find(f => f.value === ref);
});

// Available operators based on field type - backend-driven
const operators = computed(() => {
    const config = operatorConfig.value;
    const ft = selectedField.value?.fieldtype || 'Data';
    
    // Get valid operators for this fieldtype
    const validOps = config.fieldtype_operators?.[ft] || config.fieldtype_operators?.['_default'] || ['==', '!=', 'is_set', 'is_not_set'];
    const labels = config.operator_labels || {};
    
    return validOps.map(op => ({
        value: op,
        label: __(labels[op] || op)
    }));
});

// Computed Schema for Value Input
const valueFieldSchema = computed(() => {
    if (!selectedField.value) return { fieldtype: 'Data' };
    
    let schema = { ...selectedField.value };
    
    // 1. DocStatus Handling
    if (schema.value === 'doc.docstatus' || schema.fieldname === 'docstatus') {
         schema.fieldtype = 'Select';
         schema.options = [
             { label: __('Draft'), value: 0 },
             { label: __('Submitted'), value: 1 },
             { label: __('Cancelled'), value: 2 }
         ];
    }
    
    // 2. Multi-Select Handling for IN/NOT IN
    if (['in', 'not in'].includes(props.node.op)) {
         schema.fieldtype = 'MultiSelect';
         // Check if we need to adjust options for MultiSelect docstatus
         if (schema.fieldname === 'docstatus') {
             // For MultiSelect, provide simple options because standard control handles strings best
             schema.options = ["0", "1", "2"]; 
         }
    }
    
    // 3. Dynamic Link Handling (Step 2: The actual link picker)
    if (schema.fieldtype === 'Dynamic Link') {
        if (dynamicLinkDocType.value) {
            schema.fieldtype = 'Link';
            schema.options = dynamicLinkDocType.value;
        } else {
            // If no doctype selected, show Data or ReadOnly
            schema.fieldtype = 'Data';
            schema.read_only = 1;
            schema.placeholder = __('Select DocType first');
        }
    }
    
    return schema;
});

// Wrapped Value for Link/Dynamic Link Tuple handling
const wrappedValue = computed({
    get() {
        const val = props.node.right.value;
        const ft = selectedField.value?.fieldtype;
        const op = props.node.op;

        // If not a Link/Dynamic Link, return raw value
        if (ft !== 'Link' && ft !== 'Dynamic Link') return val;

        // If value is empty, return empty
        if (!val) return op === 'in' || op === 'not in' ? [] : '';

        // If it's a tuple [DocType, Value], return Value
        if (Array.isArray(val) && val.length === 2 && typeof val[0] === 'string') {
            return val[1];
        }

        // Legacy/Fallback: return raw value
        return val;       
    },
    set(newVal) {
        const ft = selectedField.value?.fieldtype;
        
        if (ft !== 'Link' && ft !== 'Dynamic Link') {
            props.node.right.value = newVal;
            return;
        }

        // Determine DocType
        let docType = '';
        if (ft === 'Link') {
            docType = selectedField.value.options;
        } else if (ft === 'Dynamic Link') {
            docType = dynamicLinkDocType.value;
        }

        if (!docType) {
            // Should not happen if UI is correct, but falback
             props.node.right.value = newVal;
             return;
        }

        // Wrap it: [DocType, Value]
        props.node.right.value = [docType, newVal];
    }
});

// Watch for changes in existing node value to init dynamicLinkDocType if needed
watch(() => props.node, (newNode) => {
    // Attempt to extract existing Dynamic Link DocType from saved tuple
    if (selectedField.value?.fieldtype === 'Dynamic Link' && !dynamicLinkDocType.value) {
        const val = newNode.right?.value;
        if (Array.isArray(val) && val.length === 2 && typeof val[0] === 'string') {
            dynamicLinkDocType.value = val[0];
        }
    }
}, { immediate: true, deep: true });

function setMapping(ref) {
    props.node.right.ref = ref;
    props.node.right.value = '';
}

function clearMapping() {
    props.node.right.ref = '';
}
</script>

<template>
    <div class="simple-condition">
        <!-- Field -->
        <div class="condition-cell field-cell">
            <FieldPickerControl
                :df="{ label: __('Field') }"
                v-model="node.left.ref"
                :fields="docFields"
            />
            <small v-if="selectedField" class="text-muted field-hint">{{ selectedField.fieldtype }}</small>
        </div>

        <!-- Operator -->
        <div class="condition-cell operator-cell">
            <label class="small text-muted mb-1 d-block">{{ __("Operator") }}</label>
            <select v-model="node.op" class="form-control form-control-sm">
                <option v-for="op in operators" :key="op.value" :value="op.value">
                    {{ op.label }}
                </option>
            </select>
        </div>

        <div class="condition-cell value-cell" v-if="!['is_set', 'is_not_set'].includes(node.op)">
            <div v-if="selectedField?.fieldtype === 'Dynamic Link'" class="mb-2">
                 <label class="small text-muted d-block">{{ __("Target DocType") }}</label>
                 <!-- Using ControlFactory to render Link to DocType -->
                 <ControlFactory
                    :df="{ fieldtype: 'Link', options: 'DocType', placeholder: __('Select DocType') }"
                    v-model="dynamicLinkDocType"
                 />
            </div>

            <MappingWrapper 
                :label="__('Value')"
                :mappingValue="node.right.ref"
                :docFields="docFields"
                @update:mappingValue="setMapping"
                @clearStatic="clearMapping"
            >
                <ControlFactory 
                    :df="valueFieldSchema"
                    v-model="wrappedValue"
                />
            </MappingWrapper>
        </div>
        <div v-else class="condition-cell value-cell"></div>

        <!-- Remove -->
        <div class="condition-cell action-cell">
            <button class="btn btn-xs btn-link text-danger" @click="emit('remove')" :title="__('Remove')">
                <i class="fa fa-trash-o"></i>
            </button>
        </div>
    </div>
</template>

<style scoped>
.simple-condition {
    display: grid;
    grid-template-columns: 1fr 140px 1fr 40px;
    gap: 12px;
    align-items: start;
    padding: 12px;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: white;
    transition: box-shadow 0.2s;
}

.simple-condition:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.condition-cell {
    min-width: 0;
}

.field-cell {
    min-width: 180px;
}

.operator-cell {
    width: 140px;
}

.value-cell {
    min-width: 180px;
}

.action-cell {
    width: 40px;
    display: flex;
    justify-content: center;
    padding-top: 24px;
}

.field-hint {
    display: block;
    margin-top: 2px;
    font-size: 11px;
}

/* Responsive: Stack on narrow screens */
@media (max-width: 768px) {
    .simple-condition {
        grid-template-columns: 1fr 1fr;
        grid-template-rows: auto auto;
    }
    .action-cell {
        padding-top: 0;
    }
}
</style>
