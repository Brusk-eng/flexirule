
<template>
  <div class="condition-builder">
      <div v-if="!modelValue || (!modelValue.op && (!modelValue.conditions || modelValue.conditions.length === 0))" class="text-center p-4">
          <button class="btn btn-primary" @click="initializeModel">Initialize Conditions</button>
      </div>
      
      <ConditionGroup 
        v-else 
        :modelValue="root" 
        :isRoot="true" 
        :docFields="docFields"
        @update:modelValue="val => root = val"
        @add-condition="addCondition"
        @add-group="addGroup"
        @add-collection="addCollection"
      />
      
      <!-- Debug View -->
      <div v-if="debug" class="mt-4 p-2 bg-gray-100 text-xs font-mono border-t">
          <pre>{{ JSON.stringify(root, null, 2) }}</pre>
      </div>
  </div>
</template>

<script>
import ConditionGroup from './ConditionGroup.vue';
import { useConditionTree } from './useConditionTree';

export default {
    name: "ConditionBuilder",
    components: {
        ConditionGroup
    },
    props: {
        modelValue: Object,
        docFields: Array,
        debug: {
            type: Boolean,
            default: false
        }
    },
    emits: ["update:modelValue"],
    setup(props, { emit }) {
        const { 
            root, 
            initializeModel, 
            addCondition, 
            addGroup, 
            addCollection 
        } = useConditionTree(props, emit);
        
        return {
            root,
            initializeModel,
            addCondition,
            addGroup,
            addCollection
        };
    }
}
</script>
