<template>
    <div class="mapping-wrapper">
        <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="mb-0">
                {{ label }}
                <span v-if="reqd" class="text-danger">*</span>
            </label>
            <button class="btn btn-xs btn-default" @click="toggleMode" :title="isMapped ? 'Switch to Static Value' : 'Switch to Dynamic Variable'">
                <i class="fa" :class="isMapped ? 'fa-bolt text-warning' : 'fa-font text-muted'"></i>
            </button>
        </div>
        
        <div v-if="isMapped">
            <ContextPicker 
                :modelValue="mappingValue"
                @update:modelValue="$emit('update:mappingValue', $event)"
            />
        </div>
        <div v-else>
            <slot></slot>
        </div>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import ContextPicker from './ContextPicker.vue';

const props = defineProps({
    label: String,
    reqd: [Boolean, Number],
    mappingValue: String
});

const emit = defineEmits(['update:mappingValue', 'clearStatic']);

const isMapped = ref(false);

watch(() => props.mappingValue, (val) => {
    if (val) isMapped.value = true;
}, { immediate: true });

function toggleMode() {
    isMapped.value = !isMapped.value;
    
    if (isMapped.value) {
        // Switched to Mapped: Clear static value in parent
        emit('clearStatic');
    } else {
        // Switched to Static: Clear mapping value
        emit('update:mappingValue', undefined);
    }
}
</script>
