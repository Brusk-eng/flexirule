<script setup>
import { Handle, Position } from '@vue-flow/core'

defineProps(['data', 'label'])
</script>

<template>
  <div class="action-node">
    <Handle type="target" :position="Position.Left" />
    <div class="node-content">
        <span class="icon">⚙️</span>
        <span class="label">{{ label }}</span>
    </div>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<style scoped>
.action-node {
    padding: 10px;
    border-radius: 5px;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    min-width: 150px;
    text-align: center;
}
.node-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}
</style>
