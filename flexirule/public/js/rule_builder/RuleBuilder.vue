<template>
    <div class="rule-builder-container">
        <!-- Toolbar -->
        <div class="builder-toolbar">
            <div class="toolbar-left">
                <div class="btn-group">
                    <button class="btn btn-xs btn-default" @click="addNode('process')" :title="__('Add Process')">
                        <i class="fa fa-cog"></i> {{ __("Process") }}
                    </button>
                    <button class="btn btn-xs btn-default" @click="addNode('condition')" :title="__('Add Condition')">
                        <i class="fa fa-code-fork"></i> {{ __("Condition") }}
                    </button>
                    <button class="btn btn-xs btn-default" @click="addNode('loop')" :title="__('Add Loop')">
                         <i class="fa fa-refresh"></i> {{ __("Loop") }}
                    </button>
                    <button class="btn btn-xs btn-default" @click="addNode('switch')" :title="__('Add Switch')">
                        <i class="fa fa-code-fork" style="transform: rotate(90deg)"></i> {{ __("Switch") }}
                    </button>
                    <button class="btn btn-xs btn-default" @click="addNode('wait')" :title="__('Add Wait')">
                        <i class="fa fa-clock-o"></i> {{ __("Wait") }}
                    </button>
                    <button class="btn btn-xs btn-default" @click="addNode('sub-rule')" :title="__('Add Sub-Rule')">
                         <i class="fa fa-cube"></i> {{ __("Sub-Rule") }}
                    </button>
                    <button class="btn btn-xs btn-default" @click="addNode('stop')" :title="__('Add Stop')">
                        <i class="fa fa-stop-circle"></i> {{ __("Stop") }}
                    </button>
                </div>
            </div>
            
            <div class="toolbar-center">
                <div v-if="store.rule_doc" class="rule-status-toggle">
                     <!-- Rule Active Toggle -->
                    <label class="switch" :title="__('Enable/Disable Rule')">
                        <input type="checkbox" :checked="store.rule_doc.is_active" @change="toggleRuleActive">
                        <span class="slider round"></span>
                    </label>
                    <span class="status-label">{{ store.rule_doc.is_active ? __('Active') : __('Draft') }}</span>

                    <span class="divider">|</span>

                    <!-- Show Disabled Nodes Toggle -->
                    <label class="switch small-switch" :title="__('Show Disabled Nodes')">
                        <input type="checkbox" v-model="showDisabledNodes">
                        <span class="slider round"></span>
                    </label>
                    <span class="status-label">{{ __("Show Disabled") }}</span>
                </div>
            </div>

            <div class="toolbar-right">
                <button class="btn btn-xs btn-primary mr-2" @click="testRule()" :title="__('Dry Run')">
                    <i class="fa fa-play"></i> {{ __("Test") }}
                </button>
                <button class="btn btn-xs btn-default" @click="fitView()" :title="__('Fit View')">
                    <i class="fa fa-expand"></i>
                </button>
            </div>
        </div>
        
        <!-- Main Canvas + Sidebar -->
        <div class="builder-main">
            <div class="sidebar-container" :class="{ 'sidebar-rtl': isRTL }" v-if="showSidebar" @click.stop>
                <Sidebar @close="closeSidebar" />
            </div>
            <div class="canvas-container">
                <VueFlow
                    v-model:nodes="nodes"
                    v-model:edges="edges"
                    :default-viewport="{ zoom: 1 }"
                    :min-zoom="0.2"
                    :max-zoom="2"
                    :snap-to-grid="true"
                    :snap-grid="[15, 15]"
                    fit-view-on-init
                    @node-click="onNodeClick"
                    @pane-click="onPaneClick"
                    @connect="onConnect"
                    @nodes-change="onNodesChange"
                    @edges-change="onEdgesChange"
                    @edge-click="onEdgeClick"
                >
                    <template #node-start="nodeProps">
                        <StartNode v-bind="nodeProps" />
                    </template>
                    <template #node-process="nodeProps">
                        <ProcessNode v-bind="nodeProps" />
                    </template>
                    <template #node-condition="nodeProps">
                        <ConditionNode v-bind="nodeProps" />
                    </template>
                    <template #node-loop="nodeProps">
                        <LoopNode v-bind="nodeProps" />
                    </template>
                    <template #node-stop="nodeProps">
                        <StopNode v-bind="nodeProps" />
                    </template>
                    
                    <Background :gap="15" />
                    <Panel :position="PanelPosition.BottomLeft">
                        <button class="btn btn-sm btn-default mr-2" @click="zoomIn">+</button>
                        <button class="btn btn-sm btn-default mr-2" @click="zoomOut">-</button>
                        <button class="btn btn-sm btn-default" @click="fitView()">{{ __("Fit") }}</button>
                    </Panel>
                </VueFlow>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { VueFlow, useVueFlow, Panel, PanelPosition } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { useStore } from './store';
