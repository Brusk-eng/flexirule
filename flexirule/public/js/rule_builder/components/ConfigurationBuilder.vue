<template>
    <div class="config-builder">
        <div class="config-header">
            <h6>{{ __("Configure Process Method") }}</h6>
            <button class="btn btn-xs btn-secondary" @click="clearAll">{{ __("Clear All") }}</button>
        </div>
        
        <div class="config-body">
            <template v-for="(field, idx) in visibleFields" :key="field.fieldname">
                <!-- Section Break -->
                <div v-if="field.fieldtype === 'Section Break'" class="section-break">
                    <h6 v-if="field.label">{{ __(field.label) }}</h6>
                    <hr v-else />
                </div>
                
                <!-- Column Break -->
                <div v-else-if="field.fieldtype === 'Column Break'" class="column-break"></div>
                
                <!-- Regular fields -->
                <MappingWrapper 
                    v-else
                    :label="__(field.label)"
                    :reqd="isMandatory(field)"
                    :mappingValue="mappingValues[field.fieldname]"
                    @update:mappingValue="updateMapping(field.fieldname, $event)"
                    @clearStatic="updateValue(field.fieldname, undefined)"
                >
                    <!-- DocField / FieldPicker -->
                    <FieldPickerControl
                        v-if="field.fieldtype === 'DocField'"
                        :df="field"
                        :documentType="documentType"
                        :modelValue="values[field.fieldname]"
                        @update:modelValue="updateValue(field.fieldname, $event)"
                    />
                    
                    <!-- MultiDocField / MultiFieldPicker -->
                    <MultiFieldPickerControl
                        v-else-if="field.fieldtype === 'MultiDocField'"
                        :df="field"
                        :documentType="documentType"
                        :modelValue="values[field.fieldname]"
                        @update:modelValue="updateValue(field.fieldname, $event)"
                    />
                    
                    <!-- MultiSelect -->
                    <MultiSelectControl
                        v-else-if="field.fieldtype === 'MultiSelect'"
                        :df="field"
                        :modelValue="values[field.fieldname]"
                        @update:modelValue="updateValue(field.fieldname, $event)"
                    />
                    
                    <!-- Table -->
                    <InlineTableControl
                        v-else-if="field.fieldtype === 'Table'"
                        :df="field"
                        :documentType="documentType"
                        :modelValue="values[field.fieldname]"
                        @update:modelValue="updateValue(field.fieldname, $event)"
                    />
                    
                    <!-- Percent Slider -->
                    <PercentSliderControl
                        v-else-if="field.fieldtype === 'Percent'"
                        :df="field"
                        :modelValue="values[field.fieldname]"
                        @update:modelValue="updateValue(field.fieldname, $event)"
                    />
                    
                    <!-- Select dropdown -->
                    <select 
                        v-else-if="field.fieldtype === 'Select'"
                        class="form-control form-control-sm"
                        :value="values[field.fieldname]"
                        @change="updateValue(field.fieldname, $event.target.value)"
                    >
                        <option value="">{{ __("Select...") }}</option>
                        <option v-for="opt in getSelectOptions(field)" :key="opt" :value="opt">
                            {{ __(opt) }}
                        </option>
                    </select>
                    
                    <!-- Checkbox -->
                    <div v-else-if="field.fieldtype === 'Check'" class="form-check">
                        <input 
                            type="checkbox"
                            class="form-check-input"
                            :id="'check-' + field.fieldname"
                            :checked="values[field.fieldname]"
                            @change="updateValue(field.fieldname, $event.target.checked)"
                        />
                    </div>
                    
                    <!-- Link -->
                    <LinkControl
                        v-else-if="field.fieldtype === 'Link'"
                        :df="field"
                        :modelValue="values[field.fieldname]"
                        @update:modelValue="updateValue(field.fieldname, $event)"
                    />
                    
                    <!-- Dynamic Link -->
                    <LinkControl
                        v-else-if="field.fieldtype === 'Dynamic Link'"
                        :df="{...field, options: values[field.options] || ''}"
                        :modelValue="values[field.fieldname]"
                        @update:modelValue="updateValue(field.fieldname, $event)"
                    />
                    
                    <!-- Code / Small Text -->
                    <textarea 
                        v-else-if="field.fieldtype === 'Code' || field.fieldtype === 'Small Text'"
                        class="form-control form-control-sm"
                        :value="values[field.fieldname]"
                        @input="updateValue(field.fieldname, $event.target.value)"
                        :placeholder="__(field.description)"
                        rows="3"
                    ></textarea>
                    
                    <!-- Text Editor -->
                    <textarea 
                        v-else-if="field.fieldtype === 'Text Editor'"
                        class="form-control form-control-sm"
                        :value="values[field.fieldname]"
                        @input="updateValue(field.fieldname, $event.target.value)"
                        rows="5"
                    ></textarea>
                    
                    <!-- Number inputs -->
                    <input 
                        v-else-if="field.fieldtype === 'Int' || field.fieldtype === 'Float'"
                        type="number"
                        class="form-control form-control-sm"
                        :value="values[field.fieldname]"
                        @input="updateValue(field.fieldname, parseFloat($event.target.value))"
                        :step="field.fieldtype === 'Float' ? '0.01' : '1'"
                    />
                    
                    <!-- Default text input -->
                    <input 
                        v-else
                        type="text"
                        class="form-control form-control-sm"
                        :value="values[field.fieldname]"
                        @input="updateValue(field.fieldname, $event.target.value)"
                        :placeholder="__(field.description)"
                    />
                    
                    <small v-if="field.description && !['DocField', 'MultiDocField', 'MultiSelect'].includes(field.fieldtype)" 
                           class="form-text text-muted">
                        {{ __(field.description) }}
                    </small>
                </MappingWrapper>
            </template>
        </div>
        
        <div v-if="validationErrors.length" class="alert alert-danger">
            <ul class="mb-0">
                <li v-for="error in validationErrors" :key="error">{{ error }}</li>
            </ul>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { parseSchemaToFields, validateConfigAgainstSchema } from '../utils/schemaParser.js';

