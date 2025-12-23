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
    <div class="condition-node" :class="{ 'effectively-disabled': data.is_effectively_disabled, 'selected': selected }">
        <Handle type="target" :position="Position.Left" class="handle-target" />
        
        <!-- Toolbar -->
        <div class="node-toolbar" v-if="selected">
            <button class="toolbar-btn delete" @click.stop="deleteNode" :title="__('Delete')">
                <i class="fa fa-trash"></i>
            </button>
        </div>
        
        <div class="content">
            <div class="icon">◆</div>
            <div class="text">{{ label }}</div>
        </div>
        
        <!-- True Output -->
        <div class="output-port true-port" :style="{ top: '25%' }">
             <span class="port-label">{{ __("True") }}</span>
             <Handle type="source" :position="Position.Right" id="default" class="handle-out handle-true" />
        </div>
        
        <!-- False Output -->
        <div class="output-port false-port" :style="{ top: '75%' }">
            <span class="port-label">{{ __("False") }}</span>
            <Handle type="source" :position="Position.Right" id="false" class="handle-out handle-false" />
        </div>
    </div>
</template>

<style scoped>
.condition-node {
    padding: 10px 15px; background: white; border: 2px solid var(--warning);
    border-radius: 8px; min-width: 140px; position: relative; box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    transition: all 0.2s; min-height: 70px; display: flex; align-items: center; justify-content: center;
}
.condition-node.selected { box-shadow: 0 0 0 2px var(--primary); }
.effectively-disabled { opacity: 0.5; filter: grayscale(100%); pointer-events: none; }
.condition-node:hover { transform: translateY(-2px); box-shadow: 0 5px 10px rgba(0,0,0,0.15); }

.content { display: flex; align-items: center; gap: 8px; text-align: center; }
.icon { font-size: 18px; color: var(--warning); transform: rotate(45deg); display: inline-block; width: 18px; height: 18px; background: var(--warning); border-radius: 2px; }
.content .icon { transform: rotate(45deg); background: transparent; width: auto; height: auto; } /* Reset */
.text { font-size: 12px; font-weight: 600; color: var(--text-color); }

.node-toolbar {
    position: absolute; top: -30px; right: 0;
    background: var(--fg-color); border-radius: 4px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    display: flex; padding: 2px;
    animation: fadeIn 0.2s;
}
.toolbar-btn {
    border: none; background: transparent; padding: 4px 8px;
    border-radius: 3px; cursor: pointer; color: var(--text-color); font-size: 12px;
}
.toolbar-btn:hover { background: var(--bg-light-gray); }
.toolbar-btn.delete:hover { background: var(--danger); color: white; }

/* Ports */
.output-port { position: absolute; right: 0; display: flex; align-items: center; transform: translateX(50%); }
.port-label { 
    position: absolute; right: 12px; font-size: 9px; font-weight: 700; 
    text-transform: uppercase; pointer-events: none;
    background: rgba(255,255,255,0.9); padding: 0 2px; border-radius: 2px;
}
.true-port .port-label { color: var(--success); }
.false-port .port-label { color: var(--danger); }

.handle-target { 
    background: var(--text-muted) !important; border: 2px solid white !important; 
    width: 12px !important; height: 12px !important; left: -6px !important; 
}
.handle-out { border: 2px solid white !important; width: 12px !important; height: 12px !important; right: 0 !important; }
.handle-true { background: var(--success) !important; }
.handle-false { background: var(--danger) !important; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
</style>