import { generateShortId } from './utils';

import StartNode from './components/nodes/StartNode.vue';
import ProcessNode from './components/nodes/ProcessNode.vue';
import ConditionNode from './components/nodes/ConditionNode.vue';
import LoopNode from './components/nodes/LoopNode.vue';
import StopNode from './components/nodes/StopNode.vue';
import Sidebar from './components/Sidebar.vue';

const props = defineProps({ rule: String });
const store = useStore();
const { fitView, zoomIn, zoomOut } = useVueFlow();

const showDisabledNodes = ref(true);

const nodes = computed({
    get: () => {
        const disabledIds = store.effectiveDisabledIds || new Set();
        return (store.graph.elements || [])
            .filter(el => {
                if (!el.position) return false;
                if (el.type === 'start') return true;
                // Filtering
                if (!showDisabledNodes.value && el.data?.is_enabled === 0) return false;
                return true;
            })
            .map(el => {
                // Determine effective disablement
                const isEffectiveDisabled = disabledIds.has(el.id);
                // Return shallow copy with updated data
                return {
                    ...el,
                    data: {
                        ...el.data,
                        is_effectively_disabled: isEffectiveDisabled
                    }
                };
            });
    },
    set: (val) => {
        const edges = store.graph.elements.filter(el => el.source);
        const currentIds = new Set(val.map(n => n.id));
        // Preserve hidden nodes
        const hiddenNodes = store.graph.elements.filter(el => el.position && !currentIds.has(el.id));
        store.graph.elements = [...val, ...hiddenNodes, ...edges];
    }
});

const edges = computed({
    get: () => (store.graph.elements || []).filter(el => el.source),
    set: (val) => {
        const nodesList = store.graph.elements.filter(el => el.position);
        store.graph.elements = [...nodesList, ...val];
    }
});

const showSidebar = computed(() => store.graph.selected !== null);
const isRTL = computed(() => document.documentElement.dir === 'rtl');

function closeSidebar() { store.graph.selected = null; }

onMounted(async () => {
    if (props.rule) store.rule_name = props.rule;
    await store.fetch();
    autoConnectStartNode();
    window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => { window.removeEventListener('keydown', handleKeydown); });

function handleKeydown(e) {
    // Save: Ctrl+S
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        store.save_changes();
    }
    // Undo: Ctrl+Z
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        if (store.can_undo()) store.undo();
    }
    // Redo: Ctrl+Y or Ctrl+Shift+Z
    if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        if (store.can_redo()) store.redo();
    }
}

function autoConnectStartNode() {
    const startNode = (store.graph.elements || []).find(el => el.type === 'start');
    if (!startNode) return;
    
    // Check if start node has any outgoing edges
    const hasStartEdge = (store.graph.elements || []).some(el => el.source === startNode.id);
    if (hasStartEdge) return;

    const firstNode = (store.graph.elements || []).find(el => el.position && el.type !== 'start' && el.data?.is_enabled !== 0);
    if (firstNode) {
        store.graph.elements.push({
            id: `e-${startNode.id}-${firstNode.id}`,
            source: startNode.id, target: firstNode.id,
            sourceHandle: 'default', animated: true
        });
    }
}

function onNodeClick(event) { store.graph.selected = event.node; }
function onPaneClick() { store.graph.selected = null; }

function onConnect(params) {
    const newEdge = {
        id: `e-${params.source}-${params.target}-${params.sourceHandle || 'default'}`,
        source: params.source, target: params.target,
        sourceHandle: params.sourceHandle || 'default',
        animated: store.graph.elements.find(el => el.id === params.source)?.type === 'start'
    };
    store.graph.elements.push(newEdge);
    store.mark_dirty();
}

function onNodesChange(changes) {
    const hasDrag = changes.some(c => c.type === 'position' && c.dragging === false);
    if (hasDrag) store.mark_position_change();
}

function onEdgesChange(changes) {
    changes.forEach(change => {
        if (change.type === 'remove') {
            store.delete_edge(change.id);
        }
    });
}

