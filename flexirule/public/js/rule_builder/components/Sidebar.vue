<template>
    <div class="rule-sidebar">
        <div class="sidebar-header">
            <h4>{{ selectedNode?.data?.action_label || selectedNode?.label || 'Properties' }}</h4>
            <button class="btn-close" @click="$emit('close')">×</button>
        </div>
        
        <div class="sidebar-content" v-if="selectedNode">
            <!-- Start Node -->
            <template v-if="selectedNode.type === 'start'">
                <div class="form-group">
                    <label>Document Type</label>
                    <input type="text" class="form-control" :value="selectedNode.data?.document_type" readonly />
                </div>
                <div class="form-group">
                    <label>Trigger Event</label>
                    <input type="text" class="form-control" :value="selectedNode.data?.trigger_event" readonly />
                </div>
                
                <div class="form-group">
                    <label>Trigger Filters</label>
                    <div class="help-text text-muted mb-2" style="font-size: 11px;">Condition filters evaluated before Rule execution.</div>
                    
                    <button class="btn btn-default btn-sm w-100" @click="editFilters">
                        <i class="fa fa-filter"></i> Set Filters
                    </button>
                    
                    <div v-if="selectedNode.data?.trigger_filters && selectedNode.data.trigger_filters !== '[]'" class="mt-2" style="font-size: 12px; color: var(--text-muted);">
                        <i class="fa fa-check-circle text-success"></i> Filters Configured
                    </div>
                </div>
            </template>
            
            <!-- Action Nodes -->
            <template v-else>
                <div class="form-group">
                    <label>Label</label>
                    <input type="text" class="form-control" 
                        :value="selectedNode.label"
                        @input="updateLabel($event.target.value)" />
                </div>
                
                <div class="form-group">
                    <label>Type</label>
                    <select class="form-control" 
                        :value="selectedNode.data?.action_type"
                        @change="updateActionType($event.target.value)">
                        <option value="Process">Process</option>
                        <option value="Condition">Condition</option>
                        <option value="Switch">Switch</option>
                        <option value="Wait">Wait</option>
                        <option value="Sub-Rule">Sub-Rule</option>
                        <option value="Stop">Stop</option>
                    </select>
                </div>
                
                <template v-if="selectedNode.data?.action_type === 'Process'">
                    <div class="form-group relative">
                        <label>Method</label>
                        <div class="input-group">
                            <input type="text" class="form-control" 
                                v-model="methodSearch"
                                @focus="showMethodSuggestions = true"
                                @input="filterMethods"
                                placeholder="Search method..." />
                            <button class="btn btn-default btn-sm" @click="showMethodDescription" title="Show Description">
                                <i class="fa fa-info-circle"></i>
                            </button>
                        </div>
                        
                        <div v-if="showMethodSuggestions" class="suggestions-dropdown">
                            <div v-for="m in store.process_methods.filter(m => 
                                    m.method_name.toLowerCase().includes(methodSearch.toLowerCase()) || 
                                    (m.method_path && m.method_path.toLowerCase().includes(methodSearch.toLowerCase()))
                                )" 
                                :key="m.name" 
                                class="suggestion-item"
                                @click="selectMethod(m)">
                                <div class="suggestion-name">{{ m.method_name }}</div>
                                <div class="suggestion-path" v-if="m.method_path">{{ m.method_path }}</div>
                            </div>
                            <div v-if="!store.process_methods.length" class="p-2 text-muted">No methods found</div>
                        </div>
                    </div>
                    
                    <button v-if="selectedNode.data?.process_method"
                        class="btn btn-sm btn-default w-100 mb-3" 
                        @click="openConfigDialog">
                        <i class="fa fa-cog"></i> Configure
                    </button>

                    <div class="row">
                        <div class="col-xs-6">
                            <div class="form-group">
                                <label>Timeout (s)</label>
                                <input type="number" class="form-control" 
                                    :value="selectedNode.data?.timeout || 30"
                                    @input="updateField('timeout', parseInt($event.target.value))" />
                            </div>
                        </div>
                        <div class="col-xs-6">
                            <div class="form-group">
                                <label>Priority</label>
                                <input type="number" class="form-control" 
                                    :value="selectedNode.data?.priority || 0"
                                    @input="updateField('priority', parseInt($event.target.value))" />
                            </div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>On Error</label>
                        <select class="form-control" 
                            :value="selectedNode.data?.on_error || 'Stop'"
                            @change="updateField('on_error', $event.target.value)">
                            <option value="Stop">Stop</option>
                            <option value="Continue">Continue</option>
                            <option value="Retry">Retry</option>
                            <option value="Rollback">Rollback</option>
                            <option value="Escalate">Escalate</option>
                        </select>
                    </div>

                    <div class="form-group" v-if="selectedNode.data?.on_error === 'Retry'">
                        <label>Retry Count</label>
                        <input type="number" class="form-control" 
                            :value="selectedNode.data?.retry_count || 0"
                            @input="updateField('retry_count', parseInt($event.target.value))" />
                    </div>

                    <div class="form-group">
                        <label>Return Variable</label>
                        <input type="text" class="form-control" 
                            :value="selectedNode.data?.return_variable"
                            @input="updateField('return_variable', $event.target.value)" 
                            placeholder="result_var_name" />
                    </div>

                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" 
                                :checked="selectedNode.data?.is_async"
                                @change="updateField('is_async', $event.target.checked ? 1 : 0)" />
                            Run Asynchronously
                        </label>
                    </div>
                </template>

                <template v-if="selectedNode.data?.action_type === 'Sub-Rule'">
                    <div class="form-group">
                        <label>Select Rule</label>
                        <input type="text" class="form-control" 
                             :value="selectedNode.data?.sub_rule_name" 
                             @input="updateSubRuleName($event.target.value)"
                             placeholder="Rule Name" />
                         <div class="help-text text-muted" style="font-size:11px">Rule to execute. Context vars are shared.</div>
                    </div>
                </template>

                <template v-if="selectedNode.data?.action_type === 'Switch'">
                    <div class="form-group">
                        <label>Switch Expression (Python)</label>
                        <textarea class="form-control" rows="2"
                            :value="selectedNode.data?.switch_expression"
                            @input="updateSwitchExpression($event.target.value)"
                            placeholder="doc.category"></textarea>
                    </div>
                    <div class="alert alert-warning" style="font-size:11px; padding: 5px;">
                        <i class="fa fa-info-circle"></i> Visual branching for cases is not yet supported. Use 'Default Next' for the fallback path. Configuration of specific cases requires generic Method Config adjustments.
                    </div>
                </template>
                
                <div class="form-group" v-if="selectedNode.data?.action_type === 'Condition'">
                    <label>Expression</label>
                    <textarea class="form-control" rows="3"
                        :value="selectedNode.data?.condition_expression"
                        @input="updateField('condition_expression', $event.target.value)"
                        placeholder="doc.status == 'Active'"></textarea>
                </div>
                
                <div class="form-group" v-if="selectedNode.type !== 'stop'">
                    <label>{{ selectedNode.data?.action_type === 'Condition' ? 'If True →' : 'Next →' }}</label>
                    <select class="form-control"
                        :value="selectedNode.data?.next_step_if_true"
                        @change="updateNextStep('next_step_if_true', $event.target.value)">
                        <option value="">End Flow</option>
                        <option v-for="node in availableNextNodes" :key="node.id" :value="node.id">
                            {{ node.label }}
                        </option>
                    </select>
                </div>
                
                <div class="form-group" v-if="selectedNode.data?.action_type === 'Condition'">
                    <label>If False →</label>
                    <select class="form-control"
                        :value="selectedNode.data?.next_step_if_false"
                        @change="updateNextStep('next_step_if_false', $event.target.value)">
                        <option value="">End Flow</option>
                        <option v-for="node in availableNextNodes" :key="node.id" :value="node.id">
                            {{ node.label }}
                        </option>
                    </select>
                </div>
                
                <hr />
                
                <label class="checkbox-label">
                    <input type="checkbox" 
                        :checked="selectedNode.data?.is_enabled !== 0"
                        @change="updateField('is_enabled', $event.target.checked ? 1 : 0)" />
                    Enabled
                </label>
                
                <button class="btn btn-sm btn-danger w-100 mt-3" @click="deleteNode">
                    <i class="fa fa-trash"></i> Delete
                </button>
            </template>
        </div>
    </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue';
