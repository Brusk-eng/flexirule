<script setup>
import { computed, ref } from 'vue';
import { Handle, Position } from '@vue-flow/core';
import { useStore } from '../../store';

const props = defineProps(['data', 'label', 'id']);
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
    <div class="process-node n8n-style" :class="{ 'effectively-disabled': data.is_effectively_disabled }">
        <Handle type="target" :position="Position.Left" class="handle-target"/>
        
        <div class="node-header">
            <div class="icon-wrapper"><i class="fa fa-cogs"></i></div>
            <div class="node-title">
                <div class="node-label">{{ data.action_label || label }}</div>
                <div class="node-subtitle">{{ data.process_method || __('Select Method') }}</div>
            </div>
            <button class="delete-btn" @click.stop="deleteNode">×</button>
        </div>

        <div class="node-body">
            <div class="node-actions">
                <div class="action-item" @click.stop="toggleInputSchema" :title="__('Input Schema')">
                    <i class="fa fa-sign-in"></i>
                    <div v-if="showInputSchema" class="popover-card">
                        <h6>{{ __("Input Schema") }}</h6>
                        <pre>{{ methodSchema?.input_schema || __('No schema') }}</pre>
                    </div>
                </div>
                <div class="action-item" @click.stop="toggleConfig" :title="__('Configuration')">
                    <i class="fa fa-sliders" :class="{ 'active': data.config || data.method_config }"></i>
                     <div v-if="showConfig" class="popover-card">
                        <h6>{{ __("Configuration") }}</h6>
                        <pre>{{ data.config || data.method_config || __('Not configured') }}</pre>
                    </div>
                </div>
                <div class="action-item" @click.stop="toggleOutputSchema" :title="__('Output Schema')">
                    <i class="fa fa-sign-out"></i>
                     <div v-if="showOutputSchema" class="popover-card">
                        <h6>{{ __("Output Schema") }}</h6>
                        <pre>{{ methodSchema?.output_schema || __('No schema') }}</pre>
                    </div>
                </div>
            </div>
        </div>

        <Handle type="source" :position="Position.Right" id="default" class="handle-source"/>
    </div>
</template>

<style scoped>
.n8n-style {
    background: #fff; border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    width: 200px; border: 1px solid var(--border-color);
    transition: all 0.2s ease; overflow: visible;
}
.effectively-disabled { opacity: 0.5; filter: grayscale(100%); pointer-events: none; }
.n8n-style:hover { border-color: var(--primary); }
.node-header {
    display: flex; align-items: center; padding: 10px;
    border-bottom: 1px solid var(--border-color); background: #f8fafc; border-radius: 8px 8px 0 0;
}
.icon-wrapper {
    width: 32px; height: 32px; background: #e0f2fe; color: #0284c7;
    border-radius: 6px; display: flex; align-items: center; justify-content: center; margin-right: 10px;
}
.node-title { flex: 1; overflow: hidden; }
.node-label { font-weight: 600; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.node-subtitle { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.delete-btn {
    opacity: 0; background: none; border: none; color: var(--text-muted);
    font-size: 18px; cursor: pointer; transition: opacity 0.2s; padding: 0 4px;
}
.n8n-style:hover .delete-btn { opacity: 1; }
.node-body { padding: 8px 10px; }
.node-actions { display: flex; justify-content: space-between; }
.action-item { cursor: pointer; color: var(--text-muted); padding: 4px; border-radius: 4px; position: relative; }
.action-item:hover { background: var(--bg-light-gray); color: var(--text-color); }
.action-item i.active { color: var(--primary); }
.popover-card {
    position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%);
    background: white; border: 1px solid var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    padding: 10px; border-radius: 6px; width: 250px; z-index: 100; margin-bottom: 10px; max-height: 300px; overflow-y: auto;
}
.popover-card h6 { margin: 0 0 5px 0; font-weight: 600; border-bottom: 1px solid var(--border-color); padding-bottom: 5px; }
.popover-card pre { margin: 0; font-size: 10px; white-space: pre-wrap; background: #f8f9fa; padding: 5px; border-radius: 4px; }
.handle-target { width: 10px !important; height: 10px !important; border: 2px solid #fff; box-shadow: 0 0 0 1px var(--border-color); background: var(--text-muted) !important; }
.handle-source { width: 10px !important; height: 10px !important; border: 2px solid #fff; box-shadow: 0 0 0 1px var(--border-color); background: var(--primary) !important; }
</style>
