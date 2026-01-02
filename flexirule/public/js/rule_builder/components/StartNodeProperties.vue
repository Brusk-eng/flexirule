<!--
  StartNodeProperties - Properties panel for Start node
  
  This component handles the special Start node which uses Rule DocType fields,
  not Rule Action fields.
-->
<script setup>
import { computed, ref } from 'vue';
import { useStore } from '../store';

const props = defineProps({
    nodeData: Object
});

const emit = defineEmits(['update:field', 'open:conditions']);

const store = useStore();

// Trigger event options from store
const trigger_event_options = computed(() => store.trigger_event_options || []);

function update_field(fieldname, value) {
    emit('update:field', fieldname, value);
}

// Check if conditions are configured
const has_conditions = computed(() => {
    const cond = props.nodeData?.trigger_condition;
    return cond && cond !== '{}' && cond !== 'null';
});
</script>

<template>
    <div class="start-node-properties">
        <!-- Document Type (Read-only) -->
        <div class="form-group">
            <label class="control-label">{{ __("Document Type") }}</label>
            <input 
                type="text" 
                class="form-control" 
                :value="nodeData?.document_type" 
                readonly 
            />
        </div>
        
        <!-- Trigger Event -->
        <div class="form-group">
            <label class="control-label">{{ __("Trigger Event") }}</label>
            <select 
                class="form-control" 
                :value="nodeData?.trigger_event"
                @change="update_field('trigger_event', $event.target.value)"
            >
                <option v-for="opt in trigger_event_options" :key="opt" :value="opt">
                    {{ opt }}
                </option>
            </select>
        </div>
        
        <!-- Trigger Filters (Legacy, Read-only) -->
        <div class="form-group">
            <label class="control-label">{{ __("Trigger Filters (Legacy)") }}</label>
            <div class="description text-muted mb-2">
                {{ __("ReadOnly: Auto-compiled from Condition Builder") }}
            </div>
            <textarea 
                class="form-control text-mono" 
                rows="2" 
                readonly
                :value="nodeData?.trigger_filters"
            ></textarea>
        </div>
        
        <!-- Trigger Condition -->
        <div class="form-group">
            <label class="control-label">{{ __("Trigger Condition (Logic)") }}</label>
            <div class="description text-muted mb-2">
                {{ __("Define complex logic conditions for when this rule should trigger.") }}
            </div>
            
            <button 
                class="btn btn-default btn-sm w-100"
                @click="emit('open:conditions')"
            >
                <i class="fa fa-code-fork"></i> 
                {{ __("Open Condition Builder") }}
            </button>
            
            <div v-if="has_conditions" class="mt-2 text-success small">
                <i class="fa fa-check-circle"></i> 
                {{ __("Conditions Configured") }}
            </div>
        </div>
    </div>
</template>

<style scoped>
.start-node-properties {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.form-group {
    margin-bottom: 0;
}

.control-label {
    font-size: 11px;
    font-weight: 500;
    margin-bottom: 4px;
    color: var(--text-muted);
    display: block;
}

.description {
    font-size: 11px;
}

.form-control {
    width: 100%;
    padding: 6px 10px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 13px;
}

.text-mono {
    font-family: monospace;
    font-size: 11px;
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

.mt-2 {
    margin-top: 8px;
}

.mb-2 {
    margin-bottom: 8px;
}
</style>