import { useStore } from '../store';

const emit = defineEmits(['close']);
const store = useStore();

const selectedNode = computed(() => store.graph.selected);

// Process Method Autocomplete
const methodSearch = ref('');
const showMethodSuggestions = ref(false);
const methodDescription = ref('');

watch(() => selectedNode.value?.data?.process_method, (newVal) => {
    if (newVal) {
        const method = store.process_methods.find(m => m.name === newVal);
        methodSearch.value = method ? method.method_name : newVal;
        methodDescription.value = method ? method.description : '';
    } else {
        methodSearch.value = '';
        methodDescription.value = '';
    }
}, { immediate: true });

function filterMethods() {
    showMethodSuggestions.value = true;
}

function selectMethod(method) {
    methodSearch.value = method.method_name;
    updateProcessMethod(method.name);
    showMethodSuggestions.value = false;
}

function showMethodDescription() {
    if (methodDescription.value) {
        frappe.msgprint({
            title: __('Method Description'),
            message: methodDescription.value
        });
    } else {
        frappe.msgprint(__('No description available'));
    }
}

function updateStartNodeFilters(filtersJSON) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.trigger_filters = filtersJSON;
    store.mark_dirty();
}

function editFilters() {
    if (!selectedNode.value?.data?.document_type) return;

    const doctype = selectedNode.value.data.document_type;
    const currentFilters = selectedNode.value.data.trigger_filters;

    frappe.model.with_doctype(doctype, () => {
        const dialog = new frappe.ui.Dialog({
            title: __('Set Trigger Filters'),
            fields: [
                {
                    fieldname: 'filter_area',
                    fieldtype: 'HTML',
                    label: 'Filters'
                }
            ],
            size: 'large',
            primary_action_label: __('Set'),
            secondary_action_label: __('Preview Python'),
            secondary_action: () => {
                const values = filter_group.get_filters();
                const expression = convertFiltersToPython(values);
                frappe.msgprint({
                    title: 'Python Expression',
                    message: `<pre>${expression}</pre>`,
                    indicator: 'blue'
                });
            }
        });

        // Set action converts FilterGroup -> Python -> update
        dialog.set_primary_action(__('Set'), () => {
             const values = filter_group.get_filters();
             const expression = convertFiltersToPython(values);
             updateStartNodeFilters(expression);  // Save as Python string
             dialog.hide();
        });

        // Add custom button for Import (optional now, since load handles it, but good for raw edit)
        dialog.add_custom_action(__('Edit Raw Python'), () => {
             const values = filter_group.get_filters();
             const currentExpr = convertFiltersToPython(values);
             
             frappe.prompt(
                { 
                    label: 'Python Expression', fieldname: 'expression', 
                    fieldtype: 'Code', options: 'Python', reqd: 1,
                    default: currentExpr 
                },
                (data) => {
                     updateStartNodeFilters(data.expression);
                     dialog.hide();
                },
                __('Edit Raw Python'),
                __('Save')
            );
        });

        dialog.show();
        
        // Initialize FilterGroup
        const filter_group = new frappe.ui.FilterGroup({
            parent: dialog.get_field("filter_area").$wrapper,
            doctype: doctype,
            on_change: () => {},
        });
        
        // Load initial values: Python String -> JSON Filters
        if (currentFilters && typeof currentFilters === 'string') {
            try {
                // If it looks like a list (legacy support or empty), try JSON parse
                if (currentFilters.trim().startsWith('[') && currentFilters.includes(']')) {
                     try {
                         const jsonFilters = JSON.parse(currentFilters);
                         filter_group.add_filters_to_filter_group(jsonFilters);
                         frappe.show_alert({message: __('Imported successfully'), indicator: 'green'});
                         return;
                     } catch(e) {
                         // Not JSON, proceed as Python
                         frappe.msgprint(__('Could not parse expression. Ensure format is: field == "value"'));
                     }
                }
                
                // Parse Python Expression
                const parsedFilters = convertPythonToFilters(currentFilters, doctype);
                if (parsedFilters && parsedFilters.length) {
                    filter_group.add_filters_to_filter_group(parsedFilters);
                }
            } catch(e) { 
                console.error("Error parsing python filters", e);
                frappe.msgprint(__('Error parsing expression: ') + e.message);
            }
        }
    });
}

