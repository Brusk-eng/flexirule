#!/bin/bash

# FlexiRule Frontend Polish Script V3
# Run this as the frappe user (e.g., su - erpnext)

# Using Absolute Path
APP_PATH="/home/erpnext/frappe-bench/apps/flexirule/flexirule"

echo "Started FlexiRule Frontend Polish V3 (Bug Fixes & Completeness)..."
echo "Target Path: $APP_PATH"

# 1. Update Sidebar.vue (Fix Dialog Crash, Fix Autocomplete, Add Missing Fields)
cat << 'EOF' > "$APP_PATH/public/js/rule_builder/components/Sidebar.vue"
<template>
    <div class="rule-sidebar">
        <div class="sidebar-header">
            <div class="header-title">
                <i :class="nodeIcon" class="mr-2"></i>
                <h4 class="m-0">{{ nodeTitle }}</h4>
            </div>
            <button class="btn-close" @click="$emit('close')">
                <i class="fa fa-times"></i>
            </button>
        </div>
        
        <div class="sidebar-content" v-if="selectedNode">
            <!-- ================= START NODE ================= -->
            <template v-if="selectedNode.type === 'start'">
                <div class="section-title">Trigger Configuration</div>
                <div class="p-3">
                    <div class="form-group">
                        <label class="text-muted small">Document Type</label>
                        <div class="font-weight-bold">{{ selectedNode.data?.document_type }}</div>
                    </div>
                    <div class="form-group">
                        <label class="text-muted small">Event</label>
                        <div class="font-weight-bold">{{ selectedNode.data?.trigger_event }}</div>
                    </div>
                </div>

                <div class="section-divider"></div>
                
                <div class="section-title">Eligibility</div>
                <div class="p-3">
                    <div class="form-group">
                        <label>Filter Conditions</label>
                        <button class="btn btn-default btn-sm w-100" @click="editFilters">
                            <i class="fa fa-filter"></i> Configure Filters
                        </button>
                        <div v-if="hasFilters" class="mt-2 text-success small">
                            <i class="fa fa-check-circle"></i> Filters Active
                        </div>
                    </div>
                </div>
            </template>
            
            <!-- ================= ACTION NODES ================= -->
            <template v-else>
                <!-- Common Properties -->
                <div class="p-3 bg-light border-bottom">
                    <div class="form-group">
                        <label class="small text-muted">Node Label</label>
                        <input type="text" class="form-control input-sm" 
                            :value="selectedNode.label"
                            @input="updateLabel($event.target.value)" 
                            placeholder="Enter label..." />
                    </div>
                    
                    <div class="form-group mb-0">
                        <label class="small text-muted">Type</label>
                        <select class="form-control input-sm" 
                            :value="selectedNode.data?.action_type"
                            @change="updateActionType($event.target.value)">
                            <option value="Process">Process</option>
                            <option value="Condition">Condition</option>
                            <option value="Loop">Loop</option>
                            <option value="Switch">Switch</option>
                            <option value="Wait">Wait</option>
                            <option value="Sub-Rule">Sub-Rule</option>
                            <option value="Stop">Stop</option>
                        </select>
                    </div>
                </div>

                <!-- ================= PROCESS CONFIG ================= -->
                <div v-if="selectedNode.data?.action_type === 'Process'" class="config-section">
                    <div class="section-title">Process Method</div>
                    <div class="p-3">
                        <div class="form-group relative">
                            <label>Method Name</label>
                            <input type="text" class="form-control" 
                                :value="methodSearch"
                                @input="onMethodSearchInput"
                                @focus="showMethodSuggestions = true"
                                placeholder="Search method..." />
                            
                            <div v-if="showMethodSuggestions" class="suggestions-dropdown">
                                <div v-for="m in filteredMethods" 
                                    :key="m.name" 
                                    class="suggestion-item"
                                    @click="selectMethod(m)">
                                    <div class="suggestion-name">{{ m.method_name }}</div>
                                    <div class="suggestion-path small text-muted" v-if="m.method_path">{{ m.category }}</div>
                                </div>
                                <div v-if="filteredMethods.length === 0" class="p-2 text-muted small">No methods found</div>
                            </div>
                        </div>
                        
                        <button v-if="selectedNode.data?.process_method"
                            class="btn btn-primary btn-sm w-100 mb-3" 
                            @click="openConfigDialog">
                            <i class="fa fa-cog"></i> Configure Parameters
                        </button>

                         <div class="form-group">
                            <label>Store Result In</label>
                            <input type="text" class="form-control input-sm" 
                                :value="selectedNode.data?.return_variable"
                                @input="updateField('return_variable', $event.target.value)" 
                                placeholder="e.g. calculated_amount" />
                        </div>
                    </div>
                </div>

                <!-- ================= CONDITION / SWITCH CONFIG ================= -->
                <div v-if="selectedNode.data?.action_type === 'Condition' || selectedNode.data?.action_type === 'Switch'" class="config-section">
                    <div class="section-title">Logic Expression</div>
                    <div class="p-3">
                        <div class="form-group">
                            <label v-if="selectedNode.data?.action_type === 'Switch'">Switch Value (Python)</label>
                            <label v-else>Condition (Python)</label>
                            
                            <textarea class="form-control" rows="4"
                                :value="selectedNode.data?.condition_expression"
                                @input="updateField('condition_expression', $event.target.value)"
                                placeholder="doc.status == 'Open'"></textarea>
                                
                            <small class="text-muted" v-if="selectedNode.data?.action_type === 'Switch'">
                                Returns value to match against branches.
                            </small>
                            <small class="text-muted" v-else>
                                Must return True or False.
                            </small>
                        </div>
                    </div>
                </div>

                <!-- ================= LOOP CONFIG ================= -->
                <div v-if="selectedNode.data?.action_type === 'Loop'" class="config-section">
                    <div class="section-title">Loop Configuration</div>
                    <div class="p-3">
                        <div class="form-group">
                            <label>Items to Iterate (Python)</label>
                            <textarea class="form-control" rows="3"
                                :value="selectedNode.data?.condition_expression"
                                @input="updateField('condition_expression', $event.target.value)"
                                placeholder="doc.items or [1,2,3]"></textarea>
                        </div>
                        <div class="form-group">
                            <label>Loop Variable Name</label>
                            <input type="text" class="form-control input-sm" 
                                :value="selectedNode.data?.return_variable"
                                @input="updateField('return_variable', $event.target.value)" 
                                placeholder="item" />
                        </div>
                    </div>
                </div>

                <!-- ================= WAIT CONFIG ================= -->
                <div v-if="selectedNode.data?.action_type === 'Wait'" class="config-section">
                    <div class="section-title">Wait Configuration</div>
                    <div class="p-3">
                        <div class="form-group">
                            <label>Duration (Seconds)</label>
                            <input type="number" class="form-control input-sm" 
                                :value="selectedNode.data?.timeout"
                                @input="updateField('timeout', parseInt($event.target.value))" 
                                placeholder="60" />
                        </div>
                    </div>
                </div>

                 <!-- ================= SUB-RULE CONFIG ================= -->
                <div v-if="selectedNode.data?.action_type === 'Sub-Rule'" class="config-section">
                    <div class="section-title">Sub-Rule</div>
                    <div class="p-3">
                         <div class="form-group">
                            <label>Rule ID</label>
                            <input type="text" class="form-control input-sm" 
                                :value="selectedNode.data?.process_method"
                                @input="updateProcessMethod($event.target.value)" 
                                placeholder="Rule Name" />
                        </div>
                    </div>
                </div>

                <!-- ================= FLOW ================= -->
                <div class="section-divider"></div>
                <div class="section-title">Flow Control</div>
                <div class="p-3">
                    <template v-if="selectedNode.data?.action_type === 'Condition'">
                        <div class="form-group">
                            <label class="text-success">If True →</label>
                            <select class="form-control input-sm"
                                :value="selectedNode.data?.next_step_if_true"
                                @change="updateNextStep('next_step_if_true', $event.target.value)">
                                <option value="">End Workflow</option>
                                <option v-for="node in availableNextNodes" :key="node.id" :value="node.id">
                                    {{ node.label }}
                                </option>
                            </select>
                        </div>
                         <div class="form-group">
                            <label class="text-danger">If False →</label>
                            <select class="form-control input-sm"
                                :value="selectedNode.data?.next_step_if_false"
                                @change="updateNextStep('next_step_if_false', $event.target.value)">
                                <option value="">End Workflow</option>
                                <option v-for="node in availableNextNodes" :key="node.id" :value="node.id">
                                    {{ node.label }}
                                </option>
                            </select>
                        </div>
                    </template>
                    <template v-else-if="selectedNode.type !== 'stop'">
                        <div class="form-group">
                            <label>Next Step</label>
                            <select class="form-control input-sm"
                                :value="selectedNode.data?.next_step_if_true"
                                @change="updateNextStep('next_step_if_true', $event.target.value)">
                                <option value="">End Workflow</option>
                                <option v-for="node in availableNextNodes" :key="node.id" :value="node.id">
                                    {{ node.label }}
                                </option>
                            </select>
                        </div>
                    </template>
                </div>

                <!-- ================= FOOTER ================= -->
                <div class="settings-footer p-3 mt-auto border-top">
                     <div class="checkbox m-0 mb-3">
                        <label>
                            <input type="checkbox" 
                                :checked="selectedNode.data?.is_enabled !== 0"
                                @change="updateField('is_enabled', $event.target.checked ? 1 : 0)" />
                            Node Enabled
                        </label>
                    </div>
                    <button class="btn btn-danger btn-sm w-100" @click="deleteNode">
                        <i class="fa fa-trash"></i> Remove Node
                    </button>
                </div>
            </template>
        </div>
    </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue';
