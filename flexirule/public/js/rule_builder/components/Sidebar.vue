<template>
    <div class="rule-sidebar">
        <div class="sidebar-header">
            <h4>{{ selectedNode?.data?.action_label || selectedNode?.label || __('Properties') }}</h4>
            <button class="btn-close" @click="$emit('close')">×</button>
        </div>
        
        <div class="sidebar-content" v-if="selectedNode">
            <!-- Start Node -->
            <template v-if="selectedNode.type === 'start'">
                <div class="form-group">
                    <label>{{ __("Document Type") }}</label>
                    <input type="text" class="form-control" :value="selectedNode.data?.document_type" readonly />
                </div>
                <div class="form-group">
                    <label>{{ __("Trigger Event") }}</label>
                    <select class="form-control" 
                        :value="selectedNode.data?.trigger_event"
                        @change="updateTriggerEvent($event.target.value)">
                        <option v-for="opt in triggerEventOptions" :key="opt" :value="opt">
                            {{ opt }}
                        </option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>{{ __("Trigger Filters (Legacy)") }}</label>
                    <div class="help-text text-muted mb-2" style="font-size: 11px;">{{ __("ReadOnly: Auto-compiled from Condition Builder") }}</div>
                     <textarea class="form-control text-mono" rows="2" readonly 
                        :value="selectedNode.data?.trigger_filters"></textarea>
                </div>
                
                <div class="form-group mt-3">
                    <label>{{ __("Trigger Condition (Logic)") }}</label>
                    <div class="help-text text-muted mb-2" style="font-size: 11px;">{{ __("Define complex logic here.") }}</div>
                    
                    <button class="btn btn-default btn-sm w-100 mb-2" @click="showConditionModal = true">
                        <i class="fa fa-code-fork"></i> {{ __("Open Condition Builder") }}
                    </button>
                    
                    <div v-if="selectedNode.data?.trigger_condition && selectedNode.data.trigger_condition !== '{}'" class="mt-2" style="font-size: 12px; color: var(--text-muted);">
                         <i class="fa fa-check-circle text-success"></i> {{ __("Conditions Configured") }}
                    </div>
                </div>
            </template>
            
            <!-- Action Nodes -->
            <template v-else>
                <div class="form-group">
                    <label>{{ __("Label") }}</label>
                    <input type="text" class="form-control" 
                        :value="selectedNode.label"
                        @input="updateLabel($event.target.value)" />
                </div>
                
                <div class="form-group">
                    <label>{{ __("Type") }}</label>
                    <select class="form-control" 
                        :value="selectedNode.data?.action_type"
                        @change="updateActionType($event.target.value)">
                        <option value="Process">{{ __("Process") }}</option>
                        <option value="Condition">{{ __("Condition") }}</option>
                        <option value="Switch">{{ __("Switch") }}</option>
                        <option value="Loop">{{ __("Loop") }}</option>
                        <option value="Wait">{{ __("Wait") }}</option>
                        <option value="Sub-Rule">{{ __("Sub-Rule") }}</option>
                        <option value="Stop">{{ __("Stop") }}</option>
                    </select>
                </div>
                
                <template v-if="selectedNode.data?.action_type === 'Process'">
                    <!-- New File-backed Process Selection -->
                    <div class="form-group relative">
                        <label>{{ __("Process") }}</label>
                        <div class="input-group">
                            <select class="form-control"
                                :value="selectedNode.data?.process_name"
                                @change="updateProcess($event.target.value)">
                                <option value="">{{ __("Select Process...") }}</option>
                                <option v-for="p in store.processes" :key="p.name" :value="p.name">
                                    {{ p.name }}
                                </option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-group relative" v-if="selectedNode.data?.process_name">
                        <label>{{ __("Operation") }}</label>
                        <select class="form-control"
                            :value="selectedNode.data?.operation"
                            @change="updateOperation($event.target.value)">
                            <option value="">{{ __("Select Operation...") }}</option>
                            <option v-for="op in currentProcessOperations" :key="op.func_name" :value="op.func_name">
                                {{ op.label }}
                            </option>
                        </select>
                        <div v-if="selectedOperation?.description" class="help-text text-muted mt-1" style="font-size:11px">
                            {{ selectedOperation.description }}
                        </div>
                    </div>
                    
                    <!-- Legacy Method Selector (shown if no process selected) -->
                    <div class="form-group relative" v-if="!selectedNode.data?.process_name">
                        <label>{{ __("Method (Legacy)") }}</label>
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
                            <div v-for="m in store.process_methods.filter(m => 
                                    m.method_name.toLowerCase().includes(methodSearch.toLowerCase()) || 
                                    (m.method_path && m.method_path.toLowerCase().includes(methodSearch.toLowerCase()))
                                )" 
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
                            <div v-if="!store.process_methods.length" class="p-2 text-muted">{{ __("No methods found") }}</div>
                        </div>
                    </div>
                    
                    <button v-if="selectedNode.data?.process_name && selectedNode.data?.operation"
                        class="btn btn-sm btn-default w-100 mb-3" 
                        @click="openConfigDialog">
                        <i class="fa fa-cog"></i> {{ __("Configure") }}
                    </button>
                    <button v-else-if="selectedNode.data?.process_method"
                        class="btn btn-sm btn-default w-100 mb-3" 
                        @click="openConfigDialog">
                        <i class="fa fa-cog"></i> {{ __("Configure") }}
                    </button>

                    <div class="row">
                        <div class="col-xs-6">
                            <div class="form-group">
                                <label>{{ __("Timeout (s)") }}</label>
                                <input type="number" class="form-control" 
                                    :value="selectedNode.data?.timeout || 30"
                                    @input="updateField('timeout', parseInt($event.target.value))" />
                            </div>
                        </div>
                        <div class="col-xs-6">
                            <div class="form-group">
                                <label>{{ __("Priority") }}</label>
                                <input type="number" class="form-control" 
                                    :value="selectedNode.data?.priority || 0"
                                    @input="updateField('priority', parseInt($event.target.value))" />
                            </div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>{{ __("On Error") }}</label>
                        <select class="form-control" 
                            :value="selectedNode.data?.on_error || 'Stop'"
                            @change="updateField('on_error', $event.target.value)">
                            <option value="Stop">{{ __("Stop") }}</option>
                            <option value="Continue">{{ __("Continue") }}</option>
                            <option value="Retry">{{ __("Retry") }}</option>
                            <option value="Rollback">{{ __("Rollback") }}</option>
                            <option value="Escalate">{{ __("Escalate") }}</option>
                        </select>
                    </div>

                    <div class="form-group" v-if="selectedNode.data?.on_error === 'Retry'">
                        <label>{{ __("Retry Count") }}</label>
                        <input type="number" class="form-control" 
                            :value="selectedNode.data?.retry_count || 0"
                            @input="updateField('retry_count', parseInt($event.target.value))" />
                    </div>

                    <!-- Output Mapping Section -->
                    <div class="form-group" v-if="!selectedNode.data?.is_async">
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
                                :checked="selectedNode.data?.is_async"
                                :disabled="selectedMethod?.transactional"
                                @change="updateField('is_async', $event.target.checked ? 1 : 0)" />
                            {{ __("Run Asynchronously") }}
                            <span v-if="selectedMethod?.transactional" class="ml-1 text-warning"><i class="fa fa-lock"></i></span>
                        </label>
                        <div v-if="selectedMethod?.transactional" class="help-text text-danger mt-1" style="font-size:10px">
                            {{ __("Transactional methods must run synchronously.") }}
                        </div>
                    </div>

                    <!-- Reactive Configuration -->
                    <div class="method-config-section mt-4 pt-3 border-top">
                        <ConfigurationBuilder 
                            v-if="selectedMethodSchema"
                            :schema="selectedMethodSchema"
                            :modelValue="selectedNode.data?.config"
                            :inputMapping="selectedNode.data?.input_mapping"
                            :documentType="store.rule_doc?.document_type"
                            :docMeta="store.raw_meta"
                            @update:modelValue="updateField('config', $event)"
                            @update:inputMapping="updateField('input_mapping', $event)"
                        />
                        <div v-if="selectedNode.data?.action_type === 'Process' && !selectedMethodSchema" class="form-group">
                            <label>{{ __("Static Config (JSON)") }}</label>
                            <textarea class="form-control text-mono" rows="4" style="font-size: 11px;"
                                :value="selectedNode.data?.config"
                                @input="updateField('config', $event.target.value)"
                                placeholder="{}"></textarea>
                        </div>
                        <div v-if="selectedNode.data?.action_type === 'Process'" class="form-group mt-3">
                            <label style="font-weight:600">{{ __("Input Mapping (JSON)") }}</label>
                            <textarea class="form-control text-mono" rows="3" style="font-size: 11px;"
                                :value="selectedNode.data?.input_mapping"
                                @input="updateField('input_mapping', $event.target.value)"
                                placeholder="{}"></textarea>
                            <div class="help-text text-muted" style="font-size:10px">
                                {{ __("Map context variables to method arguments. e.g. {\"threshold\": \"doc.total\"}") }}
                            </div>
                        </div>
                    </div>
                </template>

                <template v-if="selectedNode.data?.action_type === 'Loop'">
                    <div class="form-group">
                        <label>{{ __("Iterator (Python)") }}</label>
                        <input type="text" class="form-control" 
                            :value="getJsonConfig('iterator')"
                            @input="updateJsonConfig('iterator', $event.target.value)"
                            placeholder="doc.items" />
                        <div class="help-text text-muted" style="font-size:11px">{{ __("List to iterate over.") }}</div>
                    </div>
                    <div class="form-group">
                        <label>{{ __("Item Alias") }}</label>
                        <input type="text" class="form-control" 
                            :value="getJsonConfig('alias')"
                            @input="updateJsonConfig('alias', $event.target.value)"
                            placeholder="item" />
                        <div class="help-text text-muted" style="font-size:11px">{{ __("Variable name for current item.") }}</div>
                    </div>
                </template>

                <template v-if="selectedNode.data?.action_type === 'Wait'">
                    <div class="form-group">
                        <label>{{ __("Duration (Seconds)") }}</label>
                        <input type="number" class="form-control" 
                            :value="getJsonConfig('duration')"
                            @input="updateJsonConfig('duration', parseFloat($event.target.value))" />
                    </div>
                </template>

                <template v-if="selectedNode.data?.action_type === 'Sub-Rule'">
                    <div class="form-group relative">
                        <label>{{ __("Select Rule") }}</label>
                        <div class="input-group">
                            <input type="text" class="form-control" 
                                v-model="subRuleSearch"
                                @focus="showSubRuleSuggestions = true"
                                :placeholder="__('Search rule...')" />
                        </div>
                        
                        <div v-if="showSubRuleSuggestions" class="suggestions-dropdown">
                            <div v-for="r in store.available_rules.filter(r => 
                                    r.name.toLowerCase().includes(subRuleSearch.toLowerCase()) || 
                                    (r.rule_name && r.rule_name.toLowerCase().includes(subRuleSearch.toLowerCase()))
                                )" 
                                :key="r.name" 
                                class="suggestion-item"
                                @click="selectSubRule(r)">
                                <div class="d-flex justify-content-between align-items-center w-100">
                                    <div class="suggestion-name">{{ r.rule_name || r.name }}</div>
                                    <span v-if="r.trigger_event === 'Manual'" class="badge badge-info" style="font-size:9px">{{ __("Manual") }}</span>
                                    <span v-else class="badge border text-muted" style="font-size:9px">{{ r.trigger_event }}</span>
                                </div>
                                <div class="suggestion-path" style="font-size:10px">{{ r.name }}</div>
                            </div>
                            <div v-if="!store.available_rules.length" class="p-2 text-muted">{{ __("No rules found for this DocType") }}</div>
                        </div>
                        <div class="help-text text-muted" style="font-size:11px">{{ __("Rule to execute. Context vars are shared.") }}</div>
                    </div>
                    
                    <!-- Sub-Rule Bypass Options -->
                    <div class="form-group mt-3 p-2 border rounded bg-light">
                        <label class="mb-2" style="font-weight:600">{{ __("Sub-Rule Execution Options") }}</label>
                        
                        <label class="checkbox-label d-block mb-2">
                            <input type="checkbox" 
                                :checked="selectedNode.data?.skip_conditions !== 0"
                                @change="updateField('skip_conditions', $event.target.checked ? 1 : 0)" />
                            {{ __("Skip Trigger Conditions") }}
                        </label>
                        <div class="help-text text-muted mb-3" style="font-size:10px">
                            {{ __("When enabled, the sub-rule's trigger_condition will be bypassed. Useful when calling sub-rules that are normally triggered automatically.") }}
                        </div>
                        
                        <label class="checkbox-label d-block">
                            <input type="checkbox" 
                                :checked="selectedNode.data?.skip_permissions === 1"
                                @change="updateField('skip_permissions', $event.target.checked ? 1 : 0)" />
                            {{ __("Skip Permission Checks") }}
                            <span class="badge badge-warning ml-1" style="font-size:9px">{{ __("Audit") }}</span>
                        </label>
                        <div class="help-text text-muted" style="font-size:10px">
                            {{ __("When enabled, the sub-rule executes regardless of user permissions. This action is logged for auditing.") }}
                        </div>
                    </div>
                </template>

                <template v-if="selectedNode.data?.action_type === 'Switch'">
                    <div class="form-group">
                        <label>{{ __("Switch Expression (Python)") }}</label>
                        <textarea class="form-control" rows="2"
                            :value="getJsonConfig('expression')"
                            @input="updateJsonConfig('expression', $event.target.value)"
                            placeholder="doc.category"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>{{ __("Cases") }}</label>
                        <div class="case-list">
                            <div v-for="(nodeId, val) in getJsonConfig('cases', {})" :key="val" class="case-item mb-2 p-2 border rounded bg-light">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <strong class="text-primary">{{ val }}</strong>
                                    <button class="btn btn-xs btn-danger" @click="removeSwitchCase(val)">
                                        <i class="fa fa-times"></i>
                                    </button>
                                </div>
                                <div class="text-muted small">
                                    <i class="fa fa-arrow-right"></i> {{ getNodeLabel(nodeId) }}
                                </div>
                            </div>
                        </div>
                        
                        <div class="add-case mt-2 p-2 border rounded">
                            <input type="text" class="form-control input-sm mb-1" v-model="newCaseValue" :placeholder="__('Value (e.g. \'Active\')')" />
                            <select class="form-control input-sm mb-1" v-model="newCaseTarget">
                                <option value="" disabled>{{ __("Select Target Node") }}</option>
                                <option v-for="node in availableNextNodes" :key="node.id" :value="node.id">
                                    {{ node.label }}
                                </option>
                            </select>
                            <button class="btn btn-xs btn-default w-100" @click="addSwitchCase" :disabled="!newCaseValue || !newCaseTarget">
                                <i class="fa fa-plus"></i> {{ __("Add Case") }}
                            </button>
                        </div>
                    </div>
                </template>
                
                <div class="form-group" v-if="selectedNode.data?.action_type === 'Condition'">
                    <label>{{ __("Expression (Legacy)") }}</label>
                    <div class="help-text text-muted mb-2" style="font-size: 11px;">{{ __("ReadOnly: Auto-compiled from Condition Builder") }}</div>
                    <textarea class="form-control" rows="3" readonly
                        :value="selectedNode.data?.condition_expression"
                        placeholder="Active = True"></textarea>
                    
                    <button class="btn btn-default btn-sm w-100 mt-2" @click="showConditionModal = true">
                        <i class="fa fa-code-fork"></i> {{ __("Open Condition Builder") }}
                    </button>
                    
                    <div v-if="selectedNode.data?.condition_json && selectedNode.data.condition_json !== '{}'" class="mt-2" style="font-size: 12px; color: var(--text-muted);">
                         <i class="fa fa-check-circle text-success"></i> {{ __("Conditions Configured") }}
                    </div>
                </div>
                
                <div class="form-group" v-if="selectedNode.type !== 'stop'">
                    <label>{{ 
                        selectedNode.data?.action_type === 'Condition' ? __('If True →') : 
                        selectedNode.data?.action_type === 'Loop' ? __('Do (Loop Body) →') :
                        selectedNode.data?.action_type === 'Switch' ? __('Default (Else) →') :
                        __('Next →') 
                    }}</label>
                    <select class="form-control"
                        :value="selectedNode.data?.next_step_if_true"
                        @change="updateNextStep('next_step_if_true', $event.target.value)">
                        <option value="">{{ __("End Flow") }}</option>
                        <option v-for="node in availableNextNodes" :key="node.id" :value="node.id">
                            {{ node.label }}
                        </option>
                    </select>
                </div>
                
                <div class="form-group" v-if="selectedNode.data?.action_type === 'Condition' || selectedNode.data?.action_type === 'Loop'">
                    <label>{{ selectedNode.data?.action_type === 'Loop' ? __('Done (Exit Loop) →') : __('If False →') }}</label>
                    <select class="form-control"
                        :value="selectedNode.data?.next_step_if_false"
                        @change="updateNextStep('next_step_if_false', $event.target.value)">
                        <option value="">{{ __("End Flow") }}</option>
                        <option v-for="node in availableNextNodes" :key="node.id" :value="node.id">
                            {{ node.label }}
                        </option>
                    </select>
                </div>
                
                <hr />
                
                <label class="checkbox-label">
                    <input type="checkbox" 
                        :checked="selectedNode.data?.is_enabled !== 0"
                        @change="updateField('is_enabled', $event.target.checked ? 1 : 0)" />
                    {{ __("Enabled") }}
                </label>
                <button class="btn btn-sm btn-danger w-100 mt-3" @click="deleteNode">
                    <i class="fa fa-trash"></i> {{ __("Delete") }}
                </button>
            </template>
        </div>
        
        <!-- Condition Builder Modal -->
        <Teleport to="body">
            <div v-if="showConditionModal" class="condition-modal-overlay">
                <div class="condition-modal-content">
                    <div class="modal-header">
                        <h4>{{ __("Condition Builder") }}</h4>
                        <button class="btn-close" @click="showConditionModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3 d-flex justify-content-end">
                            <label class="d-flex align-items-center gap-2" style="cursor:pointer">
                                <input type="checkbox" v-model="showOldDoc">
                                <span class="small">{{ __("Show Old Document Fields") }}</span>
                            </label>
                        </div>
                           <ConditionBuilder 
                                :modelValue="currentConditions"
                                :docFields="docFields"
                                @update:modelValue="updateConditions"
                           />
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-primary" @click="saveConditions">{{ __("Apply Conditions") }}</button>
                    </div>
                </div>
            </div>
        </Teleport>
    </div>