function convertFiltersToPython(filters) {
    if (!filters || !filters.length) return "True";
    
    // filters format: [[doctype, field, operator, value], ...]
    const operatorMap = {
        '=': '==',
        '!=': '!=',
        '>': '>',
        '<': '<',
        '>=': '>=',
        '<=': '<=',
        'Like': 'in', // Approximate mapping
        'Not Like': 'not in',
        'In': 'in',
        'Not In': 'not in',
        'is': 'is',
        'like': 'in',
        'not like': 'not in',
        'in': 'in',
        'not in': 'not in'
    };

    return filters.map(f => {
        const field = f[1];
        const op = operatorMap[f[2]] || '==';
        let val = f[3];
        
        // Handle various value types
        if (Array.isArray(val)) {
             // Handle Array -> Tuple
             const quoted = val.map(v => typeof v === 'string' ? `'${v}'` : v);
             val = `(${quoted.join(', ')})`;
        } else if (typeof val === 'string') {
             // If comma separated string for IN operator, convert to tuple
             if ((op === 'in' || op === 'not in') && val.includes(',')) {
                 const parts = val.split(',').map(v => `'${v.trim()}'`);
                 val = `(${parts.join(', ')})`;
             } else {
                 val = `'${val}'`;
             }
        }
        
        // Handle Like/Not Like reversing operands if needed or strict "like"
        // For simplicity using standard python comparison structure
        // No doc. prefix needed for standard frappe.safe_eval(expr, None, doc)
        return `${field} ${op} ${val}`;
    }).join(' and ');
}