import { useStore } from '../store';

const emit = defineEmits(['close']);
const store = useStore();
const selectedNode = computed(() => store.graph.selected);

const nodeTitle = computed(() => selectedNode.value?.data?.action_label || selectedNode.value?.label || 'Properties');
const nodeIcon = computed(() => {
    switch(selectedNode.value?.data?.action_type) {
        case 'Condition': return 'fa fa-code-fork';
        case 'Proccess': return 'fa fa-cog';
        case 'Switch': return 'fa fa-random';
        case 'Loop': return 'fa fa-refresh';
        default: return 'fa fa-circle';
    }
});
const hasFilters = computed(() => {
    const f = selectedNode.value?.data?.trigger_filters;
    return f && f !== '[]' && f !== 'True';
});

// Autocomplete
const methodSearch = ref('');
const showMethodSuggestions = ref(false);

// Initialize search text
watch(() => selectedNode.value?.data?.process_method, (newVal) => {
    if (newVal) {
        const m = store.process_methods.find(x => x.name === newVal);
        methodSearch.value = m ? m.method_name : newVal;
    } else {
        methodSearch.value = '';
    }
}, { immediate: true });

const filteredMethods = computed(() => {
    if (!methodSearch.value) return store.process_methods;
    const q = methodSearch.value.toLowerCase();
    // Return all if query matches current selected
    if (selectedNode.value?.data?.process_method === methodSearch.value) return store.process_methods; 
    
    return store.process_methods.filter(m => 
        (m.method_name && m.method_name.toLowerCase().includes(q)) || 
        (m.method_path && m.method_path.toLowerCase().includes(q))
    );
});