</template>

<style scoped>
.condition-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1050; /* Bootstrap modal z-index */
    display: flex;
    justify-content: center;
    align-items: center;
}

.condition-modal-content {
    background: white;
    width: 800px;
    max-width: 90vw;
    max-height: 85vh;
    border-radius: 6px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.modal-header {
    padding: 15px;
    border-bottom: 1px solid #eee;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-body {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
}

.modal-footer {
    padding: 15px;
    border-top: 1px solid #eee;
    text-align: right;
    background: #fcfcfc;
}
</style>

<script setup>
import { computed, ref, watch, nextTick, onMounted } from 'vue';
import { useStore } from '../store';
import ConfigurationBuilder from './ConfigurationBuilder.vue';
import ConditionBuilder from './condition_builder/ConditionBuilder.vue';

const emit = defineEmits(['close']);
const store = useStore();

const selectedNode = computed(() => store.graph.selected);
const selectedMethod = computed(() => {
    if (!selectedNode.value?.data?.process_method) return null;
    return (store.process_methods || []).find(m => m.name === selectedNode.value.data.process_method);
});

// File-backed Process Operations
const currentProcessOperations = computed(() => {
    const processName = selectedNode.value?.data?.process_name;
    if (!processName) return [];
    return store.get_process_operations(processName);
});

const selectedOperation = computed(() => {
    const operationName = selectedNode.value?.data?.operation;
    if (!operationName || !currentProcessOperations.value.length) return null;
    return currentProcessOperations.value.find(op => op.func_name === operationName);
});

const selectedOperationSchema = computed(() => {
    if (!selectedOperation.value) return null;
    // Get config_fields from operation's get_config_fields()
    const processName = selectedNode.value?.data?.process_name;
    if (!processName) return null;
    const fields = store.get_operation_config_fields(processName, selectedOperation.value.func_name, null);
    if (fields && fields.length) {
        return { fields };
    }
    return null;
});

const triggerEventOptions = computed(() => store.trigger_event_options);

const selectedMethodSchema = computed(() => {
    // For file-backed process: use operation schema
    if (selectedOperationSchema.value) {
        return selectedOperationSchema.value;
    }
    // Legacy: use method config_schema
    if (!selectedMethod.value?.config_schema) return null;
    try {
        return JSON.parse(selectedMethod.value.config_schema);
    } catch (e) {
        return null;
    }
});

// Condition Builder Modal Logic
const showConditionModal = ref(false);
const currentConditions = ref({});

// DocFields for Autocomplete (Reactive from Store)
const showOldDoc = ref(false);
const docFields = computed(() => {
    let fields = [...store.doc_fields];
    
    // Add [OLD] fields if toggled
    if (showOldDoc.value) {
        const oldFields = store.doc_fields
            .filter(f => f.value.startsWith('doc.'))
            .map(f => ({
                ...f,
                label: `old_doc.${f.fieldname} (${f.label.split('(')[1] ? f.label.split('(')[1].replace(')', '') : f.label})`,
                value: f.value.replace('doc.', 'old_doc.')
            }));
        fields = [...fields, ...oldFields];
    }
    
    return fields.sort((a, b) => a.label.localeCompare(b.label));
});

// Watch trigger open
watch(showConditionModal, (val) => {
    if (val && selectedNode.value?.data) {
        // Ensure metadata is loaded
        const doctype = selectedNode.value.data.document_type || store.rule_doc?.document_type;
        if (doctype) store.fetch_metadata(doctype);

        let source = null;
        if (selectedNode.value.type === 'start') {
             source = selectedNode.value.data.trigger_condition; 
        } else if (selectedNode.value.data.action_type === 'Condition') {
             source = selectedNode.value.data.condition_json;
        }
        
        let parsed = null;
        if (typeof source === 'string' && source.trim() !== '') {
             try { parsed = JSON.parse(source); }
             catch(e) { parsed = null; }
        } else if (typeof source === 'object') {
             parsed = source;
        }
        
        // Migration / Initialization
        if (!parsed || (!parsed.op && !parsed.conditions)) {
            // New Root
             currentConditions.value = { op: "and", conditions: [] };
        } else {
            // Legacy Migration (simple check)
            if (parsed.type === 'group' && !parsed.op) {
                parsed.op = parsed.logicalOperator === 'OR' ? 'or' : 'and';
                // Recursive legacy fix? For now assume top-level is enough or user rebuilds
                // Ideally we'd traverse. But let's assume valid Schema or Empty.
            }
            currentConditions.value = JSON.parse(JSON.stringify(parsed));
        }
    }
});

function updateConditions(val) {
    currentConditions.value = val;
}

function saveConditions() {
    if (!selectedNode.value?.data) return;
    
    // Determine target field
    if (selectedNode.value.type === 'start') {
        selectedNode.value.data.trigger_condition = JSON.stringify(currentConditions.value);
    } else if (selectedNode.value.data?.action_type === 'Condition') {
        selectedNode.value.data.condition_json = JSON.stringify(currentConditions.value);
    }
    
    store.mark_dirty();
    showConditionModal.value = false;
    frappe.show_alert({message: __('Conditions Updated'), indicator: 'green'});
}

// Process Method Autocomplete
const methodSearch = ref('');
const showMethodSuggestions = ref(false);
const subRuleSearch = ref('');
const showSubRuleSuggestions = ref(false);
const methodDescription = ref('');

watch(() => selectedNode.value?.data?.process_method, (newVal) => {
    if (newVal) {
        const method = (store.process_methods || []).find(m => m.name === newVal);
        methodSearch.value = method ? method.method_name : newVal;
        methodDescription.value = method ? method.description : '';
    } else {
        methodSearch.value = '';
        methodDescription.value = '';
    }
}, { immediate: true });

watch(() => selectedNode.value?.data?.rule, (newVal) => {
    if (newVal) {
        const r = (store.available_rules || []).find(r => r.name === newVal);
        subRuleSearch.value = r ? (r.rule_name || r.name) : newVal;
    } else {
        subRuleSearch.value = '';
    }
}, { immediate: true });
onMounted(() => {
    store.fetch_available_rules(store.rule_doc?.document_type);
});

function filterMethods() {
    showMethodSuggestions.value = true;
}

function selectMethod(method) {
    methodSearch.value = method.method_name;
    updateProcessMethod(method.name);
    showMethodSuggestions.value = false;
}

function showMethodDescription() {
    if (methodDescription.value) {
        frappe.msgprint({
            title: __('Method Description'),
            message: methodDescription.value
        });
    } else {
        frappe.msgprint(__('No description available'));
    }
}

function updateStartNodeFilters(filtersJSON) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.trigger_filters = filtersJSON;
    store.mark_dirty();
}

