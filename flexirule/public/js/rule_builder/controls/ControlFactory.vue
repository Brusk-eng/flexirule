<template>
  <div class="control-factory">
      <!-- Link -->
      <LinkControl v-if="df?.fieldtype === 'Link'"
          :df="df"
          :modelValue="modelValue"
          @update:modelValue="$emit('update:modelValue', $event)"
      />

      <!-- Select -->
      <SelectControl v-else-if="df?.fieldtype === 'Select'"
          :df="df"
          :modelValue="modelValue"
          @update:modelValue="$emit('update:modelValue', $event)"
      />

      <!-- Check -->
      <CheckControl v-else-if="df?.fieldtype === 'Check'"
          :df="df"
          :modelValue="modelValue"
          @update:modelValue="$emit('update:modelValue', $event)"
      />

      <!-- Number (Int, Float, Currency, Percent) -->
      <input v-else-if="['Int', 'Float', 'Currency', 'Percent'].includes(df?.fieldtype)"
          type="number"
          step="any"
          class="form-control input-sm"
          :value="modelValue"
          @input="$emit('update:modelValue', df.fieldtype === 'Int' ? parseInt($event.target.value) : parseFloat($event.target.value))"
      />

      <!-- Date / Datetime -->
      <input v-else-if="['Date', 'Datetime'].includes(df?.fieldtype)"
          :type="df.fieldtype === 'Date' ? 'date' : 'datetime-local'"
          class="form-control input-sm"
          :value="modelValue"
          @input="$emit('update:modelValue', $event.target.value)"
      />

      <!-- MultiSelect -->
      <MultiSelectControl v-else-if="df?.fieldtype === 'MultiSelect' || df?.fieldtype === 'Table MultiSelect'"
          :df="df"
          :modelValue="modelValue"
          @update:modelValue="$emit('update:modelValue', $event)"
      />

      <!-- Default (Data, Text, etc.) -->
      <DataControl v-else
          :df="df || { fieldtype: 'Data' }"
          :modelValue="modelValue"
          @update:modelValue="$emit('update:modelValue', $event)"
      />
  </div>
</template>

<script setup>
import LinkControl from './LinkControl.vue';
import SelectControl from './SelectControl.vue';
import CheckControl from './CheckControl.vue';
import DataControl from './DataControl.vue';
import MultiSelectControl from './MultiSelectControl.vue';

const props = defineProps({
  df: Object,
  modelValue: [String, Number, Boolean, Array]
});

defineEmits(['update:modelValue']);
</script>