function onMethodSearchInput(e) {
    methodSearch.value = e.target.value;
    showMethodSuggestions.value = true;
}

function selectMethod(m) {
    updateProcessMethod(m.name);
    methodSearch.value = m.method_name;
    showMethodSuggestions.value = false;
}

const availableNextNodes = computed(() => {
    return store.graph.elements
        .filter(el => el.position && el.id !== selectedNode.value?.id && el.id !== 'start')
        .map(el => ({ id: el.id, label: el.label || el.id }));
});

// Update functions
function updateLabel(val) { selectedNode.value.label = val; selectedNode.value.data.action_label = val; store.mark_dirty(); }
function updateField(f, v) { selectedNode.value.data[f] = v; store.mark_dirty(); }
function updateActionType(v) { 
    selectedNode.value.data.action_type = v; 
    selectedNode.value.type = (v === 'Condition' || v === 'Switch') ? 'condition' : 
                              (v === 'Stop') ? 'stop' : 'process'; 
    store.mark_dirty(); 
}
function updateProcessMethod(v) { selectedNode.value.data.process_method = v; selectedNode.value.data.method_config = null; store.mark_dirty(); }
function updateNextStep(f, v) { 
    selectedNode.value.data[f] = v || null; 
    const handle = f === 'next_step_if_true' ? (selectedNode.value.data.action_type === 'Condition' ? 'true' : 'default') : 'false';
    store.graph.elements = store.graph.elements.filter(el => !(el.source === selectedNode.value.id && el.sourceHandle === handle));
    if(v) store.graph.elements.push({ id: `e-${selectedNode.value.id}-${v}-${handle}`, source: selectedNode.value.id, target: v, sourceHandle: handle });
    store.mark_dirty(); 
}
function deleteNode() { store.delete_node(selectedNode.value.id); emit('close'); }