function updateTriggerEvent(value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.trigger_event = value;
    store.mark_dirty();
}

function editFilters() {
    if (!selectedNode.value?.data?.document_type) return;

    const doctype = selectedNode.value.data.document_type;
    const currentFilters = selectedNode.value.data.trigger_filters;

    frappe.model.with_doctype(doctype, () => {
        const dialog = new frappe.ui.Dialog({
            title: __('Set Trigger Filters'),
            fields: [
                {
                    fieldname: 'filter_area',
                    fieldtype: 'HTML',
                    label: __('Filters')
                }
            ],
            size: 'large',
            primary_action_label: __('Set'),
            secondary_action_label: __('Preview Python'),
            secondary_action: () => {
                const values = filter_group.get_filters();
                const expression = convertFiltersToPython(values);
                frappe.msgprint({
                    title: 'Python Expression',
                    message: `<pre>${expression}</pre>`,
                    indicator: 'blue'
                });
            }
        });

        // Set action converts FilterGroup -> Python -> update
        dialog.set_primary_action(__('Set'), () => {
             const values = filter_group.get_filters();
             const expression = convertFiltersToPython(values);
             updateStartNodeFilters(expression);  // Save as Python string
             dialog.hide();
        });

        // Add custom button for Import (optional now, since load handles it, but good for raw edit)
        dialog.add_custom_action(__('Edit Raw Python'), () => {
             const values = filter_group.get_filters();
             const currentExpr = convertFiltersToPython(values);
             
             frappe.prompt(
                { 
                    label: __('Python Expression'), fieldname: 'expression', 
                    fieldtype: 'Code', options: 'Python', reqd: 1,
                    default: currentExpr 
                },
                (data) => {
                     updateStartNodeFilters(data.expression);
                     dialog.hide();
                },
                __('Edit Raw Python'),
                __('Save')
            );
        });

        dialog.show();
        
        // Initialize FilterGroup
        const filter_group = new frappe.ui.FilterGroup({
            parent: dialog.get_field("filter_area").$wrapper,
            doctype: doctype,
            on_change: () => {},
        });
        
        // Load initial values: Python String -> JSON Filters
        if (currentFilters && typeof currentFilters === 'string') {
            try {
                // If it looks like a list (legacy support or empty), try JSON parse
                if (currentFilters.trim().startsWith('[') && currentFilters.includes(']')) {
                     try {
                         const jsonFilters = JSON.parse(currentFilters);
                         filter_group.add_filters_to_filter_group(jsonFilters);
                         frappe.show_alert({message: __('Imported successfully'), indicator: 'green'});
                         return;
                     } catch(e) {
                         // Not JSON, proceed as Python
                         frappe.msgprint(__('Could not parse expression. Ensure format is: field == "value"'));
                     }
                }
                
                // Parse Python Expression
                const parsedFilters = convertPythonToFilters(currentFilters, doctype);
                if (parsedFilters && parsedFilters.length) {
                    filter_group.add_filters_to_filter_group(parsedFilters);
                }
            } catch(e) { 
                console.error("Error parsing python filters", e);
                frappe.msgprint(__('Error parsing expression: ') + e.message);
            }
        }
    });
}

