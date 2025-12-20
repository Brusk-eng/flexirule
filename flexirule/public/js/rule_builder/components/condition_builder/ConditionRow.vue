<template>
  <div class="condition-row p-3 mb-2 border rounded bg-white gap-3">
    
    <!-- Left Operand (Field) -->
    <div class="field-col">
       <label class="condition-label">{{ __("Field") }}</label>
        <input 
          :list="'docfields-' + modelValue.id"
          v-model="modelValue.left.ref" 
          class="form-control input-sm"
          :placeholder="__('Select Field...')"
        />
        <datalist :id="'docfields-' + modelValue.id">
            <option v-for="field in docFields" :key="field.value" :value="field.value">{{ field.label }}</option>
        </datalist>
            
       <div v-if="selectedField" class="field-type-hint">
           {{ selectedField.fieldtype }}
       </div>
    </div>

    <!-- Operator -->
    <div class="operator-col">
        <label class="condition-label">{{ __("Operator") }}</label>
        <select v-model="modelValue.op" class="form-control input-sm">
            <option v-for="op in availableOperators" :key="op.value" :value="op.value">
                {{ op.label }}
            </option>
        </select>
    </div>

    <!-- Right Operand -->
    <div class="value-col" v-if="modelValue.op !== 'has_changed' && !['is_set', 'is_not_set'].includes(modelValue.op)">
         <MappingWrapper 
            :label="__('Value')"
            :mappingValue="modelValue.right.ref"
            @update:mappingValue="setMapping($event)"
            @clearStatic="modelValue.right.value = ''"
         >
             <!-- Input: Value Mode (Static) -->
             <div class="static-input-wrapper">
                 <ControlFactory 
                    :df="selectedField"
                    v-model="modelValue.right.value"
                 />
             </div>
         </MappingWrapper>
         <div v-if="selectedField" class="field-type-hint">
            {{ selectedField.fieldtype }}
         </div>
    </div>

    <!-- Remove -->
    <div class="remove-col">
        <button class="btn btn-xs btn-link text-danger remove-btn" @click="$emit('remove')" :title="__('Remove Condition')">
            <i class="fa fa-trash-o"></i>
        </button>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';
import ControlFactory from '../../controls/ControlFactory.vue';
import MappingWrapper from '../MappingWrapper.vue';

export default {
  name: "ConditionRow",
  components: {
    ControlFactory,
    MappingWrapper
  },
  props: {
    modelValue: { type: Object, required: true },
    docFields: { type: Array, default: () => [] }
  },
  emits: ["update:modelValue", "remove"],
  setup(props) {
      
      const setMapping = (val) => {
          if (val) {
              props.modelValue.right = { ref: val };
          } else {
              props.modelValue.right = { value: "" };
          }
      };

      // Compute selected field metadata based on left.ref
      const selectedField = computed(() => {
          if (!props.modelValue.left?.ref) return null;
          return props.docFields.find(f => f.value === props.modelValue.left.ref);
      });

      const fieldOptions = computed(() => {
          if (selectedField.value?.options && typeof selectedField.value.options === 'string') {
               return selectedField.value.options.split('\n').filter(o => o);
          }
          return [];
      });

      const availableOperators = computed(() => {
          const type = selectedField.value?.fieldtype;
          const ops = [
              { value: "==", label: __("Equals") },
              { value: "!=", label: __("Not Equals") },
              { value: "is_set", label: __("Is Set") },
              { value: "is_not_set", label: __("Is Not Set") },
              { value: "has_changed", label: __("Has Changed") }
          ];

          if (['Int', 'Float', 'Currency', 'Percent', 'Date', 'Datetime'].includes(type)) {
              ops.push(
                  { value: ">", label: ">" },
                  { value: "<", label: "<" },
                  { value: ">=", label: ">=" },
                  { value: "<=", label: "<=" }
              );
          }
          
          if (['Data', 'Text', 'Small Text', 'Long Text', 'Code'].includes(type) || !type) {
              ops.push(
                  { value: "contains", label: __("Contains") },
                  { value: "not_contains", label: __("Not Contains") },
                  { value: "in", label: __("In") },
                  { value: "not in", label: __("Not In") }
              );
          }

          return ops;
      });
      
      return { 
          selectedField, 
          availableOperators, 
          fieldOptions,
          setMapping
      };
  }
};
</script>

<style scoped>
.condition-row {
    display: grid;
    grid-template-columns: 1fr 140px 1.5fr 32px;
    align-items: start;
    padding: 12px;
    background: #fff;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    transition: box-shadow 0.2s;
}

.condition-row:hover {
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* Responsive: Stack on small containers (like narrow sidebar) */
@media (max-width: 600px) {
    .condition-row {
        grid-template-columns: 1fr;
        gap: 12px;
    }
    .remove-col {
        justify-self: end;
    }
}

.condition-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 6px;
    display: block;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.field-type-hint {
    font-size: 10px;
    color: var(--gray-500);
    margin-top: 6px;
    font-style: italic;
    font-weight: 400;
}

.remove-col {
    align-self: center;
    padding-top: 16px; /* Offset for label height */
}

.remove-btn {
    opacity: 0.6;
    transition: opacity 0.2s;
}
.remove-btn:hover {
    opacity: 1;
}

/* MappingWrapper overrides to fit in grid */
.condition-row :deep(.mapping-wrapper) {
    margin-bottom: 0px;
}
.condition-row :deep(.mapping-wrapper .d-flex) {
    margin-bottom: 4px !important;
}
.condition-row :deep(.mapping-wrapper label) {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.02em;
}
</style>