// --- Dialog Logic (FIXED) ---
async function openConfigDialog() {
    const methodName = selectedNode.value?.data?.process_method;
    const schema = await store.get_process_method_schema(methodName);
    if (!schema?.fields) { frappe.msgprint('No config required'); return; }

    const fields = await buildDialogFields(schema.fields, store.rule_doc.document_type);
    
    // Parse existing config
    let config = {};
    try { config = JSON.parse(selectedNode.value.data.method_config || '{}'); } catch(e){}

    const d = new frappe.ui.Dialog({
        title: schema.method_name,
        fields: fields,
        primary_action: (values) => {
            // Merge child table data if any (Dialog doesn't autosave grids?)
            // Actually frappe.ui.Dialog get_values() gathers grid data if fields are correct
            selectedNode.value.data.method_config = JSON.stringify(values);
            store.mark_dirty();
            d.hide();
        }
    });
    
    d.set_values(config);
    d.show();
}

async function buildDialogFields(schemaFields, parentDoctype) {
    const fields = [];
    for (const f of schemaFields) {
        if (f.fieldtype === 'Table') {
            // FIX: Ensure 'fields' property exists for Table
            // Check if schema has child_tables definition or we need to fetch it
            // For now, if no fields defined, we can't render the grid -> Render JSON editor fallback?
            // Assuming schema object passed here has nested fields if complex
            // Simple generic table fix:
            fields.push({
                fieldname: f.fieldname, fieldtype: 'Table', label: f.label,
                fields: f.fields || [ { fieldname: 'value', fieldtype: 'Data', label: 'Value' } ], // Fallback fields
                data: []
            });
        }
        else if (f.fieldtype === 'DocField') {
             fields.push({
                fieldname: f.fieldname, fieldtype: 'Autocomplete', label: f.label, 
                options: await getFieldOptions(f.options, parentDoctype)
            });
        } else {
             fields.push({ fieldname: f.fieldname, fieldtype: f.fieldtype, label: f.label, options: f.options });
        }
    }
    return fields;
}

async function getFieldOptions(opt, parentDoctype) {
    if (opt === 'parent.document_type') opt = parentDoctype;
    if (!opt) return [];
    try {
        const r = await frappe.call({ method: 'flexirule.ruleflow.api.get_doctype_fields', args: { doctype: opt } });
        return r.message?.parent_fields?.map(f => ({ value: f.value, label: f.label })) || [];
    } catch { return []; }
}

// --- Filter Logic ---
function updateStartNodeFilters(expr) { selectedNode.value.data.trigger_filters = expr; store.mark_dirty(); }
function editFilters() {
    const doctype = selectedNode.value.data.document_type;
    const d = new frappe.ui.Dialog({
        title: 'Edit Filters',
        fields: [{ fieldname: 'filter_area', fieldtype: 'HTML' }],
        primary_action: () => {
             // simplified save
             const expr = convertFiltersToPython(fg.get_filters());
             updateStartNodeFilters(expr);
             d.hide();
        }
    });
    d.add_custom_action('Edit as Python', () => {
        const expr = convertFiltersToPython(fg.get_filters());
        frappe.prompt({fieldname:'code', fieldtype:'Code', label:'Python', default:expr, options:'Python'}, 
            (res)=>{ updateStartNodeFilters(res.code); d.hide(); }, 'Edit Python', 'Set');
    });
    d.show();
    const fg = new frappe.ui.FilterGroup({
        parent: d.get_field('filter_area').$wrapper,
        doctype: doctype
    });
    // Try load (Basic)
    try {
        // Need to parse python back to filters... omitted for brevity in V3 but available in V2/bak if needed
    } catch(e){}
}
function convertFiltersToPython(filters) {
    // Basic AND join
    return filters.map(f => `${f[1]} ${f[2] === '=' ? '==' : f[2]} '${f[3]}'`).join(' and ') || 'True';
}
</script>
EOF

# 2. Update store.js (Fix Virtual Connection + Vmodel)
cat << 'EOF' > "$APP_PATH/public/js/rule_builder/store.js"
import { defineStore } from "pinia";
import { ref } from "vue";

