<script setup>
import { ref, computed } from 'vue';
import { Handle, Position } from '@vue-flow/core';
import { useStore } from '../../store';

const props = defineProps(['data', 'label', 'id', 'selected']);
const store = useStore();

const showConfig = ref(false);

const nodeColor = computed(() => {
  const type = (props.data.action_type || '').toLowerCase();
  if (type.includes('switch')) return 'var(--purple-500)';
  if (type.includes('wait') || type.includes('delay')) return 'var(--gray-500)';
  if (type.includes('sub-rule') || type.includes('nested')) return 'var(--cyan-500)';
  if (type.includes('stop') || type.includes('cancel')) return 'var(--danger)';
  return '#a3d8f4'; // Light blue for process nodes
});

const nodeClass = computed(() => {
  const type = (props.data.action_type || '').toLowerCase();
  if (type.includes('switch')) return 'node-switch';
  if (type.includes('wait')) return 'node-wait';
  if (type.includes('sub-rule')) return 'node-sub-rule';
  return 'node-process';
});

function deleteNode() {
  frappe.confirm(__('Delete this node?'), () => store.delete_node(props.id));
}

function toggleConfig() {
  showConfig.value = !showConfig.value;
}
</script>

<template>
<div class="process-node-wrapper" :class="[nodeClass, { 'selected': selected }]" 
     :style="{ '--node-color': nodeColor }">

  <Handle type="target" :position="Position.Left" class="handle-target"/>
  
  <!-- Toolbar -->
  <div class="node-toolbar" v-if="selected || showConfig">
    <button class="toolbar-btn delete" @click.stop="deleteNode" :title="__('Delete')">
      <i class="fa fa-trash"></i>
    </button>
  </div>

  <!-- Content -->
  <div class="node-content">
    <div class="icon-wrapper">
      <i class="fa fa-cogs"></i>
    </div>
    <div class="details-section">
      <div class="node-label">{{ data.action_label || label }}</div>
      <div class="node-subtitle">{{ data.process_method || __('Select Method') }}</div>
    </div>
    <button class="config-trigger-btn" @click.stop="toggleConfig" :class="{ 'configured': data.config }">
      <i class="fa fa-cog"></i>
    </button>
  </div>

  <!-- Status Badge -->
  <div class="status-badge" :class="{ 'configured': data.config, 'missing': !data.config }">
    <i class="fa fa-check" v-if="data.config"></i>
    <i class="fa fa-exclamation" v-else></i>
  </div>

  <!-- Config Popover -->
  <div v-if="showConfig" class="popover-card config-popover">
    <h6>{{ __("Configuration") }} 
      <button class="close-popover" @click.stop="showConfig=false">×</button>
    </h6>
    <div class="config-content">
      <pre>{{ data.config || data.method_config || __('Not configured') }}</pre>
    </div>
  </div>

  <Handle type="source" :position="Position.Right" id="default" class="handle-source"/>
</div>
</template>

<style scoped>
.process-node-wrapper {
  width: 240px;
  min-height: 80px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  position: relative;
  border-radius: 12px;
  background-color: var(--node-color);
  box-shadow: 0 6px 12px rgba(0,0,0,0.08);
  transition: transform 0.2s, box-shadow 0.2s;
  color: #fff;
}
.process-node-wrapper:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 24px rgba(0,0,0,0.15);
}

/* Node Types */
.node-process {}
.node-switch { background-color: var(--purple-500); }
.node-wait { background-color: var(--gray-500); border-radius: 50%; }
.node-sub-rule { background-color: var(--cyan-500); }

/* Content */
.node-content {
  display: flex;
  align-items: center;
  width: 100%;
}
.icon-wrapper {
  width: 44px; height: 44px;
  border-radius: 50%;
  background: white;
  color: var(--node-color);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  margin-right: 12px;
}
.details-section { flex: 1; overflow: hidden; }
.node-label { font-weight: 700; font-size: 14px; }
.node-subtitle { font-size: 11px; font-style: italic; opacity: 0.85; }

/* Config Button */
.config-trigger-btn {
  background: rgba(255,255,255,0.2);
  border: none;
  border-radius: 50%;
  width: 28px; height: 28px;
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.config-trigger-btn:hover { background: rgba(255,255,255,0.3); }
.config-trigger-btn.configured { background: rgba(255,255,255,0.4); color: #000; }

/* Status Badge */
.status-badge {
  position: absolute;
  bottom: -8px; right: -8px;
  width: 22px; height: 22px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px;
  background: #fff;
  color: var(--node-color);
  border: 2px solid #fff;
}
.status-badge.configured { background: #fff; color: var(--node-color); }

/* Toolbar */
.node-toolbar {
  position: absolute;
  top: -36px; right: 0;
  display: flex; gap: 6px;
}
.toolbar-btn {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  border: none;
  background: rgba(0,0,0,0.25);
  color: #fff;
  cursor: pointer;
}
.toolbar-btn.delete:hover { background: var(--danger); }

/* Handles */
.handle-target, .handle-source {
  width: 12px !important; height: 12px !important;
  border: 3px solid #fff;
}
</style>
