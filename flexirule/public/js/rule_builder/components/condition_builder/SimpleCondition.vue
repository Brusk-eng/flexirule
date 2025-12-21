<script setup>
/**
 * SimpleCondition - Leaf condition editor (left op right)
 * Uses backend-driven operator configuration
 */
import { computed, inject, onMounted, ref } from 'vue';
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

        <!-- Value (hidden for is_set/is_not_set) -->
        <div v-if="!['is_set', 'is_not_set'].includes(node.op)" class="condition-cell value-cell">
            <MappingWrapper 
                :label="__('Value')"
                :mappingValue="node.right.ref"
                :docFields="docFields"
                @update:mappingValue="setMapping"
                @clearStatic="clearMapping"
            >
                <ControlFactory 
                    :df="selectedField || { fieldtype: 'Data' }"
                    v-model="node.right.value"
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
