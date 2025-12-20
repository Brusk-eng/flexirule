<template>
  <div class="collection-row border rounded p-4 mb-4 bg-white shadow-sm">
      <div class="collection-header grid gap-4 mb-3">
          
          <!-- Operator -->
           <div class="logic-col">
               <label class="condition-label">{{ __("Logic") }}</label>
               <select v-model="modelValue.op" class="form-control input-sm">
                  <option value="any">{{ __("Any") }}</option>
                  <option value="all">{{ __("All") }}</option>
                  <option value="none">{{ __("None") }}</option>
              </select>
           </div>
          
           <!-- Collection -->
           <div class="table-col">
               <label class="condition-label">{{ __("Table") }}</label>
               <input 
                 :list="'collection-list-' + modelValue.id"
                v-model="modelValue.collection" 
                class="form-control input-sm font-weight-bold"
                :placeholder="__('e.g. doc.items')"
                @input="fetchChildMeta"
              />
              <datalist :id="'collection-list-' + modelValue.id">
                  <option v-for="field in tableFields" :key="field.value" :value="field.value">{{ field.label }}</option>
              </datalist>
          </div>

          <!-- Alias -->
          <div class="alias-col">
              <label class="condition-label">{{ __("Alias") }}</label>
              <input 
                type="text" 
                v-model="modelValue.alias" 
                class="form-control input-sm"
                placeholder="row"
                title="Loop Alias"
                @input="fetchChildMeta"
              />
              <div class="field-type-hint">{{ __("Iterator Alias") }}</div>
          </div>
         
         <div class="remove-col">
             <button class="btn btn-xs btn-link text-danger remove-btn p-0" @click="$emit('remove')" :title="__('Remove Collection')">
                 <i class="fa fa-trash-o fa-lg"></i>
             </button>
         </div>
     </div>
     
     <!-- Nested Group with Child Fields -->
     <div class="pl-4 group-content">
         <ConditionGroup
           v-if="modelValue.where"
           :modelValue="modelValue.where"
           :isRoot="false"
           :docFields="childDocFields"
           @add-condition="addCondition"
           @add-group="addGroup"
           @add-collection="addCollection"
         />
     </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue';
import ConditionGroup from './ConditionGroup.vue';