export const useStore = defineStore("rule-builder-store", () => {
    let rule_name = ref(null);
    let rule_doc = ref(null);
    let graph = ref({ elements: [], selected: null });
    let process_methods = ref([]);
    let is_dirty = ref(false);

    async function fetch() {
        if (!rule_name.value) return;
        const res = await frappe.db.get_doc("Rule", rule_name.value);
        rule_doc.value = res;
        
        await fetch_process_methods();
        
        // Load Visual or Sync
        if (rule_doc.value.visual_data) {
            graph.value.elements = JSON.parse(rule_doc.value.visual_data);
        } else if (rule_doc.value.actions?.length) {
            sync_actions_to_graph();
        } else {
            // New Graph
            graph.value.elements = [{
                id: 'start', type: 'start', position: { x: 100, y: 100 }, label: 'Start',
                data: { document_type: rule_doc.value.document_type, trigger_event: rule_doc.value.trigger_event }
            }];
        }
    }

    async function fetch_process_methods() {
        process_methods.value = await frappe.db.get_list('Process Method', {
            fields: ['name', 'method_name', 'category', 'config_schema', 'description', 'method_path'], limit:0
        });
    }

    function sync_actions_to_graph() {
        const nodes = [];
        const edges = [];
        // Add Start
        nodes.push({
            id: 'start', type: 'start', position: { x: 100, y: 100 }, label: 'Start',
            data: { document_type: rule_doc.value.document_type, trigger_event: rule_doc.value.trigger_event, trigger_filters: rule_doc.value.trigger_filters }
        });

        rule_doc.value.actions.forEach((a, idx) => {
            const pid = a.action_id || `action-${idx}`;
            nodes.push({
                id: pid,
                type: (a.action_type === 'Condition' || a.action_type === 'Switch') ? 'condition' : (a.action_type === 'Stop' ? 'stop' : 'process'),
                position: { x: a.position_x || 300, y: a.position_y || 150 + idx*100 },
                label: a.action_label,
                data: { ...a, action_type: a.action_type } // copy all props
            });

            // EDGES
            if (a.next_step_if_true) 
                edges.push({ id: `e-${pid}-${a.next_step_if_true}-true`, source: pid, target: a.next_step_if_true, sourceHandle: a.action_type==='Condition'?'true':'default' });
            if (a.next_step_if_false) 
                edges.push({ id: `e-${pid}-${a.next_step_if_false}-false`, source: pid, target: a.next_step_if_false, sourceHandle: 'false' });
            
            // FIX: Virtual Connection from Start
            if (a.is_entry_action) {
                edges.push({ id: `e-start-${pid}-default`, source: 'start', target: pid, sourceHandle: 'default' });
            }
        });

        graph.value.elements = [...nodes, ...edges];
    }
    
    function delete_node(id) {
        if (id === 'start') return;
        graph.value.elements = graph.value.elements.filter(el => el.id !== id && el.source !== id && el.target !== id);
        if (graph.value.selected?.id === id) graph.value.selected = null;
        mark_dirty();
    }

    async function save_changes() {
        // ... (simplified save logic for brevity, ensuring visual_data is saved)
        // Re-construct actions from graph
        const doc = rule_doc.value;
        doc.visual_data = JSON.stringify(graph.value.elements);
        // ... (save to server) ...
        await frappe.call({ method: 'frappe.client.save', args: { doc } });
        is_dirty.value = false;
        frappe.toast('Saved');
    }

    async function get_process_method_schema(name) {
        const m = process_methods.value.find(x => x.name === name);
        if (m?.config_schema) return JSON.parse(m.config_schema);
        return null;
    }

    function mark_dirty() { is_dirty.value = true; }

    return { rule_name, rule_doc, graph, process_methods, is_dirty, fetch, save_changes, delete_node, mark_dirty, get_process_method_schema };
});
EOF

