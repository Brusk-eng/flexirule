<template>
    <div class="process-node-config">
        <div class="form-group relative">
            <label>{{ __("Method") }}</label>
            <div class="input-group">
                <input type="text" class="form-control" 
                    v-model="methodSearch"
                    @focus="showMethodSuggestions = true"
                    @input="filterMethods"
                    :placeholder="__('Search method...')" />
                <button class="btn btn-default btn-sm" @click="showMethodDescription" :title="__('Show Description')">
                    <i class="fa fa-info-circle"></i>
                </button>
            </div>
            
            <div v-if="showMethodSuggestions" class="suggestions-dropdown">
                <div v-for="m in filteredMethods" 
                    :key="m.name" 
                    class="suggestion-item"
                    @click="selectMethod(m)">
                    <div class="d-flex justify-content-between align-items-center w-100">
                        <div class="suggestion-name">{{ m.method_name }}</div>
                        <div class="method-badges">
                            <span v-if="m.transactional" class="badge badge-warning" title="Transactional" style="font-size:9px; padding:2px 4px; margin-left:2px">Tx</span>
                            <span v-if="m.side_effects === 'Pure'" class="badge badge-success" title="Pure" style="font-size:9px; padding:2px 4px; margin-left:2px">Pure</span>
                            <span v-if="m.creates_new_docs" class="badge badge-info" title="Creates Docs" style="font-size:9px; padding:2px 4px; margin-left:2px">New</span>
                        </div>
                    </div>
                    <div class="suggestion-path" v-if="m.method_path">{{ m.method_path }}</div>
                </div>
                <div v-if="!filteredMethods.length" class="p-2 text-muted">{{ __("No methods found") }}</div>
            </div>
        </div>
        
        <button v-if="nodeData?.process_method"
            class="btn btn-sm btn-default w-100 mb-3" 
            @click="$emit('open-config')">
            <i class="fa fa-cog"></i> {{ __("Configure") }}
        </button>

        <div class="row">
            <div class="col-xs-6">
                <div class="form-group">
                    <label>{{ __("Timeout (s)") }}</label>
                    <input type="number" class="form-control" 
                        :value="nodeData?.timeout || 30"
                        @input="$emit('update-field', 'timeout', parseInt($event.target.value))" />
                </div>
            </div>
            <div class="col-xs-6">
                <div class="form-group">
                    <label>{{ __("Priority") }}</label>
                    <input type="number" class="form-control" 
                        :value="nodeData?.priority || 0"
                        @input="$emit('update-field', 'priority', parseInt($event.target.value))" />
                </div>
            </div>
        </div>

        <div class="form-group">
            <label>{{ __("On Error") }}</label>
            <select class="form-control" 
                :value="nodeData?.on_error || 'Stop'"
                @change="$emit('update-field', 'on_error', $event.target.value)">
                <option value="Stop">{{ __("Stop") }}</option>
                <option value="Continue">{{ __("Continue") }}</option>
                <option value="Retry">{{ __("Retry") }}</option>
                <option value="Rollback">{{ __("Rollback") }}</option>
                <option value="Escalate">{{ __("Escalate") }}</option>
            </select>
        </div>

        <div class="form-group" v-if="nodeData?.on_error === 'Retry'">
            <label>{{ __("Retry Count") }}</label>
            <input type="number" class="form-control" 
                :value="nodeData?.retry_count || 0"
                @input="$emit('update-field', 'retry_count', parseInt($event.target.value))" />
        </div>

        <!-- Output Mapping Section -->
        <div class="form-group" v-if="!nodeData?.is_async">
             <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="mb-0" style="font-weight:600">{{ __("Output Assignments") }}</label>
            </div>
            
            <div v-if="outputFields.length">
                <div v-for="field in outputFields" :key="field.key" class="mb-2">
                    <small class="text-muted d-block">{{ field.label }} ({{ field.type }})</small>
                    <div class="input-group input-group-sm">
                        <span class="input-group-text" style="font-size:11px; background:#f0f0f0;">vars.</span>
                        <input type="text" class="form-control" 
                            :value="getOutputMapping(field.key)"
                            @input="updateOutputMapping(field.key, $event.target.value)" 
                            :placeholder="field.key === '__self__' ? 'result_var' : field.key"
                        />
                    </div>
                </div>
            </div>
            <div v-else class="text-muted small">
                 <div class="mb-1">{{ __("Map result to variable:") }}</div>
                 <div class="input-group input-group-sm">
                    <span class="input-group-text" style="font-size:11px; background:#f0f0f0;">vars.</span>
                    <input type="text" class="form-control" 
                        :value="getOutputMapping('__self__')"
                        @input="updateOutputMapping('__self__', $event.target.value)" 
                        placeholder="result_var"
                    />
                </div>
            </div>
        </div>
        <div v-else class="alert alert-warning p-2 small mt-2">
            <i class="fa fa-info-circle"></i> {{ __("Async actions cannot return values to the context.") }}
        </div>

        <div class="form-group">
            <label class="checkbox-label" :class="{ 'text-muted': selectedMethod?.transactional }" :title="selectedMethod?.transactional ? __('Transactional methods cannot run asynchronously') : ''">
                <input type="checkbox" 
                    :checked="nodeData?.is_async"
                    :disabled="selectedMethod?.transactional"
                    @change="$emit('update-field', 'is_async', $event.target.checked ? 1 : 0)" />
                {{ __("Run Asynchronously") }}
                <span v-if="selectedMethod?.transactional" class="ml-1 text-warning"><i class="fa fa-lock"></i></span>
            </label>
            <div v-if="selectedMethod?.transactional" class="help-text text-danger mt-1" style="font-size:10px">
                {{ __("Transactional methods must run synchronously.") }}
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
    nodeData: Object,
    processMethods: { type: Array, default: () => [] },
    selectedMethod: Object
});

