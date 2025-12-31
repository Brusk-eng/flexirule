<template>
    <div class="loop-node-config">
        <div class="form-group">
            <label>{{ __("Iterator (Python)") }}</label>
            <input type="text" class="form-control" 
                :value="getJsonConfig('iterator')"
                @input="$emit('update-json-config', 'iterator', $event.target.value)"
                placeholder="doc.items" />
            <div class="help-text text-muted" style="font-size:11px">{{ __("List to iterate over.") }}</div>
        </div>
        <div class="form-group">
            <label>{{ __("Item Alias") }}</label>
            <input type="text" class="form-control" 
                :value="getJsonConfig('alias')"
                @input="$emit('update-json-config', 'alias', $event.target.value)"
                placeholder="item" />
            <div class="help-text text-muted" style="font-size:11px">{{ __("Variable name for current item.") }}</div>
        </div>
    </div>
</template>

<script setup>
const props = defineProps({
    nodeData: Object
});

defineEmits(['update-json-config']);

function getJsonConfig(key, defaultVal = '') {
    // Support both new 'config' and legacy 'method_config'
    const configStr = props.nodeData?.config || props.nodeData?.method_config;
    if (!configStr) return defaultVal;
    try {
        const config = JSON.parse(configStr);
        return config[key] !== undefined ? config[key] : defaultVal;
    } catch (e) {
        return defaultVal;
    }
}
</script>
