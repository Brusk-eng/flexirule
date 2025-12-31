<script setup>
import { Handle, Position } from '@vue-flow/core'

defineProps(['data', 'label'])
</script>

<template>
  <div class="action-node-refined">
    <Handle type="target" :position="Position.Left" class="handle-target"/>
    <div class="node-content">
        <div class="icon-box">
            <span class="icon">⚙️</span>
        </div>
        <div class="text-group">
            <span class="label">{{ label }}</span>
            <span class="subtext">PROCESS</span>
        </div>
    </div>
    <Handle type="source" :position="Position.Right" class="handle-source"/>
  </div>
</template>

<style scoped>
.action-node-refined {
    background: #fff;
    width: 200px;
    height: 70px;
    position: relative;
    display: flex;
    align-items: center;
    padding: 0 16px;
    border-radius: 4px 16px 4px 16px;
    border: 1px solid var(--blue-200);
    border-left: 5px solid var(--blue-500);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    transition: all 0.3s ease;
}

.action-node-refined:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.node-content {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
}

.icon-box {
    width: 34px;
    height: 34px;
    background: var(--blue-50);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
}

.text-group {
    display: flex;
    flex-direction: column;
}

.label { font-size: 13px; font-weight: 700; color: var(--text-color); }
.subtext { font-size: 8px; font-weight: 800; color: var(--blue-600); opacity: 0.6; }

/* Handles */
.handle-target {
    background: var(--gray-400) !important;
    border: 2px solid white !important;
    width: 10px !important; height: 10px !important;
    left: -5px !important;
}
.handle-source {
    background: var(--blue-500) !important;
    border: 2px solid white !important;
    width: 10px !important; height: 10px !important;
    right: -5px !important;
}
</style>