export default {
    name: "CollectionRow",
    components: {
        ConditionGroup
    },
    props: {
        modelValue: Object,
        docFields: Array
    },
    emits: ["update:modelValue", "remove"],
    setup(props) {
        const childDocFields = ref([]);
        
        const tableFields = computed(() => {
            return (props.docFields || []).filter(f => f.fieldtype === 'Table');
        });

        // Simple ID gen
        function get_uuid() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        const fetchChildMeta = () => {
            let collectionName = props.modelValue.collection;
            if (!collectionName) {
                childDocFields.value = (props.docFields || []).filter(f => f.value.startsWith('doc.'));
                return;
            }

            // Default alias to table name if empty
            if (!props.modelValue.alias) {
                let defaultAlias = collectionName.split('.').pop();
                props.modelValue.alias = defaultAlias.replace(/[^a-zA-Z0-0_]/g, '_');
            }

            // Sanitize alias: no dots or spaces allowed
            if (props.modelValue.alias) {
                const sanitized = props.modelValue.alias.replace(/[^a-zA-Z0-9_]/g, '_');
                if (sanitized !== props.modelValue.alias) {
                    props.modelValue.alias = sanitized;
                }
            }
            
            const fieldMeta = props.docFields.find(f => f.value === collectionName || f.value === 'doc.' + collectionName);
            
            if (fieldMeta && fieldMeta.fieldtype === 'Table' && fieldMeta.options) {
                const childDoctype = fieldMeta.options;
                const alias = props.modelValue.alias || 'row';
                
                frappe.model.with_doctype(childDoctype, () => {
                   try {
                        const meta = frappe.get_meta(childDoctype);
                        if (meta && meta.fields) {
                            const excludedTypes = ['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button', 'Image', 'Fold', 'Heading', 'Spacer'];
                            const fields = [];
                            
                            // 1. Add Parent Fields (doc.*)
                            (props.docFields || []).forEach(f => {
                                if (f.value.startsWith('doc.')) {
                                    fields.push(f);
                                }
                            });

                            // 2. Add Child Table Fields (row.*)
                            meta.fields.forEach(f => {
                                if (!excludedTypes.includes(f.fieldtype)) {
                                    fields.push({
                                        label: `${f.label} (${f.fieldname})`,
                                        value: alias + '.' + f.fieldname, 
                                        fieldtype: f.fieldtype,
                                        options: f.options,
                                        is_row: true
                                    });
                                }
                            });
                            
                            fields.sort((a, b) => {
                                if (a.is_row && !b.is_row) return -1;
                                if (!a.is_row && b.is_row) return 1;
                                return a.label.localeCompare(b.label);
                            });
                            childDocFields.value = fields;
                        }
                   } catch (e) { console.error(e); }
                });
            } else {
                childDocFields.value = (props.docFields || []).filter(f => f.value.startsWith('doc.'));
            }
        };

        // Recursively update condition prefixes when alias changes
        const syncAliasInConditions = (conditions, oldAlias, newAlias) => {
            if (!conditions) return;
            const oldPrefix = oldAlias + '.';
            const newPrefix = newAlias + '.';
            
            conditions.forEach(node => {
                if (node.left?.ref && node.left.ref.startsWith(oldPrefix)) {
                    node.left.ref = node.left.ref.replace(oldPrefix, newPrefix);
                }
                if (node.conditions) syncAliasInConditions(node.conditions, oldAlias, newAlias);
                if (node.where) syncAliasInConditions([node.where], oldAlias, newAlias);
            });
        };

        watch(() => props.modelValue.alias, (newAlias, oldAlias) => {
            if (oldAlias && newAlias && oldAlias !== newAlias) {
                syncAliasInConditions(props.modelValue.where?.conditions, oldAlias, newAlias);
            }
            fetchChildMeta();
        });

        watch(() => props.modelValue.collection, fetchChildMeta);
        watch(() => props.docFields, fetchChildMeta, { deep: true });
        
        onMounted(fetchChildMeta);

        const addCondition = (group) => {
            if (!group.conditions) group.conditions = [];
            let alias = props.modelValue.alias || 'row';
            group.conditions.push({
                id: get_uuid(),
                left: { ref: alias + "." },
                op: "==",
                right: { value: "" }
            });
        };

        const addGroup = (group) => {
             if (!group.conditions) group.conditions = [];
             group.conditions.push({
                id: get_uuid(),
                op: "and",
                conditions: []
            });
        }

        const addCollection = (group) => {
            if (!group.conditions) group.conditions = [];
            group.conditions.push({
                id: get_uuid(),
                op: "any",
                collection: "",
                alias: "row",
                where: {
                    op: "and",
                    conditions: []
                }
            });
        }

        return {
            tableFields,
            childDocFields,
            fetchChildMeta,
            addCondition,
            addGroup,
            addCollection
        }
    }
}
</script>

<style scoped>
.collection-row {
    border-color: var(--border-color);
    border-left: 4px solid var(--blue-500); /* Highlight collection nodes */
}

.collection-header {
    display: grid;
    grid-template-columns: 120px 1fr 140px 32px;
    align-items: start;
}

@media (max-width: 600px) {
    .collection-header {
        grid-template-columns: 1fr;
        gap: 12px;
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
}

.group-content {
    border-left: 2px solid var(--gray-200);
    padding: 12px;
    background: #fdfdfd;
    border-radius: 4px;
    margin-top: 8px;
}

.remove-col {
    align-self: center;
    padding-top: 16px;
}

.remove-btn {
    opacity: 0.6;
    transition: opacity 0.2s;
}
.remove-btn:hover {
    opacity: 1;
}
</style>
