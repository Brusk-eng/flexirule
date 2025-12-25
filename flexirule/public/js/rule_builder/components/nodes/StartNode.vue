<script setup>
import { Handle, Position } from '@vue-flow/core';
import { computed } from 'vue';

const props = defineProps(['data', 'label']);

const displayLabel = computed(() => {
    if (props.data?.document_type && props.data?.trigger_event) {
        return `${props.data.document_type}\n${props.data.trigger_event}`;
    }
    return props.label || __('Start');
});
</script>

<template>
    <div class="start-node-capsule">
        <div class="capsule-body">
            <div class="glow-effect"></div>
            <div class="content">
                <div class="play-icon">
                    <i class="fa fa-play"></i>
                </div>
                <div class="text-group">
                    <span class="entry-label">{{ __("TRIGGER") }}</span>
                    <span class="main-text">{{ displayLabel }}</span>
                </div>
            </div>
        </div>
        <Handle type="source" :position="Position.Right" id="default" class="handle-source" />
    </div>
</template>

<style scoped>
.start-node-capsule {
    position: relative;
    padding: 2px;
}

.capsule-body {
    background: linear-gradient(135deg, var(--green-500) 0%, #157347 100%);
    color: white;
    padding: 12px 24px 12px 16px;
    border-radius: 50px 10px 50px 10px; /* Aerodynamic Capsule */
    min-width: 160px;
    box-shadow: 0 10px 15px -3px rgba(0, 128, 0, 0.2);
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    transition: all 0.3s ease;
}

.capsule-body:hover {
    transform: translateY(-2px);
    box-shadow: 0 20px 25px -5px rgba(0, 128, 0, 0.3);
}

.glow-effect {
    position: absolute;
    top: -50%;
    left: -50%;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
    pointer-events: none;
}

.content {
    display: flex;
    align-items: center;
    gap: 12px;
    z-index: 1;
}

.play-icon {
    width: 32px;
    height: 32px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    backdrop-filter: blur(4px);
}

.text-group {
    display: flex;
    flex-direction: column;
}

.entry-label {
    font-size: 8px;
    font-weight: 900;
    opacity: 0.8;
    letter-spacing: 1px;
}

.main-text {
    font-size: 13px;
    font-weight: 700;
    white-space: pre-line;
    line-height: 1.1;
}

.handle-source {
    background: white !important;
    border: 3px solid var(--green-600) !important;
    width: 14px !important;
    height: 14px !important;
    right: -7px !important;
}
</style>
