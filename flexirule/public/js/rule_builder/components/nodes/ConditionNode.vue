<script setup>
import { Handle, Position } from '@vue-flow/core';
import { useStore } from '../../store';

const props = defineProps(['data', 'label', 'id', 'selected']);
const store = useStore();

function deleteNode() {
    frappe.confirm(__('Delete this node?'), () => store.delete_node(props.id));
}
</script>

<template>
    <div class="condition-node-wrapper">
        <div class="rhombus-shape" :class="{ 'selected': selected, 'effectively-disabled': data.is_effectively_disabled }">
            <div class="inner-rhombus">
                <i class="fa fa-code-fork"></i>
            </div>
        </div>

        <!-- Handles -->
        <Handle type="target" :position="Position.Left" class="handle-input" />
        
        <div class="handle-container handle-true-pos">
            <span class="port-label true-label">{{ __("YES") }}</span>
            <Handle type="source" :position="Position.Top" id="true" class="handle-out handle-true" />
        </div>

        <div class="handle-container handle-false-pos">
            <span class="port-label false-label">{{ __("NO") }}</span>
            <Handle type="source" :position="Position.Bottom" id="false" class="handle-out handle-false" />
        </div>

        <!-- Label below -->
        <div class="condition-label">{{ label }}</div>

        <!-- Toolbar -->
         <div class="node-toolbar" v-if="selected">
            <button class="toolbar-btn delete" @click.stop="deleteNode">
                <i class="fa fa-trash"></i>
            </button>
        </div>
    </div>
</template>

<style scoped>
.condition-node-wrapper {
    position: relative;
    width: 140px;
    height: 100px;
    display: flex;
    justify-content: center;
    align-items: center;
}

.rhombus-shape {
    width: 100px;
    height: 60px;
    background: var(--orange-500);
    transform: skewX(-20deg); /* Slanted Rect / Rhombus */
    border-radius: 4px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    border: 2px solid white;
}

.rhombus-shape.selected {
    box-shadow: 0 0 0 4px rgba(var(--orange-rgb), 0.4);
    transform: skewX(-20deg) scale(1.05);
}

.inner-rhombus {
    transform: skewX(20deg); /* Counter-skew content */
    color: white;
    font-size: 24px;
}

.condition-label {
    position: absolute;
    bottom: -15px;
    font-size: 11px;
    font-weight: 800;
    color: var(--orange-700);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Handles */
.handle-input {
    background: var(--gray-400) !important;
    border: 2px solid white !important;
    width: 12px !important; height: 12px !important;
    left: 5px !important;
}

.handle-container {
    position: absolute;
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 10;
}

.handle-true-pos { top: -10px; left: 50%; transform: translateX(-50%); }
.handle-false-pos { bottom: -10px; left: 50%; transform: translateX(-50%); }

.handle-out {
    position: relative !important;
    transform: none !important;
    top: auto !important;
    width: 12px !important; height: 12px !important;
    border: 2px solid white !important;
}

.handle-true { background: var(--success) !important; }
.handle-false { background: var(--danger) !important; }

.port-label { font-size: 9px; font-weight: 900; }
.true-label { color: var(--success); margin-bottom: 2px; }
.false-label { color: var(--danger); margin-top: 2px; }

/* Toolbar */
.node-toolbar {
    position: absolute; top: -30px; right: 0;
    background: var(--gray-900); border-radius: 50%; padding: 4px;
}
.toolbar-btn {
    width: 24px; height: 24px; border: none; background: transparent; 
    color: white; cursor: pointer;
}
.toolbar-btn:hover { color: var(--danger); }

</style>
