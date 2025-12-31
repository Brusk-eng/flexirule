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
    <div class="process-node">
        <Handle 
            type="target" 
            :position="Position.Left" 
            class="handle-target"
        />
        
        <div class="content">
            <div class="header">
                <span class="icon">⚙️</span>
                <span class="label">{{ label }}</span>
            </div>
            <div v-if="data.process_method" class="method">{{ data.process_method }}</div>
            <div v-if="data.configuration" class="config-indicator">⚡ Configured</div>
        </div>
        
        <button class="delete-btn" @click.stop="deleteNode" title="Delete Node">×</button>
        
        <Handle 
            type="source" 
            :position="Position.Right" 
            id="default"
            class="handle-source"
        />
    </div>
</template>

<style scoped>
.process-node {
    padding: 12px;
    background: white;
    border: 2px solid var(--primary);
    border-radius: 6px;
    min-width: 150px;
    position: relative;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.content {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 500;
}

.icon {
    font-size: 16px;
}

.label {
    font-size: 13px;
}

.method {
    font-size: 10px;
    color: var(--text-muted);
}

.config-indicator {
    font-size: 9px;
    color: var(--primary);
    font-weight: 600;
}

/* Delete button */
.delete-btn {
    position: absolute;
    top: -8px;
    right: -8px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--danger);
    color: white;
    border: 2px solid white;
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.process-node:hover .delete-btn {
    display: flex;
}

.delete-btn:hover {
    background: darkred;
    transform: scale(1.1);
}

.handle-target {
    background: var(--gray-500) !important;
    border: 2px solid white !important;
    width: 10px !important;
    height: 10px !important;
}

.handle-source {
    background: var(--primary) !important;
    border: 2px solid white !important;
    width: 12px !important;
    height: 12px !important;
}

.handle-target:hover,
.handle-source:hover {
    transform: scale(1.4);
}
</style>
