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
    
    // Switch -> Purple
    if (type.includes('switch')) return 'var(--purple-500)';
    
    // Wait -> Gray
    if (type.includes('wait') || type.includes('delay')) return 'var(--gray-500)';
    
    // Sub-rule -> Teal (Blue-Green)
    if (type.includes('sub-rule') || type.includes('nested')) return 'var(--cyan-500)';
    
    // Stop/Cancel/Delete -> Red (Fallback if StopNode not used)
    if (type.includes('stop') || type.includes('cancel')) return 'var(--danger)';

    // Process/Default -> Blue
    return 'var(--blue-500)';
});

const nodeClass = computed(() => {
    const type = (props.data.action_type || '').toLowerCase();
    if (type.includes('switch')) return 'node-switch';
    if (type.includes('wait')) return 'node-wait';
    if (type.includes('sub-rule')) return 'node-sub-rule';
    return 'node-process';
});

</script>

<template>
    <div class="process-node-wrapper" 
         :class="[nodeClass, { 'effectively-disabled': data.is_effectively_disabled, 'selected': selected }]"
         :style="{ '--node-color': nodeColor }">
        
        <Handle type="target" :position="Position.Left" class="handle-target"/>
        
        <!-- Node Toolbar -->
        <div class="node-toolbar" v-if="selected || showConfig">
            <button class="toolbar-btn delete" @click.stop="deleteNode" :title="__('Delete')">
                <i class="fa fa-trash"></i>
            </button>
        </div>

        <div class="node-content">
            <div class="icon-section" v-if="!nodeClass.includes('wait')">
                <div class="icon-wrapper" :style="{ color: nodeColor, backgroundColor: `color-mix(in srgb, ${nodeColor} 10%, white)` }">
                    <i class="fa fa-random" v-if="nodeClass.includes('switch')"></i>
                    <i class="fa fa-layer-group" v-else-if="nodeClass.includes('sub-rule')"></i>
                    <i class="fa fa-robot" v-else-if="data.process_method && data.process_method.includes('AI')"></i>
                    <i class="fa fa-cogs" v-else></i>
                </div>
            </div>
            
            <!-- Special layout for Wait (Circle) -->
            <div class="wait-content" v-if="nodeClass.includes('wait')">
                <div class="concentric-circles">
                    <i class="fa fa-hourglass-half"></i>
                </div>
                <div class="wait-label">{{ data.action_label || label }}</div>
            </div>

            <div class="details-section" v-else>
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
                <pre>{{ data.config || data.method_config || __('Not configured') }}</pre>
            </div>
        </div>

        <Handle type="source" :position="Position.Right" id="default" class="handle-source" :style="{ background: nodeColor }"/>
    </div>
</template>

<style scoped>
.process-node-wrapper {
    background: #fff;
    width: 240px;
    height: 80px;
    color: var(--text-color);
    position: relative;
    display: flex;
    align-items: center;
    padding: 0 16px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-sizing: border-box;
}

/* --- Shapes & Styles (Refined) --- */

/* 1. Process: Modern Card, Blue */
.node-process {
    border-radius: 4px 20px 4px 20px; /* Asymmetric rounding */
    border: 1px solid var(--blue-200);
    border-left: 6px solid var(--blue-500);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

/* 2. Switch: Cut-Corner Card, Purple */
.node-switch {
    width: 220px;
    clip-path: polygon(15px 0%, 100% 0%, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0% 100%, 0% 15px);
    background: white;
    border: none;
    filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
}
.node-switch::before {
    content: '';
    position: absolute;
    inset: 0;
    clip-path: polygon(15px 0%, 100% 0%, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0% 100%, 0% 15px);
    border: 2px solid var(--purple-300);
    background: var(--purple-50);
    z-index: -1;
}

/* 3. Wait: Concentric Circles, Gray */
.node-wait {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    justify-content: center;
    border: 1px solid var(--gray-300);
    background: #fff;
    padding: 0;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}
.wait-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
}
.concentric-circles {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 2px solid var(--gray-200);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    background: var(--gray-50);
}
.concentric-circles::after {
    content: '';
    position: absolute;
    inset: 4px;
    border-radius: 50%;
    border: 1px dashed var(--gray-400);
}
.concentric-circles i { font-size: 18px; color: var(--gray-600); z-index: 1; }
.wait-label { font-size: 10px; font-weight: 800; color: var(--gray-700); text-transform: uppercase; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 4. Sub-rule: Refined Layering, Teal */
.node-sub-rule {
    border-radius: 8px;
    border: 2px solid var(--cyan-400);
    background: white;
    box-shadow: 
        4px -4px 0 -1px white,
        4px -4px 0 1px var(--cyan-200),
        8px -8px 0 -1px white,
        8px -8px 0 1px var(--cyan-100);
}

/* Hover & Selected */
.process-node-wrapper:hover {
    transform: translateY(-4px) scale(1.02);
    filter: drop-shadow(0 12px 20px rgba(0,0,0,0.15));
}
.process-node-wrapper.selected {
    box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.3) !important;
}

/* Internal Styles */
.effectively-disabled { opacity: 0.5; filter: grayscale(100%); }
.node-content { display: flex; align-items: center; width: 100%; }
.icon-wrapper {
    width: 42px; height: 42px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; margin-right: 14px;
}
.details-section { flex: 1; overflow: hidden; }
.node-label { font-weight: 700; font-size: 14px; color: var(--text-color); margin-bottom: 3px; }
.node-subtitle { font-size: 11px; color: var(--text-muted); font-style: italic; }

/* Config Button */
.config-trigger-btn {
    background: var(--bg-light-gray); border: none; color: var(--text-muted);
    border-radius: 50%; width: 26px; height: 26px; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.2s;
}
.config-trigger-btn:hover { background: var(--gray-200); color: var(--text-color); }
.config-trigger-btn.configured { color: var(--node-color); background: color-mix(in srgb, var(--node-color) 15%, white); }

/* Status Badge */
.status-badge {
    position: absolute; bottom: -8px; right: -8px;
    width: 22px; height: 22px; border-radius: 50%;
    background: white; shadow: 0 2px 4px rgba(0,0,0,0.2);
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; border: 2px solid white; z-index: 10;
}
.status-badge.configured { background: var(--node-color); color: white; }
.status-badge.missing { background: var(--orange-400); color: white; }

/* Toolbar */
.node-toolbar {
    position: absolute; top: -40px; right: 0;
    background: var(--gray-900); border-radius: 8px;
    padding: 5px; gap: 5px; display: flex; z-index: 100;
}
.toolbar-btn {
    border: none; background: transparent; padding: 6px;
    border-radius: 6px; cursor: pointer; color: white;
    width: 30px; height: 30px; display: flex; align-items: center; justify-content: center;
}
.toolbar-btn:hover { background: rgba(255,255,255,0.2); }
.toolbar-btn.delete:hover { background: var(--danger); }

/* Handles */
.handle-target { 
    width: 12px !important; height: 12px !important; 
    border: 3px solid white; background: var(--gray-400) !important; 
    left: -6px !important;
}
.handle-source { 
    width: 12px !important; height: 12px !important; 
    border: 3px solid white; right: -6px !important;
}

@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
</style>