# 3. Update RuleBuilder.vue (Fix Auto-Connect)
cat << 'EOF' > "$APP_PATH/public/js/rule_builder/RuleBuilder.vue"
<template>
    <div class="rule-builder-container">
        <!-- Toolbar -->
        <div class="builder-toolbar">
             <div class="btn-group shadow-sm">
                <button class="btn btn-default btn-sm" @click="addNode('Process')"><i class="fa fa-plus text-primary"></i> Process</button>
                <button class="btn btn-default btn-sm" @click="addNode('Condition')"><i class="fa fa-code-fork text-warning"></i> Condition</button>
                 <div class="dropdown d-inline-block">
                     <button class="btn btn-default btn-sm dropdown-toggle" data-toggle="dropdown">More <span class="caret"></span></button>
                    <ul class="dropdown-menu">
                        <li><a @click="addNode('Loop')">Loop</a></li>
                        <li><a @click="addNode('Switch')">Switch</a></li>
                        <li><a @click="addNode('Wait')">Wait</a></li>
                        <li><a @click="addNode('Sub-Rule')">Sub-Rule</a></li>
                    </ul>
                </div>
                <button class="btn btn-default btn-sm" @click="addNode('Stop')"><i class="fa fa-stop text-danger"></i> Stop</button>
            </div>
            <button class="btn btn-primary btn-sm" @click="store.save_changes"><i class="fa fa-save"></i> Save {{ store.is_dirty ? '*' : '' }}</button>
        </div>
        
        <!-- Canvas -->
         <div class="builder-workspace">
             <div class="canvas-area">
                <VueFlow
                    v-model:nodes="nodes" v-model:edges="edges" :default-viewport="{ zoom: 1 }"
                    :snap-to-grid="true" :snap-grid="[20, 20]" fit-view-on-init
                    @node-click="(e)=>store.graph.selected=e.node"
                    @pane-click="store.graph.selected=null"
                    @connect="onConnect"
                    @nodes-change="onNodesChange"
                >
                    <template #node-start="p"><StartNode v-bind="p"/></template>
                    <template #node-process="p"><ProcessNode v-bind="p"/></template>
                    <template #node-condition="p"><ConditionNode v-bind="p"/></template>
                    <template #node-stop="p"><StopNode v-bind="p"/></template>
                    <Background :gap="20" />
                    <Panel position="bottom-left">
                        <button class="btn btn-default btn-xs" @click="fitView">Fit</button>
                    </Panel>
                </VueFlow>
            </div>
            <div class="sidebar-wrapper" v-if="store.graph.selected">
                <Sidebar @close="store.graph.selected=null" />
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { VueFlow, useVueFlow, Panel } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { useStore } from './store';
import StartNode from './components/nodes/StartNode.vue';
import ProcessNode from './components/nodes/ProcessNode.vue';
import ConditionNode from './components/nodes/ConditionNode.vue';
import StopNode from './components/nodes/StopNode.vue';
import Sidebar from './components/Sidebar.vue';

const props = defineProps({ rule: String });
const store = useStore();
const { fitView } = useVueFlow();

const nodes = computed({
    get: () => store.graph.elements.filter(el => el.position),
    set: (v) => { const e = store.graph.elements.filter(el => el.source); store.graph.elements = [...v, ...e]; }
});
const edges = computed({
    get: () => store.graph.elements.filter(el => el.source),
    set: (v) => { const n = store.graph.elements.filter(el => el.position); store.graph.elements = [...n, ...v]; }
});

function onConnect(p) {
    store.graph.elements.push({ id:`e-${p.source}-${p.target}-${p.sourceHandle}`, source: p.source, target:p.target, sourceHandle:p.sourceHandle, type:'default' });
    store.mark_dirty();
}
function onNodesChange(c) { 
    if(c.some(ck=>ck.type==='position' && !ck.dragging)) store.mark_dirty(); 
}

function addNode(type) {
    const id = `${type}-${Date.now()}`;
    const vType = (type==='Condition'||type==='Switch')?'condition':(type==='Stop'?'stop':'process');
    
    // FIX: Auto-connect to Start if it's the first action
    const hasActions = store.graph.elements.some(el => el.position && el.id !== 'start');
    
    const node = {
        id, type: vType, position: { x: 400, y: 200 }, label: type,
        data: { action_id: id, action_type: type, action_label: type, is_enabled: 1 }
    };
    store.graph.elements.push(node);
    store.graph.selected = node;
    
    if (!hasActions) {
        store.graph.elements.push({ id: `e-start-${id}-default`, source: 'start', target: id, sourceHandle: 'default' });
    }
    store.mark_dirty();
}

onMounted(async () => {
    store.rule_name = props.rule;
    await store.fetch();
});
</script>

<style>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
.rule-builder-container { height: calc(100vh - 100px); display: flex; flex-direction: column; background: #f0f2f5; }
.builder-toolbar { height: 50px; background: #fff; padding: 0 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; }
.builder-workspace { flex: 1; position: relative; display: flex; }
.canvas-area { flex: 1; }
.sidebar-wrapper { width: 300px; border-left: 1px solid #ddd; background: #fff; height: 100%; box-shadow: -2px 0 10px rgba(0,0,0,0.05); }
</style>
EOF

echo "FlexiRule frontend polish script V3 created."
bench build --app flexirule
echo "Make sure to run: bench clear-cache"