const emit = defineEmits(['update-field', 'open-config', 'select-method']);

const methodSearch = ref('');
const showMethodSuggestions = ref(false);

const filteredMethods = computed(() => {
    return props.processMethods.filter(m => 
        m.method_name.toLowerCase().includes(methodSearch.value.toLowerCase()) || 
        (m.method_path && m.method_path.toLowerCase().includes(methodSearch.value.toLowerCase()))
    );
});

const outputFields = computed(() => {
    if (!props.selectedMethod?.output_schema) return [];
    try {
        const schema = JSON.parse(props.selectedMethod.output_schema);
        if (Array.isArray(schema)) {
            return schema.map(f => ({
                key: f.fieldname,
                label: f.label || f.fieldname,
                type: f.fieldtype
            }));
        } else if (schema.properties) {
            return Object.entries(schema.properties).map(([k, v]) => ({
                key: k,
                label: v.title || k,
                type: v.type
            }));
        }
        return [];
    } catch (e) {
        return [];
    }
});

watch(() => props.nodeData?.process_method, (newVal) => {
    if (newVal) {
        const method = props.processMethods.find(m => m.name === newVal);
        methodSearch.value = method ? method.method_name : newVal;
    } else {
        methodSearch.value = '';
    }
}, { immediate: true });

function filterMethods() {
    showMethodSuggestions.value = true;
}

function selectMethod(method) {
    methodSearch.value = method.method_name;
    emit('select-method', method.name);
    showMethodSuggestions.value = false;
}

function showMethodDescription() {
    if (props.selectedMethod?.description) {
        frappe.msgprint({
            title: __('Method Description'),
            message: props.selectedMethod.description
        });
    } else {
        frappe.msgprint(__('No description available'));
    }
}

function getOutputMapping(key) {
    const mappingStr = props.nodeData?.output_mapping;
    if (!mappingStr) return '';
    try {
        const mapping = JSON.parse(mappingStr);
        let val = mapping[key] || '';
        if (val.startsWith('vars.')) return val.substring(5);
        return val;
    } catch (e) { return ''; }
}

function updateOutputMapping(key, varName) {
    const mappingStr = props.nodeData?.output_mapping || '{}';
    let mapping = {};
    try { mapping = JSON.parse(mappingStr); } catch (e) {}
    
    if (!varName) {
        delete mapping[key];
    } else {
        mapping[key] = `vars.${varName}`;
    }
    
    emit('update-field', 'output_mapping', JSON.stringify(mapping));
}
</script>

<style scoped>
.suggestions-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    max-height: 250px;
    overflow-y: auto;
    z-index: 100;
}

.suggestion-item {
    padding: 8px 12px;
    cursor: pointer;
    border-bottom: 1px solid #f0f0f0;
}

.suggestion-item:hover {
    background: var(--gray-100);
}

.suggestion-name {
    font-weight: 500;
}

.suggestion-path {
    font-size: 11px;
    color: var(--text-muted);
}
</style>
