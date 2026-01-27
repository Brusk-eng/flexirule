<script setup>
/**
 * FieldPickerControl - DocField autocomplete picker
 * Shows fields from the target doctype with search
 * Supports pre-fetched fields from store via 'fields' prop
 */

const props = defineProps({
	df: Object,
	modelValue: String,
	documentType: String, // Optional: fallback for API fetch
	fields: { type: Array, default: null }, // NEW: Pre-fetched fields from store
	read_only: Boolean,
});

const emit = defineEmits(["update:modelValue"]);

const searchQuery = ref("");
const showDropdown = ref(false);
const apiFields = ref([]); // Fields fetched from API (fallback)
const loading = ref(false);

const content = computed({
	get: () => props.modelValue || "",
	set: (val) => emit("update:modelValue", val),
});

// Use props.fields if provided, otherwise use apiFields from API
const effectiveFields = computed(() => {
	if (props.fields && props.fields.length > 0) {
		return props.fields;
	}
	return apiFields.value;
});

const filteredFields = computed(() => {
	if (!searchQuery.value) return effectiveFields.value;
	const query = searchQuery.value.toLowerCase();
	return effectiveFields.value.filter(
		(f) =>
			(f.value && f.value.toLowerCase().includes(query)) ||
			(f.label && f.label.toLowerCase().includes(query))
	);
});

const displayValue = computed(() => {
	const field = effectiveFields.value.find((f) => f.value === content.value);
	return field ? `${field.label}` : content.value;
});

async function loadFields() {
	// Skip API call if fields prop is provided
	if (props.fields && props.fields.length > 0) return;

	if (!props.documentType) {
		apiFields.value = [];
		return;
	}
	loading.value = true;
	try {
		apiFields.value = await flexirule.utils.get_doctype_fields(props.documentType);
	} catch (e) {
		apiFields.value = [];
	} finally {
		loading.value = false;
	}
}

function selectField(field) {
	content.value = field.value;
	showDropdown.value = false;
	searchQuery.value = "";
}

function handleInput(e) {
	searchQuery.value = e.target.value;
	content.value = e.target.value;
	showDropdown.value = true;
}

function handleFocus() {
	showDropdown.value = true;
	if (!effectiveFields.value.length && props.documentType) loadFields();
}

function handleBlur() {
	setTimeout(() => {
		showDropdown.value = false;
	}, 200);
}

// Only trigger API load if we don't have pre-fetched fields
watch(
	() => props.documentType,
	() => {
		if (!props.fields || props.fields.length === 0) {
			loadFields();
		}
	},
	{ immediate: true }
);
</script>

<template>
	<div class="field-picker-control">
		<label v-if="df.label" class="control-label">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</label>

		<div class="field-input-wrapper">
			<input
				type="text"
				class="form-control form-control-sm"
				:value="showDropdown ? searchQuery : displayValue"
				@input="handleInput"
				@focus="handleFocus"
				@blur="handleBlur"
				:placeholder="__('Search fields...')"
				:disabled="read_only"
			/>
			<div v-if="loading" class="field-loading">
				<span class="spinner-border spinner-border-sm"></span>
			</div>
			<div v-if="showDropdown && filteredFields.length" class="field-dropdown">
				<div
					v-for="field in filteredFields"
					:key="field.value"
					class="field-option"
					:class="{ selected: field.value === content }"
					@mousedown.prevent="selectField(field)"
				>
					<span class="field-name">{{ field.value }}</span>
					<span class="field-label">{{ __(field.label) }}</span>
					<span class="field-type badge badge-secondary">{{ field.fieldtype }}</span>
				</div>
			</div>
			<div v-if="showDropdown && !filteredFields.length && !loading" class="field-dropdown">
				<div class="field-option disabled">{{ __("No fields found") }}</div>
			</div>
		</div>

		<small v-if="df.description" class="form-text text-muted">{{ df.description }}</small>
	</div>
</template>

<style scoped>
.field-picker-control {
	margin-bottom: 15px;
}
.control-label {
	font-size: 12px;
	font-weight: 500;
	margin-bottom: 5px;
	display: block;
}
.field-input-wrapper {
	position: relative;
}
.field-loading {
	position: absolute;
	right: 10px;
	top: 50%;
	transform: translateY(-50%);
}
.field-dropdown {
	position: absolute;
	top: 100%;
	left: 0;
	right: 0;
	background: white;
	border: 1px solid var(--border-color);
	border-radius: 4px;
	max-height: 250px;
	overflow-y: auto;
	z-index: 100;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.field-option {
	padding: 8px 12px;
	cursor: pointer;
	display: flex;
	align-items: center;
	gap: 8px;
	border-bottom: 1px solid var(--border-color);
}
.field-option:last-child {
	border-bottom: none;
}
.field-option:hover {
	background: var(--bg-light-gray, #f5f5f5);
}
.field-option.selected {
	background: var(--bg-light-blue, #e3f2fd);
}
.field-option.disabled {
	color: var(--text-muted);
	cursor: default;
}
.field-name {
	font-family: monospace;
	font-size: 12px;
	color: var(--primary);
}
.field-label {
	flex: 1;
	font-size: 12px;
	color: var(--text-muted);
}
.field-type {
	font-size: 10px;
	padding: 2px 6px;
}
</style>
