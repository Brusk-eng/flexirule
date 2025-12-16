<script setup>
import { Handle, Position } from '@vue-flow/core';
import { useStore } from '../../store';

const props = defineProps(['data', 'label', 'id']);
const store = useStore();

function deleteNode() {
    frappe.confirm(__('Delete this node?'), () => store.delete_node(props.id));
}
</script>

<template>
    <div class="loop-node" :class="{ 'effectively-disabled': data.is_effectively_disabled }">
        <Handle type="target" :position="Position.Left" class="handle-target" />
        
        <div class="content">
            <div class="icon">↻</div>
            <div class="text">{{ data.action_label || label }}</div>
            <div class="subtext">Loop</div>
        </div>
        
        <button class="delete-btn" @click.stop="deleteNode">×</button>
        
        <!-- Iterate / Body Path -->
        <Handle type="source" :position="Position.Right" id="default" class="handle-do" />
        <span class="handle-label label-do">Do</span>
        
        <!-- Exit / Done Path -->
        <Handle type="source" :position="Position.Bottom" id="false" class="handle-done" />
        <span class="handle-label label-done">Done</span>
    </div>
</template>

<style scoped>
.loop-node {
    padding: 10px 15px;
    background: white;
    border: 2px solid var(--orange-500);
    border-radius: 50px; /* Pill shape */
    min-width: 120px;
    position: relative;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.effectively-disabled {
    opacity: 0.5;
    filter: grayscale(100%);
    pointer-events: none;
}

.content {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 2px;
}

.icon { font-size: 18px; color: var(--orange-500); line-height: 1; }
.text { font-size: 12px; font-weight: 600; }
.subtext { font-size: 10px; color: var(--text-muted); }

.delete-btn {
    position: absolute; top: 0; right: 0;
    width: 20px; height: 20px; border-radius: 50%;
    background: var(--danger); color: white; border: 2px solid white;
    cursor: pointer; display: none; align-items: center; justify-content: center;
}
.loop-node:hover .delete-btn { display: flex; }

.handle-target { background: var(--gray-500) !important; width: 10px !important; height: 10px !important; }
.handle-do { background: var(--orange-500) !important; top: 50% !important; }
.handle-done { background: var(--gray-500) !important; }

.handle-label {
    position: absolute; font-size: 9px; font-weight: bold; color: var(--text-muted);
    pointer-events: none;
}
.label-do { right: -25px; top: 35%; color: var(--orange-500); }
.label-done { bottom: -18px; left: 50%; transform: translateX(-50%); }
</style>