function addNode(type) {
    const id = generateShortId();
    let label = '';
    let actionType = '';
    
    switch(type) {
        case 'process': 
            label = __('New Process'); 
            actionType = 'Process'; 
            break;
        case 'condition': 
            label = __('New Condition'); 
            actionType = 'Condition';
            break;
        case 'switch': 
            label = __('New Switch'); 
            actionType = 'Switch';
            break;
        case 'loop': 
            label = __('Loop'); 
            actionType = 'Loop';
            break;
        case 'wait': 
            label = __('Wait'); 
            actionType = 'Wait';
            break;
        case 'sub-rule': 
            label = __('Sub Rule'); 
            actionType = 'Sub-Rule'; 
            break;
        case 'stop':
            label = __('Stop');
            actionType = 'Stop';
            break;
        default: 
            label = __('New Action');
            actionType = 'Process';
    }

    const newNode = {
        id, type, position: { x: 300, y: 200 }, label,
        data: {
            action_id: id, 
            action_type: actionType,
            action_label: label, 
            is_enabled: 1
        }
    };
    store.graph.elements.push(newNode);
    store.graph.selected = newNode;
    store.mark_dirty();
}

function toggleRuleActive(e) {
    if (store.rule_doc) {
        store.rule_doc.is_active = e.target.checked ? 1 : 0;
        store.mark_dirty();
    }
}

function testRule() {
    if (!store.rule_doc?.document_type) {
        frappe.msgprint(__('Please select a Document Type first'));
        return;
    }
    
    const doctype = store.rule_doc.document_type;
    
    frappe.prompt(
        [
            {
                label: __('Document'),
                fieldname: 'docname',
                fieldtype: 'Link',
                options: doctype,
                reqd: 1,
                description: __('Select a document to test the rule against')
            }
        ],
        (values) => {
            frappe.call({
                method: 'flexirule.ruleflow.api.test_rule',
                args: {
                    rule_name: store.rule_name,
                    doctype: doctype,
                    docname: values.docname
                },
                freeze: true,
                freeze_message: __('Executing rule...'),
                callback: (r) => {
                    if (r.message) {
                        const result = r.message;
                        if (result.success) {
                            frappe.msgprint({
                                title: __('Test Successful'),
                                indicator: 'green',
                                message: `<p>${result.message}</p><details><summary>${__('Execution Log')}</summary><pre>${JSON.stringify(result.execution_log, null, 2)}</pre></details>`
                            });
                        } else {
                            frappe.msgprint({
                                title: __('Test Result'),
                                indicator: result.error ? 'red' : 'orange',
                                message: result.message || result.error
                            });
                        }
                    }
                }
            });
        },
        __('Test Rule'),
        __('Run Test')
    );
}

function onEdgeClick(event, edge) {
    frappe.confirm(
        __('Delete this connection?'),
        () => {
            store.delete_edge(edge.id);
            frappe.show_alert({ message: __('Connection deleted'), indicator: 'green' });
        }
    );
}
</script>

<style>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';

.rule-builder-container {
    display: flex; flex-direction: column;
    height: calc(100vh - var(--navbar-height) - var(--page-head-height) - 60px);
}
.builder-toolbar {
    display: flex; justify-content: space-between; padding: 8px 15px;
    background: var(--fg-color); border-bottom: 1px solid var(--border-color);
}
.builder-main { flex: 1; display: flex; position: relative; overflow: hidden; }
.sidebar-container {
    position: relative; height: 100%; margin-right: 10px;
    border-radius: var(--border-radius-lg); border: 1px solid var(--border-color);
    background-color: var(--fg-color);
}
.canvas-container {
    flex: 1; height: 100%; border-radius: var(--border-radius-lg);
    border: 1px solid var(--border-color); background-color: var(--fg-color);
}
.toolbar-center { display: flex; align-items: center; justify-content: center; flex: 1; }

.rule-status-toggle {
    display: flex; align-items: center; gap: 8px;
    font-size: 13px; font-weight: 500;
}
.divider { color: var(--border-color); margin: 0 10px; }

/* Switch Toggle */
.switch { position: relative; display: inline-block; width: 32px; height: 18px; margin: 0; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
    position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
    background-color: #ccc; transition: .4s; border-radius: 34px;
}
.slider:before {
    position: absolute; content: ""; height: 14px; width: 14px; left: 2px; bottom: 2px;
    background-color: white; transition: .4s; border-radius: 50%;
}
input:checked + .slider { background-color: var(--primary); }
input:focus + .slider { box-shadow: 0 0 1px var(--primary); }
input:checked + .slider:before { transform: translateX(14px); }

.small-switch { width: 28px; height: 16px; }
.small-switch .slider:before { height: 12px; width: 12px; }
.small-switch input:checked + .slider:before { transform: translateX(12px); }

/* RTL sidebar positioning */
.sidebar-rtl {
    order: 1; /* Move after canvas in flex */
    margin-right: 0;
    margin-left: 10px;
}
</style>
