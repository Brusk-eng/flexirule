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
            <div class="icon-wrapper">
                <i class="fa fa-code-fork"></i>
            </div>
            <div class="text">{{ label }}</div>
        </div>
        
        <!-- Output Ports Wrapper -->
        <div class="output-ports">
            <!-- True Output -->
            <div class="port-row true-row">
                <span class="port-label">{{ __("True") }}</span>
                <div class="handle-container true-handle-container">
                    <Handle type="source" :position="Position.Right" id="default" class="handle-out handle-true" />
                    <div class="handle-icon"><i class="fa fa-check"></i></div>
                </div>
            </div>
            
            <!-- False Output -->
            <div class="port-row false-row">
                <span class="port-label">{{ __("False") }}</span>
                <div class="handle-container false-handle-container">
                    <Handle type="source" :position="Position.Right" id="false" class="handle-out handle-false" />
                    <div class="handle-icon"><i class="fa fa-times"></i></div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.condition-node {
    padding: 0; 
    background: white; 
    border: 1px solid var(--border-color);
    border-radius: 8px; 
    width: 160px; 
    min-height: 80px;
    position: relative; 
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: all 0.2s; 
    display: flex; 
    align-items: center;
    border-left: 4px solid var(--warning);
}
.condition-node.selected { 
    border: 2px solid var(--primary); 
    box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2); 
}
.effectively-disabled { opacity: 0.5; filter: grayscale(100%); pointer-events: none; }
.condition-node:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-color: var(--primary); }

.content { 
    display: flex; 
    align-items: center; 
    padding: 12px;
    gap: 10px;
    flex: 1;
}

.icon-wrapper {
    width: 32px; height: 32px;
    background: #fffbeb; color: var(--warning);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
}

.text { 
    font-size: 13px; font-weight: 600; color: var(--text-color);
    line-height: 1.2;
}

.node-toolbar {
    position: absolute; top: -32px; right: 0;
    background: var(--fg-color); border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    display: flex; padding: 4px;
    animation: fadeIn 0.2s;
    z-index: 10;
}
.toolbar-btn {
    border: none; background: transparent; padding: 6px;
    border-radius: 4px; cursor: pointer; color: var(--text-color); font-size: 12px;
}
.toolbar-btn:hover { background: var(--bg-light-gray); }
.toolbar-btn.delete:hover { background: var(--danger-light); color: var(--danger); }

/* Ports */
.output-ports {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    padding: 10px 0;
    position: absolute;
    right: 0;
    top: 0;
    height: 100%;
}

.port-row {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    margin-right: -14px; /* Push handle out */
    height: 30px;
}

.port-label { 
    font-size: 10px; font-weight: 700; user-select: none;
    margin-right: 20px; text-transform: uppercase;
}
.true-row .port-label { color: var(--success); }
.false-row .port-label { color: var(--danger); }

.handle-container {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    display: flex; align-items: center; justify-content: center;
    position: relative; /* Anchor for absolute handle */
    transition: all 0.2s;
    z-index: 5;
}

.handle-container:hover { transform: scale(1.1); }

.true-handle-container { border: 2px solid var(--success); color: var(--success); }
.false-handle-container { border: 2px solid var(--danger); color: var(--danger); }

.handle-icon { font-size: 12px; font-weight: bold; pointer-events: none; }

.handle-target { 
    background: var(--text-muted) !important; border: 2px solid white !important; 
    width: 10px !important; height: 10px !important; left: -5px !important; 
    border-radius: 50%;
}

/* 
   Invisible Vue Flow Handle.
   Must cover the entire container to catch clicks/drags.
   Using specific Vue Flow classes if needed, but the custom class should work if ID matches.
*/
.handle-out { 
    opacity: 0; 
    width: 100% !important; 
    height: 100% !important; 
    left: 0 !important; 
    top: 0 !important;
    position: absolute !important;
    border-radius: 50%;
    cursor: crosshair;
    z-index: 10;
    transform: none !important; /* Prevent Vue Flow from centering it relative to node */
}

@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
</style>