function convertFiltersToPython(filters) {
    if (!filters || !filters.length) return "True";
    
    // filters format: [[doctype, field, operator, value], ...]
    const operatorMap = {
        '=': '==',
        '!=': '!=',
        '>': '>',
        '<': '<',
        '>=': '>=',
        '<=': '<=',
        'Like': 'in', // Approximate mapping
        'Not Like': 'not in',
        'In': 'in',
        'Not In': 'not in',
        'is': 'is',
        'like': 'in',
        'not like': 'not in',
        'in': 'in',
        'not in': 'not in'
    };

    return filters.map(f => {
        const field = f[1];
        const op = operatorMap[f[2]] || '==';
        let val = f[3];
        
        // Handle various value types
        if (Array.isArray(val)) {
             // Handle Array -> Tuple
             const quoted = val.map(v => typeof v === 'string' ? `'${v}'` : v);
             val = `(${quoted.join(', ')})`;
        } else if (typeof val === 'string') {
             // If comma separated string for IN operator, convert to tuple
             if ((op === 'in' || op === 'not in') && val.includes(',')) {
                 const parts = val.split(',').map(v => `'${v.trim()}'`);
                 val = `(${parts.join(', ')})`;
             } else {
                 val = `'${val}'`;
             }
        }
        
        // Handle Like/Not Like reversing operands if needed or strict "like"
        // For simplicity using standard python comparison structure
        // No doc. prefix needed for standard frappe.safe_eval(expr, None, doc)
        return `${field} ${op} ${val}`;
    }).join(' and ');
}

