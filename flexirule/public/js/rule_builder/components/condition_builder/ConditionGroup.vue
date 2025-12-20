
<template>
  <div class="condition-group p-4 mb-4 rounded border" :class="isRoot ? 'bg-light-gray shadow-sm' : 'bg-white'">
    <!-- Group Header: Logical Operator Switch -->
    <div class="d-flex justify-content-between align-items-center mb-3">
        <div class="btn-group btn-group-sm bg-white border rounded p-1">
            <button 
                class="btn btn-xs" 
                :class="group.op === 'and' ? 'btn-primary shadow-sm' : 'btn-ghost'"
                @click="group.op = 'and'"
            >{{ __("AND") }}</button>
            <button 
                class="btn btn-xs" 
                :class="group.op === 'or' ? 'btn-primary shadow-sm' : 'btn-ghost'"
                @click="group.op = 'or'"
            >{{ __("OR") }}</button>
        </div>
        
        <div class="d-flex gap-2">
            <button class="btn btn-xs btn-default border-gray-300" @click="emit('add-condition', group)">
                <i class="fa fa-plus mr-1"></i> {{ __("Condition") }}
            </button>
            <button class="btn btn-xs btn-default border-gray-300" @click="emit('add-group', group)">
                <i class="fa fa-folder-open-o mr-1"></i> {{ __("Group") }}
            </button>
            <button class="btn btn-xs btn-default border-gray-300" @click="emit('add-collection', group)">
                <i class="fa fa-table mr-1"></i> {{ __("Collection") }}
            </button>
            <button v-if="!isRoot" class="btn btn-xs btn-link text-danger p-0 ml-2" @click="emit('remove', index)">
                <i class="fa fa-times"></i>
            </button>
        </div>
    </div>

    <!-- Children -->
    <div class="group-content pl-4">
        <div v-if="!group.conditions || group.conditions.length === 0" class="text-muted text-sm py-3 italic text-center border-dashed border rounded bg-white-50">
            {{ __("No conditions. Click buttons above to start.") }}
        </div>
        
        <div v-for="(node, idx) in group.conditions" :key="node.id || idx" class="mb-3 last:mb-0">
            <!-- Leaf Condition (Has left) -->
            <ConditionRow 
                v-if="node.left" 
                v-model="group.conditions[idx]"
                :docFields="docFields"
                @remove="removeNode(idx)"
            />

            <!-- Nested Group (Has conditions, no where) -->
            <ConditionGroup 
                v-else-if="node.conditions && !node.where"
                :modelValue="node"
                :isRoot="false"
                :docFields="docFields"
                :index="idx"
                @update:modelValue="val => group.conditions[idx] = val"
                @remove="removeNode"
                @add-condition="emit('add-condition', $event)"
                @add-group="emit('add-group', $event)"
                @add-collection="emit('add-collection', $event)"
            />

             <!-- Collection (Child Table) (Has where) -->
             <CollectionRow
                v-else-if="node.where"
                v-model="group.conditions[idx]"
                :docFields="docFields"
                @remove="removeNode(idx)"
            />
        </div>
    </div>
  </div>
</template>

<script>
// Recursive component
import ConditionRow from './ConditionRow.vue';
import CollectionRow from './CollectionRow.vue';

export default {
  name: "ConditionGroup",
  components: {
    ConditionRow,
    CollectionRow
  },
  props: {
    modelValue: Object,
    isRoot: Boolean,
    index: Number,
    docFields: Array
  },
  emits: ["update:modelValue", "remove", "add-condition", "add-group", "add-collection"],
  setup(props, { emit }) {
      const parentEmit = emit; 
      const group = props.modelValue;
      
      const removeNode = (idx) => {
          group.conditions.splice(idx, 1);
      }
      
      return { group, removeNode, emit: parentEmit }
  }
};
</script>

<style scoped>
.condition-group {
    border-color: var(--border-color) !important;
}

.bg-light-gray {
    background-color: #f8fafc;
}

.group-content {
    border-left: 2px solid var(--gray-200);
}

.btn-ghost {
    background: transparent;
    border: none;
    color: var(--text-muted);
}
.btn-ghost:hover {
    background: var(--gray-100);
    color: var(--text-color);
}

.border-gray-300 {
    border-color: #d1d5db !important;
}

.bg-white-50 {
    background-color: rgba(255, 255, 255, 0.5);
}

.last\:mb-0:last-child {
    margin-bottom: 0 !important;
}
</style>
