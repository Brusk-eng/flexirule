<script setup>
import { computed, ref, inject } from 'vue';
import { Handle, Position } from '@vue-flow/core';
import { useStore } from '../../store';

const props = defineProps(['data', 'label', 'id', 'selected']);
const store = useStore();

const showInputSchema = ref(false);
const showConfig = ref(false);
const showOutputSchema = ref(false);

const methodSchema = computed(() => store.get_process_method_schema(props.data.process_method));

function deleteNode() {
    frappe.confirm(__('Delete this node?'), () => store.delete_node(props.id));
}
function toggleInputSchema() { showInputSchema.value = !showInputSchema.value; }
function toggleConfig() { showConfig.value = !showConfig.value; }
function toggleOutputSchema() { showOutputSchema.value = !showOutputSchema.value; }
</script>

<template>
    <div class="process-node n8n-style" :class="{ 'effectively-disabled': data.is_effectively_disabled, 'selected': selected }">
        <Handle type="target" :position="Position.Left" class="handle-target"/>
        
        <!-- Node Toolbar (Simulated) -->
        <div class="node-toolbar" v-if="selected || showConfig || showInputSchema || showOutputSchema">
            <button class="toolbar-btn delete" @click.stop="deleteNode" :title="__('Delete')">
                <i class="fa fa-trash"></i>
            </button>
            <button class="toolbar-btn" @click.stop="toggleConfig" :title="__('Configuration')" :class="{ 'active': showConfig }">
                <i class="fa fa-sliders"></i>
            </button>
        </div>

        <div class="node-header">
            <div class="icon-wrapper"><i class="fa fa-cogs"></i></div>
            <div class="node-title">
                <div class="node-label">{{ data.action_label || label }}</div>
                <div class="node-subtitle">{{ data.process_method || __('Select Method') }}</div>
            </div>
        </div>

        <div class="node-body">
            <!-- Indicators -->
             <div class="node-indicators">
                <span v-if="data.config" class="indicator configured" :title="__('Configured')">●</span>
                <span v-else class="indicator missing" :title="__('Missing Config')">●</span>
             </div>
             
             <!-- Popovers -->
             <div v-if="showConfig" class="popover-card config-popover">
                <h6>{{ __("Configuration") }} <button class="close-popover" @click.stop="showConfig=false">×</button></h6>
                <pre>{{ data.config || data.method_config || __('Not configured') }}</pre>
            </div>
        </div>

        <Handle type="source" :position="Position.Right" id="default" class="handle-source"/>
    </div>
</template>

<style scoped>
.n8n-style {
    background: #fff; border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    width: 220px; border: 1px solid var(--border-color);
    transition: all 0.2s ease; overflow: visible; position: relative;
    border-left: 4px solid var(--primary);
}
.n8n-style.selected { ring: 2px solid var(--primary); border-color: var(--primary); }
.effectively-disabled { opacity: 0.5; filter: grayscale(100%); pointer-events: none; }
.n8n-style:hover { border-color: var(--primary); transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }

.node-toolbar {
    position: absolute; top: -35px; right: 0;
    background: var(--fg-color); border-radius: 4px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    display: flex; padding: 2px; gap: 2px;
    animation: fadeIn 0.2s;
}
.toolbar-btn {
    border: none; background: transparent; padding: 4px 8px;
    border-radius: 3px; cursor: pointer; color: var(--text-color);
    font-size: 12px;
}
.toolbar-btn:hover { background: var(--bg-light-gray); }
.toolbar-btn.delete:hover { background: var(--danger); color: white; }
.toolbar-btn.active { background: var(--primary); color: white; }

.node-header {
    display: flex; align-items: center; padding: 12px;
    border-bottom: 1px solid var(--border-color); background: #f8fafc; border-radius: 0 4px 0 0;
}
.icon-wrapper {
    width: 32px; height: 32px; background: #e0f2fe; color: #0284c7;
    border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-right: 12px;
}
.node-title { flex: 1; overflow: hidden; }
.node-label { font-weight: 600; font-size: 13px; color: var(--text-color); margin-bottom: 2px; }
.node-subtitle { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.node-body { padding: 0; position: relative; }
.node-indicators { padding: 4px 10px; display: flex; justify-content: flex-end; }
.indicator { font-size: 10px; margin-left: 4px; }
.indicator.configured { color: var(--success); }
.indicator.missing { color: var(--orange); }

.popover-card {
    position: absolute; top: 100%; left: 0; right: 0;
    background: white; border: 1px solid var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    padding: 10px; border-radius: 6px; z-index: 100; margin-top: 5px; max-height: 200px; overflow-y: auto;
}
.popover-card h6 { margin: 0 0 5px 0; font-weight: 600; font-size: 11px; display: flex; justify-content: space-between; }
.close-popover { border: none; background: none; cursor: pointer; font-weight: bold; }
.popover-card pre { margin: 0; font-size: 10px; white-space: pre-wrap; background: #f8f9fa; padding: 5px; border-radius: 4px; }

.handle-target { width: 12px !important; height: 12px !important; border: 2px solid #fff; background: var(--text-muted) !important; left: -6px !important; }
.handle-source { width: 12px !important; height: 12px !important; border: 2px solid #fff; background: var(--primary) !important; right: -6px !important; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
</style>