function convertPythonToFilters(expression, doctype) {
    // Simple regex parser for field op value
    // Supports AND logic only (which matches Frappe FilterGroup capabilities)
    
    if (!expression) return [];

    const parts = expression.split(/\s+and\s+/i);
    const filters = [];
    
    const opMapReverse = {
        '==': '=',
        '!=': '!=',
        '>': '>',
        '<': '<',
        '>=': '>=',
        '<=': '<=',
        'in': 'in', 
        'not in': 'not in',
        'is': 'is'
    };
    
    // Regex matches: (doc.)?field_name operator 'value' or number or list/tuple
    // Groups: 1=(optional doc.), 2=field, 3=operator, 4=value
    const regex = /(?:doc\.)?(\w+)\s*(==|!=|>=|<=|>|<|in|not in|is)\s*((?:['"].*?['"])|(?:\d+(?:\.\d+)?)|(?:None|True|False)|(?:\[.*?\])|(?:\(.*?\)))/;
    
    for (const part of parts) {
        const match = part.trim().match(regex);
        if (match) {
            const field = match[1]; 
            const op = opMapReverse[match[2]] || '=';
            let val = match[3];
            
            // Unquote string
            if ((val.startsWith("'") && val.endsWith("'")) || (val.startsWith('"') && val.endsWith('"'))) {
                val = val.slice(1, -1);
            }
            // Handle booleans/nulls
            else if (val === 'None') val = '';
            // Handle List/Tuple for 'in' operator
            else if (val.startsWith('[') || val.startsWith('(')) {
                // Convert Python tuple/list string to JS array
                // standardizing quotes to double for JSON parse, simple heuristic
                try {
                    // Replace ' with " and () with []
                    let arrayStr = val.replace(/'/g, '"');
                    if (arrayStr.startsWith('(')) {
                        arrayStr = '[' + arrayStr.slice(1, -1) + ']';
                    }
                    val = JSON.parse(arrayStr);
                } catch(e) {
                    console.warn("Failed to parse list/tuple value", val);
                    // Fallback: strip brackets and standard cleanup if JSON fails?
                    // For now, let it be string if parse fails, though FilterGroup might complain if it expects array
                }
            }
            
            filters.push([doctype, field, op, val]);
        }
    }
    
    return filters;
}

const availableNextNodes = computed(() => {
    return store.graph.elements
        .filter(el => el.position && el.id !== selectedNode.value?.id && el.id !== 'start')
        .map(el => ({ id: el.id, label: el.label || el.id }));
});

function updateLabel(value) {
    if (!selectedNode.value) return;
    selectedNode.value.label = value;
    if (selectedNode.value.data) selectedNode.value.data.action_label = value;
    store.mark_dirty();
}

const outputFields = computed(() => {
    if (!selectedMethod.value?.output_schema) return [];
    try {
        const schema = JSON.parse(selectedMethod.value.output_schema);
        if (Array.isArray(schema)) {
             // Frappe field list format
             return schema.map(f => ({
                 key: f.fieldname,
                 label: f.label || f.fieldname,
                 type: f.fieldtype
             }));
        } else if (schema.properties) {
             // JSON Schema format (fallback)
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

function getOutputMapping(key) {
    const mappingStr = selectedNode.value.data?.output_mapping;
    if (!mappingStr) return '';
    try {
        const mapping = JSON.parse(mappingStr);
        // Structure: source_key -> target_var
        // Use 'vars.' prefix if not present for display? No, store purely the name?
        // Proposal says "Map to Variable Name". Usually users type "my_score".
        // Engine updates `vars.my_score`. 
        // Let's assume user types just the variable name "my_score", and we PREPEND "vars." in storage?
        // OR user types "vars.my_score"? 
        // The UI shows "vars." prefix in a span. So input is "my_score".
        // Storage should be "my_score" or "vars.my_score"?
        // Mapping.py `update_context` handles `vars.my_score` or top-level.
        // It's safer to store `vars.my_score` if we want to be explicit.
        // Let's store "vars.my_score".
        
        let val = mapping[key] || '';
        if (val.startsWith('vars.')) return val.substring(5);
        return val;
    } catch (e) { return ''; }
}

function updateOutputMapping(key, varName) {
    const mappingStr = selectedNode.value.data?.output_mapping || '{}';
    let mapping = {};
    try { mapping = JSON.parse(mappingStr); } catch (e) {}
    
    if (!varName) {
        delete mapping[key];
    } else {
        // Enforce vars. prefix
        mapping[key] = `vars.${varName}`;
    }
    
    updateField('output_mapping', JSON.stringify(mapping));
}

function updateField(key, value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data[key] = value;
    store.mark_dirty();
}

function updateActionType(value) {
    if (!selectedNode.value) return;
    selectedNode.value.type = value.toLowerCase();
    if (selectedNode.value.data) selectedNode.value.data.action_type = value;
    store.mark_dirty();
}

function updateProcessMethod(value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.process_method = value;
    selectedNode.value.data.config = null;
    store.mark_dirty();
}

function updateProcess(value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.process_name = value;
    selectedNode.value.data.operation = null;  // Reset operation when process changes
    selectedNode.value.data.config = null;     // Reset config
    // Clear legacy method if switching to process
    if (value) {
        selectedNode.value.data.process_method = null;
    }
    store.mark_dirty();
}

function updateOperation(value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.operation = value;
    selectedNode.value.data.config = null;  // Reset config when operation changes
    store.mark_dirty();
}

function updateSubRuleName(value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.rule = value;
    // Store in config for backward compat - engine now prioritizes .rule
    selectedNode.value.data.config = JSON.stringify({ "rule": value });
    store.mark_dirty();
}

function selectSubRule(rule) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.rule = rule.name;
    selectedNode.value.data.config = JSON.stringify({ "rule": rule.name });
    subRuleSearch.value = rule.rule_name || rule.name;
    showSubRuleSuggestions.value = false;
    store.mark_dirty();
}

// JSON Config Helpers (For Loop, Switch, Wait) - uses 'config' field with backward compat
function getJsonConfig(key, defaultVal) {
    // Support both new 'config' and legacy 'method_config'
    const configStr = selectedNode.value?.data?.config || selectedNode.value?.data?.method_config;
    if (!configStr) return defaultVal;
    try {
        const config = JSON.parse(configStr);
        return config[key] !== undefined ? config[key] : defaultVal;
    } catch(e) {
        return defaultVal;
    }
}

function updateJsonConfig(key, value) {
    if (!selectedNode.value?.data) return;
    let config = {};
    try {
        config = JSON.parse(selectedNode.value.data.config || selectedNode.value.data.method_config || '{}');
    } catch(e) {}
    
    config[key] = value;
    selectedNode.value.data.config = JSON.stringify(config);
    store.mark_dirty();
}

const newCaseValue = ref('');
const newCaseTarget = ref('');

function addSwitchCase() {
    if (!newCaseValue.value || !newCaseTarget.value) return;
    
    let config = {};
    try {
        config = JSON.parse(selectedNode.value.data.config || selectedNode.value.data.method_config || '{}');
    } catch(e) {}
    
    if (!config.cases) config.cases = {};
    config.cases[newCaseValue.value] = newCaseTarget.value;
    
    selectedNode.value.data.config = JSON.stringify(config);
    store.mark_dirty();
    
    newCaseValue.value = '';
    newCaseTarget.value = '';
}

function removeSwitchCase(val) {
    let config = {};
    try {
        config = JSON.parse(selectedNode.value.data.config || selectedNode.value.data.method_config || '{}');
    } catch(e) {}
    
    if (config.cases && config.cases[val]) {
        delete config.cases[val];
        selectedNode.value.data.config = JSON.stringify(config);
        store.mark_dirty();
    }
}

function getNodeLabel(id) {
    const node = store.graph.elements.find(el => el.id === id);
    return node ? (node.label || node.id) : id;
}

function updateNextStep(field, value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data[field] = value || null;
    updateEdge(field, value);
    store.mark_dirty();
}

function updateEdge(field, newTarget) {
    const nodeId = selectedNode.value.id;
    const handleType = field === 'next_step_if_true' ? 
        (selectedNode.value.data?.action_type === 'Condition' ? 'true' : 'default') : 'false';
    
    store.graph.elements = store.graph.elements.filter(el => 
        !(el.source === nodeId && el.sourceHandle === handleType)
    );
    
    if (newTarget) {
        store.graph.elements.push({
            id: `e-${nodeId}-${newTarget}-${handleType}`,
            source: nodeId,
            target: newTarget,
            sourceHandle: handleType
        });
    }
}

function deleteNode() {
    if (selectedNode.value) {
        store.delete_node(selectedNode.value.id);
        emit('close');
    }
}

async function openConfigDialog() {
    // Check for new process_name + operation OR legacy process_method
    const processName = selectedNode.value?.data?.process_name;
    const operationName = selectedNode.value?.data?.operation;
    const methodName = selectedNode.value?.data?.process_method;
    
    let schema = null;
    let dialogTitle = '';
    
    if (processName && operationName) {
        // New file-backed process
        const fields = store.get_operation_config_fields(processName, operationName, null);
        if (fields && fields.length) {
            schema = { fields };
            dialogTitle = `${processName} - ${operationName}`;
        }
    } else if (methodName) {
        // Legacy process method
        schema = await store.get_process_method_schema(methodName);
        dialogTitle = schema?.method_name || methodName;
    }
    
    if (!schema?.fields) {
        frappe.msgprint(__('No configuration available'));
        return;
    }
    
    const parentDoctype = store.rule_doc?.document_type;
    const childTables = schema.child_tables || {};
    const dialogFields = await buildDialogFields(schema.fields, parentDoctype, childTables);
    
    // Parse current config (support both new 'config' and legacy 'method_config')
    let currentConfig = {};
    try {
        const configStr = selectedNode.value.data?.config || selectedNode.value.data?.method_config;
        if (configStr && configStr !== '{}' && configStr !== 'null') {
            currentConfig = JSON.parse(configStr);
        }
    } catch (e) {
        console.error('Failed to parse configuration:', e);
    }
    
    // Pre-populate Table field data in the field definitions
    dialogFields.forEach(f => {
        if (f.fieldtype === 'Table' && currentConfig[f.fieldname]) {
            f.data = currentConfig[f.fieldname];
        } else if (currentConfig[f.fieldname] !== undefined && f.fieldtype !== 'Table') {
            f.default = currentConfig[f.fieldname];
        }
    });
    
    const dialog = new frappe.ui.Dialog({
        title: dialogTitle || __('Configure'),
        fields: dialogFields,
        size: 'large',
        primary_action_label: __('Save'),
        primary_action: () => {
            const values = dialog.get_values();
            if (values) {
                // For Table fields, get data from grid
                dialogFields.forEach(f => {
                    if (f.fieldtype === 'Table') {
                        const field = dialog.fields_dict[f.fieldname];
                        if (field && field.grid) {
                            values[f.fieldname] = field.grid.get_data();
                        }
                    }
                });
                
                selectedNode.value.data.config = JSON.stringify(values);
                store.mark_dirty();
                frappe.show_alert({ message: __('Configuration saved'), indicator: 'green' });
            }
            dialog.hide();
        }
    });
    
    dialog.show();
    
    // For Table fields, refresh grid with data after dialog is shown
    setTimeout(() => {
        dialogFields.forEach(f => {
            if (f.fieldtype === 'Table' && currentConfig[f.fieldname]) {
                const field = dialog.fields_dict[f.fieldname];
                if (field && field.grid) {
                    // Clear and set data
                    field.grid.df.data = currentConfig[f.fieldname];
                    field.grid.refresh();
                }
            }
        });
        
        // Set non-table values
        const nonTableConfig = {};
        Object.keys(currentConfig).forEach(key => {
            const field = dialogFields.find(f => f.fieldname === key);
            if (field && field.fieldtype !== 'Table') {
                nonTableConfig[key] = currentConfig[key];
            }
        });
        if (Object.keys(nonTableConfig).length > 0) {
            dialog.set_values(nonTableConfig);
        }
    }, 150);
}

async function buildDialogFields(schemaFields, parentDoctype, childTables = {}) {
    const fields = [];
    
    for (const field of schemaFields) {
        const mapped = await mapSchemaField(field, parentDoctype, childTables);
        if (mapped) {
            // Handle array of fields (e.g., Table expands to label + table)
            if (Array.isArray(mapped)) {
                fields.push(...mapped);
            } else {
                fields.push(mapped);
            }
        }
    }
    
    return fields;
}

async function mapSchemaField(field, parentDoctype, childTables) {
    const { fieldname, fieldtype, label, reqd, options, description } = field;
    const defaultVal = field.default;
    
    switch (fieldtype) {
        case 'DocField':
            // Single field picker → Autocomplete
            return {
                fieldname,
                fieldtype: 'Autocomplete',
                label,
                reqd,
                description,
                options: await getFieldOptions(options, parentDoctype)
            };
        
        case 'MultiDocField':
            // Multi field picker → MultiSelectList (MultiCheck crashes in Dialogs)
            const multiOptions = await getFieldOptions(options, parentDoctype);
            return {
                fieldname,
                fieldtype: 'MultiSelectList',
                label,
                reqd,
                description,
                options: multiOptions
            };
        
        case 'Table':
            // Inline table → Table control with child fields
            // Check table_fields from process adapter OR childTables from schema
            const childSchema = field.table_fields || childTables[options] || [];
            if (!childSchema.length) {
                console.warn(`No table_fields or child_tables definition for: ${options}`);
                return null;
            }
            
            // Map child fields recursively
            const childFields = [];
            for (const cf of childSchema) {
                const mappedChild = await mapSchemaField(cf, parentDoctype, {});
                if (mappedChild && !Array.isArray(mappedChild)) {
                    // For table child fields, convert Autocomplete to Data with options
                    if (mappedChild.fieldtype === 'Autocomplete') {
                        mappedChild.fieldtype = 'Select';
                        mappedChild.options = mappedChild.options?.map(o => o.value || o).join('\n') || '';
                    }
                    if (mappedChild.fieldtype === 'MultiCheck') {
                        mappedChild.fieldtype = 'Select';
                        mappedChild.options = mappedChild.options?.map(o => o.value || o).join('\n') || '';
                    }
                    mappedChild.in_list_view = 1;
                    childFields.push(mappedChild);
                }
            }
            
            return {
                fieldname,
                fieldtype: 'Table',
                label,
                reqd,
                description,
                fields: childFields,
                data: [],
                cannot_add_rows: false,
                in_place_edit: false
            };
        
        case 'MultiSelect':
            // Multi-select → MultiSelectList
            const selectOpts = parseSelectOptions(options);
            return {
                fieldname,
                fieldtype: 'MultiSelectList',
                label,
                reqd,
                description,
                options: selectOpts
            };
        
        case 'Percent':
            // Percent → Float with description
            return {
                fieldname,
                fieldtype: 'Float',
                label,
                reqd,
                description: description || 'Value from 0-100',
                default: defaultVal
            };
        
        default:
            // Standard Frappe fieldtype - pass through
            return {
                fieldname,
                fieldtype,
                label,
                reqd,
                options,
                description,
                default: defaultVal
            };
    }
}

async function getFieldOptions(optionsRef, parentDoctype) {
    let targetDoctype = parentDoctype;
    
    if (optionsRef === 'parent.document_type') {
        targetDoctype = parentDoctype;
    } else if (optionsRef && !optionsRef.includes('.')) {
        targetDoctype = optionsRef;
    }
    
    if (!targetDoctype) return [];
    
    try {
        const result = await frappe.call({
            method: 'flexirule.ruleflow.api.get_doctype_fields',
            args: { doctype: targetDoctype }
        });
        
        if (result.message?.parent_fields) {
            const opts = result.message.parent_fields.map(f => ({
                value: f.value,
                label: `${f.label} (${f.fieldtype})`
            }));
            
            // Add child table fields
            if (result.message.child_tables) {
                result.message.child_tables.forEach(table => {
                    opts.push({ value: '', label: `── ${table.table_label} ──`, disabled: true });
                    table.fields.forEach(f => {
                        opts.push({ value: f.value, label: `  ${f.label}` });
                    });
                });
            }
            
            return opts;
        }
    } catch (e) {
        console.error('Failed to fetch field options:', e);
    }
    
    return [];
}

function parseSelectOptions(options) {
    if (!options) return [];
    return options.split('\n').filter(Boolean).map(opt => ({
        value: opt.trim(),
        label: opt.trim()
    }));
}

</script>

<style scoped>
.rule-sidebar {
    width: 280px;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-left: 1px solid var(--border-color);
}

.sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 15px;
    border-bottom: 1px solid var(--border-color);
}

.sidebar-header h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
}

.btn-close {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: var(--text-muted);
    padding: 0;
}

.sidebar-content {
    flex: 1;
    padding: 15px;
    overflow-y: auto;
}

.form-group {
    margin-bottom: 12px;
}

.form-group label {
    display: block;
    font-size: 11px;
    font-weight: 500;
    margin-bottom: 4px;
    color: var(--text-muted);
    text-transform: uppercase;
}

.form-control {
    width: 100%;
    padding: 6px 10px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 13px;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
}

hr {
    margin: 15px 0;
    border: none;
    border-top: 1px solid var(--border-color);
}

.w-100 { width: 100%; }
.mt-3 { margin-top: 15px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }

.suggestions-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.suggestion-item {
    padding: 8px 10px;
    cursor: pointer;
    border-bottom: 1px solid var(--border-color-muted);
}
.suggestion-item:hover {
    background-color: var(--bg-light-gray);
}
.suggestion-name {
    font-weight: 500;
    font-size: 13px;
}
.suggestion-path {
    font-size: 11px;
    color: var(--text-muted);
}
.input-group {
    display: flex;
    gap: 5px;
}
.relative { position: relative; }
.case-list {
    max-height: 150px;
    overflow-y: auto;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 5px;
}
.case-item {
    background-color: var(--bg-light-gray);
}
</style>