// Import new controls
import MultiSelectControl from '../controls/MultiSelectControl.vue';
import FieldPickerControl from '../controls/FieldPickerControl.vue';
import MultiFieldPickerControl from '../controls/MultiFieldPickerControl.vue';
import InlineTableControl from '../controls/InlineTableControl.vue';
import PercentSliderControl from '../controls/PercentSliderControl.vue';
import LinkControl from '../controls/LinkControl.vue';
import MappingWrapper from './MappingWrapper.vue';

const props = defineProps({
    schema: Object,
    modelValue: [String, Object], // Config JSON
    inputMapping: [String, Object], // Mapping JSON
    documentType: String
});

const emit = defineEmits(['update:modelValue', 'update:inputMapping', 'validation-change']);

const fields = ref([]);
const values = ref({}); // Static config
const mappingValues = ref({}); // Input mapping
const validationErrors = ref([]);

// Parse schema to fields
watch(() => props.schema, (schema) => {
    if (!schema) {
        fields.value = [];
        return;
    }
    fields.value = parseSchemaToFields(schema, props.documentType);
}, { immediate: true });

// Parse model value
watch(() => props.modelValue, (val) => {
    try {
        values.value = typeof val === 'string' ? JSON.parse(val) : (val || {});
    } catch (e) {
        values.value = {};
    }
    validate();
}, { immediate: true });

// Parse input mapping
watch(() => props.inputMapping, (val) => {
    try {
        mappingValues.value = typeof val === 'string' ? JSON.parse(val) : (val || {});
    } catch (e) {
        mappingValues.value = {};
    }
}, { immediate: true });

// Filter visible fields based on depends_on
const visibleFields = computed(() => {
    return fields.value.filter(field => {
        if (!field.depends_on) return true;
        return evaluateDependsOn(field.depends_on, values.value);
    });
});

// Evaluate if a field is mandatory (supports mandatory_depends_on)
function isMandatory(field) {
    if (field.reqd) return true;
    if (!field.mandatory_depends_on) return false;
    return evaluateDependsOn(field.mandatory_depends_on, values.value);
}

// Evaluate depends_on expression
function evaluateDependsOn(expression, formData) {
    if (!expression) return true;
    
    // Parse "eval:doc.field=='value'" format
    const match = expression.match(/^eval:(.+)$/);
    if (!match) return true;
    
    let condition = match[1];
    
    // Replace doc.X with actual values
    condition = condition.replace(/doc\.(\w+)/g, (_, fieldname) => {
        const val = formData[fieldname];
        if (val === undefined || val === null) return "''";
        if (typeof val === 'string') return `'${val}'`;
        return String(val);
    });
    
    try {
        return new Function(`return ${condition}`)();
    } catch (e) {
        console.warn('depends_on evaluation failed:', expression, e);
        return true;
    }
}

function getSelectOptions(field) {
    const opts = field.options || '';
    if (typeof opts === 'string') {
        return opts.split('\n').filter(Boolean);
    }
    return opts;
}

function updateValue(fieldname, value) {
    // If value is undefined, remove key
    if (value === undefined) {
        const newValues = { ...values.value };
        delete newValues[fieldname];
        values.value = newValues;
    } else {
        values.value = { ...values.value, [fieldname]: value };
    }
    emit('update:modelValue', JSON.stringify(values.value));
    validate();
}

function updateMapping(fieldname, value) {
    if (value === undefined) {
        const newMapping = { ...mappingValues.value };
        delete newMapping[fieldname];
        mappingValues.value = newMapping;
    } else {
        mappingValues.value = { ...mappingValues.value, [fieldname]: value };
    }
    emit('update:inputMapping', JSON.stringify(mappingValues.value));
}

function validate() {
    // Note: Validation should check IF mapped OR configured for required fields
    // This requires merging config + mapping for validation purposes
    // Or updated validateConfigAgainstSchema to accept mappings.
    // For now, keeping as is (checks config only). 
    // Ideally, if a field is mapped, it should be considered "filled".
    
    // Merge for validation check
    const mergedForValidation = { ...values.value, ...mappingValues.value };
    
    const result = validateConfigAgainstSchema(mergedForValidation, props.schema);
    validationErrors.value = result.errors || [];
    emit('validation-change', result.valid);
}

function clearAll() {
    values.value = {};
    mappingValues.value = {};
    emit('update:modelValue', '{}');
    emit('update:inputMapping', '{}');
    validate();
}
</script>

<style scoped>
.config-builder {
    max-height: 500px;
    overflow-y: auto;
}
.config-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    background: white;
    z-index: 1;
}
.config-header h6 {
    margin: 0;
    font-size: 13px;
}
.config-body {
    padding: 15px;
}
.form-group {
    margin-bottom: 15px;
}
.form-group > label {
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 5px;
    display: block;
}
.section-break {
    margin: 20px 0 15px;
}
.section-break h6 {
    font-size: 12px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin: 0 0 10px;
}
.section-break hr {
    margin: 0;
}
.column-break {
    height: 10px;
}
.form-check {
    padding-left: 0;
}
.alert {
    margin: 10px;
    font-size: 12px;
}
</style>
