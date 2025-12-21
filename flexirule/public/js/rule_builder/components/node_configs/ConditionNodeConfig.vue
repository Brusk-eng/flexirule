<template>
    <div class="condition-node-config">
        <div class="form-group">
            <label>{{ __("Expression (Legacy)") }}</label>
            <div class="help-text text-muted mb-2" style="font-size: 11px;">{{ __("ReadOnly: Auto-compiled from Condition Builder") }}</div>
            <textarea class="form-control" rows="3" readonly
                :value="nodeData?.condition_expression"
                placeholder="Active = True"></textarea>
            
            <button class="btn btn-default btn-sm w-100 mt-2" @click="$emit('open-condition-builder')">
                <i class="fa fa-code-fork"></i> {{ __("Open Condition Builder") }}
            </button>
            
            <div v-if="nodeData?.condition_json && nodeData.condition_json !== '{}'" class="mt-2" style="font-size: 12px; color: var(--text-muted);">
                 <i class="fa fa-check-circle text-success"></i> {{ __("Conditions Configured") }}
            </div>
        </div>
    </div>
</template>

<script setup>
defineProps({
    nodeData: Object
});

defineEmits(['open-condition-builder']);
</script>
