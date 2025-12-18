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
    <div class="stop-node">
        <Handle 
            type="target" 
            :position="Position.Left" 
            class="handle-target"
        />
        
        <div class="content">
            <span class="icon">■</span>
            <span class="text">{{ label }}</span>
        </div>
        
        <button class="delete-btn" @click.stop="deleteNode" :title="__('Delete Node')">×</button>
    </div>
</template>

<style scoped>
.stop-node {
    padding: 12px 16px;
    background: linear-gradient(135deg, var(--danger) 0%, #dc3545 100%);
    color: white;
    border-radius: 8px;
    min-width: 100px;
    box-shadow: 0 2px 8px rgba(220,53,69,0.3);
    position: relative;
}

.content {
    display: flex;
    align-items: center;
    gap: 8px;
}

.icon {
    font-size: 16px;
}

.text {
    font-size: 12px;
    font-weight: 600;
}

.delete-btn {
    position: absolute;
    top: -8px;
    right: -8px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: white;
    color: var(--danger);
    border: 2px solid var(--danger);
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.stop-node:hover .delete-btn {
    display: flex;
}

.delete-btn:hover {
    background: var(--danger);
    color: white;
    transform: scale(1.1);
}

.handle-target {
    background: white !important;
    border: 2px solid var(--danger) !important;
    width: 10px !important;
    height: 10px !important;
}

.handle-target:hover {
    transform: scale(1.4);
}
</style>
