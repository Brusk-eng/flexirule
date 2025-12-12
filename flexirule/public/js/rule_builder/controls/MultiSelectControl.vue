<script setup>
/**
 * MultiSelectControl - Like Frappe Report Multiselect
 * Renders options as toggleable pills/chips
 */
import { ref, computed, watch, onMounted } from "vue";

const props = defineProps({
    df: Object,
    modelValue: [Array, String],
    read_only: Boolean
});

const emit = defineEmits(["update:modelValue"]);

const selected = computed({
    get() {
        if (Array.isArray(props.modelValue)) return props.modelValue;
        if (typeof props.modelValue === 'string' && props.modelValue) {
            try {
                return JSON.parse(props.modelValue);
            } catch {
                return props.modelValue.split(',').map(s => s.trim()).filter(Boolean);
            }
        }
        return [];
    },
    set(val) {
        emit("update:modelValue", val);
    }
});

const options = computed(() => {
    const opts = props.df?.options || '';
    if (Array.isArray(opts)) return opts;
    if (typeof opts === 'string') {
        return opts.split('\n').map(o => o.trim()).filter(Boolean);
    }
    return [];
});

function toggle(opt) {
    if (props.read_only) return;
    const current = [...selected.value];
    const idx = current.indexOf(opt);
    if (idx >= 0) {
        current.splice(idx, 1);
    } else {
        current.push(opt);
    }
    emit("update:modelValue", current);
}

function isSelected(opt) {
    return selected.value.includes(opt);
}

function selectAll() {
    emit("update:modelValue", [...options.value]);
}

function clearAll() {
    emit("update:modelValue", []);
}
</script>

<template>
    <div class="multiselect-control">
        <label v-if="df.label" class="control-label">
            {{ __(df.label) }}
            <span v-if="df.reqd" class="text-danger">*</span>
        </label>
        
        <div class="multiselect-actions" v-if="!read_only && options.length > 3">
            <button type="button" class="btn btn-xs btn-default" @click="selectAll">
                {{ __("Select All") }}
            </button>
            <button type="button" class="btn btn-xs btn-default" @click="clearAll">
                {{ __("Clear") }}
            </button>
        </div>
        
        <div class="multiselect-pills">
            <button
                v-for="opt in options"
                :key="opt"
                type="button"
                class="pill-btn"
                :class="{ active: isSelected(opt), disabled: read_only }"
                @click="toggle(opt)"
                :disabled="read_only"
            >
                <span class="pill-check" v-if="isSelected(opt)">✓</span>
                {{ __(opt.replace(/_/g, ' ')) }}
            </button>
        </div>
        
        <small v-if="df.description" class="form-text text-muted">
            {{ df.description }}
        </small>
    </div>
</template>

<style scoped>
.multiselect-control { margin-bottom: 15px; }
.control-label { font-size: 12px; font-weight: 500; margin-bottom: 8px; display: block; }
.multiselect-actions { margin-bottom: 8px; display: flex; gap: 5px; }
.multiselect-pills { display: flex; flex-wrap: wrap; gap: 6px; }
.pill-btn {
    display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px;
    font-size: 12px; border: 1px solid var(--border-color, #d1d8dd);
    border-radius: 16px; background: var(--bg-color, white);
    cursor: pointer; transition: all 0.15s ease;
}
.pill-btn:hover:not(.disabled) { border-color: var(--primary); background: var(--bg-light-blue, #f0f8ff); }
.pill-btn.active { background: var(--primary); border-color: var(--primary); color: white; }
.pill-btn.disabled { opacity: 0.6; cursor: not-allowed; }
.pill-check { font-size: 10px; font-weight: bold; }
</style>
