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
    <div class="condition-node" :class="{ 'effectively-disabled': data.is_effectively_disabled }">
        <Handle type="target" :position="Position.Left" class="handle-target" />
        
        <div class="content">
            <div class="icon">◆</div>
            <div class="text">{{ label }}</div>
        </div>
        
        <button class="delete-btn" @click.stop="deleteNode">×</button>
        
        <!-- True handle at 30% from top -->
        <Handle type="source" :position="Position.Right" id="true" class="handle-true" :style="{ top: '30%' }" />
        <span class="handle-label true-label">✓ {{ __("True") }}</span>
        
        <!-- False handle at 70% from top (distinct from True) -->
        <Handle type="source" :position="Position.Right" id="false" class="handle-false" :style="{ top: '70%' }" />
        <span class="handle-label false-label">✗ {{ __("False") }}</span>
    </div>
</template>

<style scoped>
.condition-node {
    padding: 12px 15px; background: white; border: 2px solid var(--warning);
    border-radius: 8px; min-width: 120px; position: relative; box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.effectively-disabled { opacity: 0.5; filter: grayscale(100%); pointer-events: none; }
.content { display: flex; align-items: center; gap: 6px; flex-direction: column; }
.icon { font-size: 16px; color: var(--warning); }
.text { font-size: 12px; font-weight: 500; }
.delete-btn {
    position: absolute; top: -8px; right: -8px; width: 20px; height: 20px; border-radius: 50%;
    background: var(--danger); color: white; border: 2px solid white; cursor: pointer; display: none;
    align-items: center; justify-content: center;
}
.condition-node:hover .delete-btn { display: flex; }
.handle-target { background: var(--gray-500) !important; border: 2px solid white !important; width: 10px !important; height: 10px !important; }
.handle-true { background: var(--success) !important; border: 2px solid white !important; width: 12px !important; height: 12px !important; }
.handle-false { background: var(--danger) !important; border: 2px solid white !important; width: 12px !important; height: 12px !important; }
.handle-label { position: absolute; font-size: 9px; font-weight: 600; color: white; padding: 2px 5px; border-radius: 3px; pointer-events: none; }
.true-label { top: 25%; right: -38px; background: var(--success); }
.false-label { top: 65%; right: -38px; background: var(--danger); }
</style>