function convertPythonToFilters(expression, doctype) {
    // Simple regex parser for field op value
    // Supports AND logic only (which matches Frappe FilterGroup capabilities)
    
    if (!expression) return [];

    const parts = expression.split(/\s+and\s+/i);
    const filters = [];
    
    const opMapReverse = {
        '==': '=',
        '!=': '!=',
        '>': '>',
        '<': '<',
        '>=': '>=',
        '<=': '<=',
        'in': 'in', 
        'not in': 'not in',
        'is': 'is'
    };
    
    // Regex matches: (doc.)?field_name operator 'value' or number or list/tuple
    // Groups: 1=(optional doc.), 2=field, 3=operator, 4=value
    const regex = /(?:doc\.)?(\w+)\s*(==|!=|>=|<=|>|<|in|not in|is)\s*((?:['"].*?['"])|(?:\d+(?:\.\d+)?)|(?:None|True|False)|(?:\[.*?\])|(?:\(.*?\)))/;
    
    for (const part of parts) {
        const match = part.trim().match(regex);
        if (match) {
            const field = match[1]; 
            const op = opMapReverse[match[2]] || '=';
            let val = match[3];
            
            // Unquote string
            if ((val.startsWith("'") && val.endsWith("'")) || (val.startsWith('"') && val.endsWith('"'))) {
                val = val.slice(1, -1);
            }
            // Handle booleans/nulls
            else if (val === 'None') val = '';
            // Handle List/Tuple for 'in' operator
            else if (val.startsWith('[') || val.startsWith('(')) {
                // Convert Python tuple/list string to JS array
                // standardizing quotes to double for JSON parse, simple heuristic
                try {
                    // Replace ' with " and () with []
                    let arrayStr = val.replace(/'/g, '"');
                    if (arrayStr.startsWith('(')) {
                        arrayStr = '[' + arrayStr.slice(1, -1) + ']';
                    }
                    val = JSON.parse(arrayStr);
                } catch(e) {
                    console.warn("Failed to parse list/tuple value", val);
                    // Fallback: strip brackets and standard cleanup if JSON fails?
                    // For now, let it be string if parse fails, though FilterGroup might complain if it expects array
                }
            }
            
            filters.push([doctype, field, op, val]);
        }
    }
    
    return filters;
}

const availableNextNodes = computed(() => {
    return store.graph.elements
        .filter(el => el.position && el.id !== selectedNode.value?.id && el.id !== 'start')
        .map(el => ({ id: el.id, label: el.label || el.id }));
});

function updateLabel(value) {
    if (!selectedNode.value) return;
    selectedNode.value.label = value;
    if (selectedNode.value.data) selectedNode.value.data.action_label = value;
    store.mark_dirty();
}

function updateField(field, value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data[field] = value;
    store.mark_dirty();
}

function updateActionType(value) {
    if (!selectedNode.value) return;
    selectedNode.value.type = value.toLowerCase();
    if (selectedNode.value.data) selectedNode.value.data.action_type = value;
    store.mark_dirty();
}

function updateProcessMethod(value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.process_method = value;
    selectedNode.value.data.method_config = null;
    store.mark_dirty();
}

function updateSubRuleName(value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.sub_rule_name = value;
    // Store in method_config as expected by Engine
    selectedNode.value.data.method_config = JSON.stringify({ "rule": value });
    store.mark_dirty();
}

function updateSwitchExpression(value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data.switch_expression = value;
    // Update method_config with expression. Preserve cases if they exist (though UI doesn't edit them yet)
    let config = {};
    try {
        config = JSON.parse(selectedNode.value.data.method_config || '{}');
    } catch(e) {}
    
    config.expression = value;
    selectedNode.value.data.method_config = JSON.stringify(config);
    store.mark_dirty();
}

function updateNextStep(field, value) {
    if (!selectedNode.value?.data) return;
    selectedNode.value.data[field] = value || null;
    updateEdge(field, value);
    store.mark_dirty();
}

function updateEdge(field, newTarget) {
    const nodeId = selectedNode.value.id;
    const handleType = field === 'next_step_if_true' ? 
        (selectedNode.value.data?.action_type === 'Condition' ? 'true' : 'default') : 'false';
    
    store.graph.elements = store.graph.elements.filter(el => 
        !(el.source === nodeId && el.sourceHandle === handleType)
    );
    
    if (newTarget) {
        store.graph.elements.push({
            id: `e-${nodeId}-${newTarget}-${handleType}`,
            source: nodeId,
            target: newTarget,
            sourceHandle: handleType
        });
    }
}

function deleteNode() {
    if (selectedNode.value) {
        store.delete_node(selectedNode.value.id);
        emit('close');
    }
}

async function openConfigDialog() {
    const methodName = selectedNode.value?.data?.process_method;
    if (!methodName) return;
    
    const schema = await store.get_process_method_schema(methodName);
    if (!schema?.fields) {
        frappe.msgprint(__('No configuration available'));
        return;
    }
    
    const parentDoctype = store.rule_doc?.document_type;
    const childTables = schema.child_tables || {};
    const dialogFields = await buildDialogFields(schema.fields, parentDoctype, childTables);
    
    // Parse current config
    let currentConfig = {};
    try {
        const configStr = selectedNode.value.data?.method_config;
        if (configStr && configStr !== '{}' && configStr !== 'null') {
            currentConfig = JSON.parse(configStr);
        }
    } catch (e) {
        console.error('Failed to parse configuration:', e);
    }
    
    // Pre-populate Table field data in the field definitions
    dialogFields.forEach(f => {
        if (f.fieldtype === 'Table' && currentConfig[f.fieldname]) {
            f.data = currentConfig[f.fieldname];
        } else if (currentConfig[f.fieldname] !== undefined && f.fieldtype !== 'Table') {
            f.default = currentConfig[f.fieldname];
        }
    });
    
    const dialog = new frappe.ui.Dialog({
        title: schema.method_name || methodName,
        fields: dialogFields,
        size: 'large',
        primary_action_label: __('Save'),
        primary_action: () => {
            const values = dialog.get_values();
            if (values) {
                // For Table fields, get data from grid
                dialogFields.forEach(f => {
                    if (f.fieldtype === 'Table') {
                        const field = dialog.fields_dict[f.fieldname];
                        if (field && field.grid) {
                            values[f.fieldname] = field.grid.get_data();
                        }
                    }
                });
                
                selectedNode.value.data.method_config = JSON.stringify(values);
                store.mark_dirty();
                frappe.show_alert({ message: __('Configuration saved'), indicator: 'green' });
            }
            dialog.hide();
        }
    });
    
    dialog.show();
    
    // For Table fields, refresh grid with data after dialog is shown
    setTimeout(() => {
        dialogFields.forEach(f => {
            if (f.fieldtype === 'Table' && currentConfig[f.fieldname]) {
                const field = dialog.fields_dict[f.fieldname];
                if (field && field.grid) {
                    // Clear and set data
                    field.grid.df.data = currentConfig[f.fieldname];
                    field.grid.refresh();
                }
            }
        });
        
        // Set non-table values
        const nonTableConfig = {};
        Object.keys(currentConfig).forEach(key => {
            const field = dialogFields.find(f => f.fieldname === key);
            if (field && field.fieldtype !== 'Table') {
                nonTableConfig[key] = currentConfig[key];
            }
        });
        if (Object.keys(nonTableConfig).length > 0) {
            dialog.set_values(nonTableConfig);
        }
    }, 150);
}

async function buildDialogFields(schemaFields, parentDoctype, childTables = {}) {
    const fields = [];
    
    for (const field of schemaFields) {
        const mapped = await mapSchemaField(field, parentDoctype, childTables);
        if (mapped) {
            // Handle array of fields (e.g., Table expands to label + table)
            if (Array.isArray(mapped)) {
                fields.push(...mapped);
            } else {
                fields.push(mapped);
            }
        }
    }
    
    return fields;
}

async function mapSchemaField(field, parentDoctype, childTables) {
    const { fieldname, fieldtype, label, reqd, options, description } = field;
    const defaultVal = field.default;
    
    switch (fieldtype) {
        case 'DocField':
            // Single field picker → Autocomplete
            return {
                fieldname,
                fieldtype: 'Autocomplete',
                label,
                reqd,
                description,
                options: await getFieldOptions(options, parentDoctype)
            };
        
        case 'MultiDocField':
            // Multi field picker → MultiCheck with checkboxes
            const multiOptions = await getFieldOptions(options, parentDoctype);
            return {
                fieldname,
                fieldtype: 'MultiCheck',
                label,
                reqd,
                description,
                options: multiOptions,
                columns: 2,
                select_all: true
            };
        
        case 'Table':
            // Inline table → Table control with child fields
            const childSchema = childTables[options] || [];
            if (!childSchema.length) {
                console.warn(`No child_tables definition for: ${options}`);
                return null;
            }
            
            // Map child fields recursively
            const childFields = [];
            for (const cf of childSchema) {
                const mappedChild = await mapSchemaField(cf, parentDoctype, {});
                if (mappedChild && !Array.isArray(mappedChild)) {
                    // For table child fields, convert Autocomplete to Data with options
                    if (mappedChild.fieldtype === 'Autocomplete') {
                        mappedChild.fieldtype = 'Select';
                        mappedChild.options = mappedChild.options?.map(o => o.value || o).join('\n') || '';
                    }
                    if (mappedChild.fieldtype === 'MultiCheck') {
                        mappedChild.fieldtype = 'Select';
                        mappedChild.options = mappedChild.options?.map(o => o.value || o).join('\n') || '';
                    }
                    mappedChild.in_list_view = 1;
                    childFields.push(mappedChild);
                }
            }
            
            return {
                fieldname,
                fieldtype: 'Table',
                label,
                reqd,
                description,
                fields: childFields,
                data: [],
                cannot_add_rows: false,
                in_place_edit: false
            };
        
        case 'MultiSelect':
            // Multi-select → MultiCheck
            const selectOpts = parseSelectOptions(options);
            return {
                fieldname,
                fieldtype: 'MultiCheck',
                label,
                reqd,
                description,
                options: selectOpts,
                columns: 2
            };
        
        case 'Percent':
            // Percent → Float with description
            return {
                fieldname,
                fieldtype: 'Float',
                label,
                reqd,
                description: description || 'Value from 0-100',
                default: defaultVal
            };
        
        default:
            // Standard Frappe fieldtype - pass through
            return {
                fieldname,
                fieldtype,
                label,
                reqd,
                options,
                description,
                default: defaultVal
            };
    }
}

async function getFieldOptions(optionsRef, parentDoctype) {
    let targetDoctype = parentDoctype;
    
    if (optionsRef === 'parent.document_type') {
        targetDoctype = parentDoctype;
    } else if (optionsRef && !optionsRef.includes('.')) {
        targetDoctype = optionsRef;
    }
    
    if (!targetDoctype) return [];
    
    try {
        const result = await frappe.call({
            method: 'flexirule.ruleflow.api.get_doctype_fields',
            args: { doctype: targetDoctype }
        });
        
        if (result.message?.parent_fields) {
            const opts = result.message.parent_fields.map(f => ({
                value: f.value,
                label: `${f.label} (${f.fieldtype})`
            }));
            
            // Add child table fields
            if (result.message.child_tables) {
                result.message.child_tables.forEach(table => {
                    opts.push({ value: '', label: `── ${table.table_label} ──`, disabled: true });
                    table.fields.forEach(f => {
                        opts.push({ value: f.value, label: `  ${f.label}` });
                    });
                });
            }
            
            return opts;
        }
    } catch (e) {
        console.error('Failed to fetch field options:', e);
    }
    
    return [];
}

function parseSelectOptions(options) {
    if (!options) return [];
    return options.split('\n').filter(Boolean).map(opt => ({
        value: opt.trim(),
        label: opt.trim()
    }));
}

</script>

<style scoped>
.rule-sidebar {
    width: 280px;
    height: 100%;
    display: flex;
    flex-direction: column;
}

.sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 15px;
    border-bottom: 1px solid var(--border-color);
}

.sidebar-header h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
}

.btn-close {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: var(--text-muted);
    padding: 0;
}

.sidebar-content {
    flex: 1;
    padding: 15px;
    overflow-y: auto;
}

.form-group {
    margin-bottom: 12px;
}

.form-group label {
    display: block;
    font-size: 11px;
    font-weight: 500;
    margin-bottom: 4px;
    color: var(--text-muted);
    text-transform: uppercase;
}

.form-control {
    width: 100%;
    padding: 6px 10px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 13px;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
}

hr {
    margin: 15px 0;
    border: none;
    border-top: 1px solid var(--border-color);
}

.w-100 { width: 100%; }
.mt-3 { margin-top: 15px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }

.suggestions-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.suggestion-item {
    padding: 8px 10px;
    cursor: pointer;
    border-bottom: 1px solid var(--border-color-muted);
}
.suggestion-item:hover {
    background-color: var(--bg-light-gray);
}
.suggestion-name {
    font-weight: 500;
    font-size: 13px;
}
.suggestion-path {
    font-size: 11px;
    color: var(--text-muted);
}
.input-group {
    display: flex;
    gap: 5px;
}
.relative { position: relative; }
</style>
