<script setup>
/**
 * InlineTableControl - Repeatable rows with columns
 * For complex mappings like field_config arrays
 */
import { ref, computed, watch } from "vue";

const props = defineProps({
    df: Object,
    modelValue: [Array, String],
    documentType: String,
    read_only: Boolean
});

const emit = defineEmits(["update:modelValue"]);

const rows = computed({
    get() {
        if (Array.isArray(props.modelValue)) return props.modelValue;
        if (typeof props.modelValue === 'string' && props.modelValue) {
            try {
                return JSON.parse(props.modelValue);
            } catch {
                return [];
            }
        }
        return [];
    },
    set(val) {
        emit("update:modelValue", val);
    }
});

const tableFields = computed(() => {
    return props.df?.table_fields || [];
});

function addRow() {
    const newRow = {};
    tableFields.value.forEach(f => {
        newRow[f.fieldname] = f.default || '';
    });
    emit("update:modelValue", [...rows.value, newRow]);
}

function removeRow(idx) {
    const updated = [...rows.value];
    updated.splice(idx, 1);
    emit("update:modelValue", updated);
}

function updateCell(rowIdx, fieldname, value) {
    const updated = [...rows.value];
    updated[rowIdx] = { ...updated[rowIdx], [fieldname]: value };
    emit("update:modelValue", updated);
}
</script>

<template>
    <div class="inline-table-control">
        <label v-if="df.label" class="control-label">
            {{ __(df.label) }}
            <span v-if="df.reqd" class="text-danger">*</span>
        </label>
        
        <div class="table-wrapper">
            <table class="table table-sm table-bordered">
                <thead>
                    <tr>
                        <th v-for="col in tableFields" :key="col.fieldname">
                            {{ __(col.label) }}
                        </th>
                        <th v-if="!read_only" style="width:40px"></th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, idx) in rows" :key="idx">
                        <td v-for="col in tableFields" :key="col.fieldname">
                            <input
                                type="text"
                                class="form-control form-control-sm"
                                :value="row[col.fieldname]"
                                @input="updateCell(idx, col.fieldname, $event.target.value)"
                                :disabled="read_only"
                            />
                        </td>
                        <td v-if="!read_only">
                            <button
                                type="button"
                                class="btn btn-xs btn-danger"
                                @click="removeRow(idx)"
                            >×</button>
                        </td>
                    </tr>
                    <tr v-if="!rows.length">
                        <td :colspan="tableFields.length + 1" class="text-muted text-center">
                            {{ __("No rows. Click Add to create one.") }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <button
            v-if="!read_only"
            type="button"
            class="btn btn-xs btn-default"
            @click="addRow"
        >
            + {{ __("Add Row") }}
        </button>
        
        <small v-if="df.description" class="form-text text-muted">{{ df.description }}</small>
    </div>
</template>

<style scoped>
.inline-table-control { margin-bottom: 15px; }
.control-label { font-size: 12px; font-weight: 500; margin-bottom: 5px; display: block; }
.table-wrapper { margin-bottom: 8px; }
.table { margin-bottom: 0; }
.table th { font-size: 11px; font-weight: 500; }
.table td { padding: 4px; }
.table input { font-size: 12px; }
</style>
