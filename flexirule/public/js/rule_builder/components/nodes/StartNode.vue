<script setup>
import { Handle, Position } from '@vue-flow/core';
import { computed } from 'vue';

const props = defineProps(['data', 'label']);

const displayLabel = computed(() => {
    if (props.data?.document_type && props.data?.trigger_event) {
        return `${props.data.document_type}\n${props.data.trigger_event}`;
    }
    return props.label || 'Start';
});
</script>

<template>
    <div class="start-node">
        <div class="content">
            <div class="icon">▶</div>
            <div class="text">{{ displayLabel }}</div>
        </div>
        <!-- Source handle (right side) - MUST be visible for connections -->
        <Handle 
            type="source" 
            :position="Position.Right" 
            id="default"
            class="handle-source"
        />
    </div>
</template>

<style scoped>
.start-node {
    padding: 12px 18px;
    background: linear-gradient(135deg, var(--success) 0%, #28a745 100%);
    color: white;
    border-radius: 8px;
    min-width: 130px;
    box-shadow: 0 2px 8px rgba(0,128,0,0.3);
    position: relative;
}

.content {
    display: flex;
    align-items: center;
    gap: 8px;
}

.icon {
    font-size: 18px;
}

.text {
    font-size: 12px;
    font-weight: 600;
    white-space: pre-line;
    line-height: 1.3;
}

/* Make handles visible */
.handle-source {
    background: white !important;
    border: 2px solid var(--success) !important;
    width: 12px !important;
    height: 12px !important;
}

.handle-source:hover {
    background: var(--success) !important;
    transform: scale(1.3);
}
</style>
