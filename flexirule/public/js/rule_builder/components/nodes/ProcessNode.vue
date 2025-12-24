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
function toggleConfig() { showConfig.value = !showConfig.value; }

// Color Helper
const nodeColor = computed(() => {
    const type = (props.data.action_type || '').toLowerCase();
    // Stop/Cancel/Delete -> Red
    if (type.includes('stop') || type.includes('cancel') || type.includes('delete')) return 'var(--danger)';
    // Create/Insert -> Green
    if (type.includes('create') || type.includes('insert')) return 'var(--success)';
    // Update/Save -> Blue
    if (type.includes('update') || type.includes('save') || type.includes('process')) return 'var(--blue-500)'; // Default Process
    // Email/Notify -> Orange
    if (type.includes('email') || type.includes('notify') || type.includes('switch')) return 'var(--orange-500)';
    // App/Script/Loop -> Purple
    if (type.includes('script') || type.includes('code') || type.includes('loop')) return 'var(--purple-500)';
    // Wait -> Yellow
    if (type.includes('wait') || type.includes('delay')) return 'var(--yellow-500)';
    
    return 'var(--primary)';
});

const nodeBgColor = computed(() => {
     // Light variant for icon background
     return nodeColor.value.replace(')', '-rgb), 0.1)'); // Rough simulation if vars allow, else fallback
});

</script>

<template>
    <div class="process-node ai-agent-style" 
         :class="{ 'effectively-disabled': data.is_effectively_disabled, 'selected': selected }"
         :style="{ '--node-color': nodeColor }">
        <Handle type="target" :position="Position.Left" class="handle-target"/>
        
        <!-- Node Toolbar -->
        <div class="node-toolbar" v-if="selected || showConfig">
            <button class="toolbar-btn delete" @click.stop="deleteNode" :title="__('Delete')">
                <i class="fa fa-trash"></i>
            </button>
        </div>

        <div class="node-content">
            <div class="icon-section">
                <div class="icon-wrapper" :style="{ color: nodeColor, backgroundColor: `color-mix(in srgb, ${nodeColor} 10%, white)` }">
                    <i class="fa fa-robot" v-if="data.process_method && data.process_method.includes('AI')"></i>
                    <i class="fa fa-envelope" v-else-if="data.action_type && data.action_type.includes('Notify')"></i>
                    <i class="fa fa-trash" v-else-if="data.action_type && data.action_type.includes('Delete')"></i>
                    <i class="fa fa-plus" v-else-if="data.action_type && data.action_type.includes('Create')"></i>
                    <i class="fa fa-edit" v-else-if="data.action_type && data.action_type.includes('Update')"></i>
                    <i class="fa fa-cogs" v-else></i>
                </div>
            </div>
            <div class="details-section">
                <div class="node-label">{{ data.action_label || label }}</div>
                <div class="node-subtitle">{{ data.process_method || __('Select Method') }}</div>
            </div>
             <!-- Config Button (Visible) -->
             <button class="config-trigger-btn" @click.stop="toggleConfig" :title="__('Unconfigured')" :class="{ 'configured': data.config }">
                <i class="fa fa-cog"></i>
            </button>
        </div>

        <!-- Status Indicator (Checkmark) -->
        <div class="status-badge" :class="{ 'configured': data.config, 'missing': !data.config }" :style="{ borderColor: nodeColor }">
            <i class="fa fa-check" v-if="data.config"></i>
            <i class="fa fa-exclamation" v-else></i>
        </div>

        <!-- Popovers -->
        <div v-if="showConfig" class="popover-card config-popover">
            <h6>{{ __("Configuration") }} <button class="close-popover" @click.stop="showConfig=false">×</button></h6>
            <div class="config-content">
                 <!-- Placeholder for actual form, showing JSON for now -->
                <pre>{{ data.config || data.method_config || __('Not configured') }}</pre>
            </div>
        </div>

        <Handle type="source" :position="Position.Right" id="default" class="handle-source" :style="{ background: nodeColor }"/>
    </div>
</template>

<style scoped>
.ai-agent-style {
    background: #fff;
    border-radius: 12px;
    width: 240px;
    height: 80px;
    border: 1px solid var(--border-color);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    transition: all 0.2s ease;
    position: relative;
    display: flex;
    align-items: center;
    padding: 0 16px;
    border-left: 4px solid var(--node-color);
}

.ai-agent-style:hover {
    border-color: var(--node-color);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
}

.ai-agent-style.selected {
    border: 2px solid var(--node-color);
    box-shadow: 0 0 0 2px rgba(0,0,0, 0.1);
}

.effectively-disabled {
    opacity: 0.6;
    filter: grayscale(100%);
}

.node-content {
    display: flex;
    align-items: center;
    width: 100%;
}

.icon-wrapper {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    margin-right: 12px;
}

.details-section {
    flex: 1;
    overflow: hidden;
}

.node-label {
    font-weight: 600;
    font-size: 14px;
    color: var(--text-color);
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.node-subtitle {
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.config-trigger-btn {
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-muted);
    border-radius: 4px;
    padding: 4px;
    cursor: pointer;
    transition: all 0.2s;
}
.config-trigger-btn:hover {
    background: var(--bg-light-gray);
    color: var(--text-color);
}
.config-trigger-btn.configured {
    color: var(--node-color);
}

.status-badge {
    position: absolute;
    bottom: -6px;
    right: -6px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    border: 2px solid white;
}

.status-badge.configured {
    background: var(--node-color);
    color: white;
}

.status-badge.missing {
    background: var(--orange);
    color: white;
}

.node-toolbar {
    position: absolute;
    top: -32px;
    right: 0;
    background: var(--fg-color);
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    display: flex;
    padding: 4px;
    gap: 4px;
    z-index: 10;
    animation: fadeIn 0.2s;
}

.toolbar-btn {
    border: none;
    background: transparent;
    padding: 6px;
    border-radius: 4px;
    cursor: pointer;
    color: var(--text-color);
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    transition: all 0.1s;
}

.toolbar-btn:hover {
    background: var(--bg-light-gray);
}
.toolbar-btn.delete:hover {
    background: var(--danger-light);
    color: var(--danger);
}

.popover-card {
    position: absolute; top: calc(100% + 10px); left: 0; right: 0;
    background: white; border: 1px solid var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    padding: 12px; border-radius: 8px; z-index: 100; max-height: 200px; overflow-y: auto;
}
.popover-card h6 { margin: 0 0 8px 0; font-weight: 600; font-size: 12px; display: flex; justify-content: space-between; }
.close-popover { border: none; background: none; cursor: pointer; font-weight: bold; padding: 0 4px; }
.popover-card pre { margin: 0; font-size: 11px; white-space: pre-wrap; background: #f8f9fa; padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); }

.handle-target { 
    width: 10px !important; 
    height: 10px !important; 
    border: 2px solid white; 
    background: var(--text-muted) !important; 
    left: -5px !important; 
    border-radius: 50%;
}
.handle-source { 
    width: 10px !important; 
    height: 10px !important; 
    border: 2px solid white; 
    right: -5px !important; 
    border-radius: 50%;
}

@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
</style>
