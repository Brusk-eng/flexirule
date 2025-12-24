<script setup>
import { Handle, Position } from '@vue-flow/core';
import { useStore } from '../../store';

const props = defineProps(['data', 'label', 'id']);
const store = useStore();

function deleteNode() {
    frappe.confirm(
        __('Delete this node?'),
        () => {
            store.delete_node(props.id);
        }
    );
}
</script>

<template>
    <div class="stop-node ai-agent-style">
        <Handle type="target" :position="Position.Left" class="handle-target"/>
        
        <div class="node-content">
            <div class="icon-wrapper">
                <i class="fa fa-stop"></i>
            </div>
            <div class="details-section">
                <div class="node-label">{{ label }}</div>
                <div class="node-subtitle">{{ __("End") }}</div>
            </div>
        </div>

        <button class="delete-btn" @click.stop="deleteNode" :title="__('Delete Node')">
            <i class="fa fa-trash"></i>
        </button>
    </div>
</template>

<style scoped>
.ai-agent-style {
    background: #fff;
    border-radius: 12px;
    width: 160px;
    height: 60px;
    border: 1px solid var(--border-color);
    border-left: 4px solid var(--danger);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: all 0.2s ease;
    position: relative;
    display: flex;
    align-items: center;
    padding: 0 12px;
}

.ai-agent-style:hover {
    border-color: var(--danger);
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.node-content { display: flex; align-items: center; width: 100%; }

.icon-wrapper {
    width: 32px; height: 32px;
    border-radius: 8px;
    background: #fee2e2;
    color: var(--danger);
    display: flex; align-items: center; justify-content: center;
    margin-right: 12px;
    font-size: 14px;
}

.details-section { flex: 1; }
.node-label { font-weight: 600; font-size: 13px; color: var(--text-color); }
.node-subtitle { font-size: 10px; color: var(--text-muted); }

.delete-btn {
    border: none; background: transparent; color: var(--text-gray);
    cursor: pointer; padding: 4px; display: none;
    position: absolute; top: -10px; right: -10px;
    background: white; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.ai-agent-style:hover .delete-btn { display: flex; }
.delete-btn:hover { color: var(--danger); }

.handle-target {
    background: var(--text-muted) !important;
    border: 2px solid white !important;
    width: 10px !important; height: 10px !important;
    left: -5px !important; border-radius: 50%;
}
</style>
