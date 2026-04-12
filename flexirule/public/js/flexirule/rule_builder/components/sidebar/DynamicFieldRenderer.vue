<template>
	<div class="dynamic-field-renderer">
		<!-- Loading state -->
		<div v-if="loading" class="dfr-loading">
			<i class="fa fa-spinner fa-spin"></i>
			{{ __("Loading configuration...") }}
		</div>

		<!-- Error state -->
		<div v-else-if="error" class="dfr-error">
			<i class="fa fa-exclamation-triangle"></i>
			{{ error }}
		</div>

		<!-- Sections -->
		<template v-else>
			<div v-for="section in visibleSections" :key="section.key" class="dfr-section">
				<div class="dfr-section-header" @click="toggleSection(section.key)">
					<span class="dfr-section-title">
						<i
							class="fa"
							:class="
								expandedSections[section.key]
									? 'fa-chevron-down'
									: 'fa-chevron-right'
							"
						></i>
						{{ section.label }}
					</span>
					<span v-if="section.description" class="dfr-section-desc text-muted">
						{{ section.description }}
					</span>
				</div>

				<div v-show="expandedSections[section.key]" class="dfr-section-body">
					<div
						v-for="fieldname in section.fields"
						:key="fieldname"
						class="dfr-field"
						:class="{ 'dfr-field--required': isRequired(fieldname) }"
					>
						<label class="dfr-field-label">
							{{ getFieldLabel(fieldname) }}
							<span v-if="isRequired(fieldname)" class="text-danger">*</span>
						</label>

						<!-- Select field -->
						<select
							v-if="getFieldType(fieldname) === 'Select'"
							class="form-control form-control-sm"
							:value="modelValue[fieldname]"
							:disabled="readOnly"
							@change="emitUpdate(fieldname, $event.target.value)"
						>
							<option value="">{{ __("Select...") }}</option>
							<option
								v-for="opt in getFieldOptions(fieldname)"
								:key="opt"
								:value="opt"
							>
								{{ opt }}
							</option>
						</select>

						<!-- Link field -->
						<div v-else-if="getFieldType(fieldname) === 'Link'" class="dfr-link-field">
							<input
								type="text"
								class="form-control form-control-sm"
								:value="modelValue[fieldname]"
								:disabled="readOnly"
								:placeholder="getFieldOptions(fieldname)?.[0] || ''"
								@change="emitUpdate(fieldname, $event.target.value)"
							/>
						</div>

						<!-- Check (boolean) field -->
						<div
							v-else-if="getFieldType(fieldname) === 'Check'"
							class="dfr-check-field"
						>
							<input
								type="checkbox"
								:checked="modelValue[fieldname]"
								:disabled="readOnly"
								@change="emitUpdate(fieldname, $event.target.checked ? 1 : 0)"
							/>
							<span class="dfr-check-label">{{ getFieldLabel(fieldname) }}</span>
						</div>

						<!-- Int field -->
						<input
							v-else-if="getFieldType(fieldname) === 'Int'"
							type="number"
							class="form-control form-control-sm"
							:value="modelValue[fieldname]"
							:disabled="readOnly"
							@change="emitUpdate(fieldname, parseInt($event.target.value) || 0)"
						/>

						<!-- Code / JSON field -->
						<textarea
							v-else-if="
								['Code', 'JSON', 'Text', 'Small Text'].includes(
									getFieldType(fieldname)
								)
							"
							class="form-control form-control-sm dfr-textarea"
							:value="modelValue[fieldname]"
							:disabled="readOnly"
							rows="3"
							@change="emitUpdate(fieldname, $event.target.value)"
						></textarea>

						<!-- Default: Data field -->
						<input
							v-else
							type="text"
							class="form-control form-control-sm"
							:value="modelValue[fieldname]"
							:disabled="readOnly"
							@change="emitUpdate(fieldname, $event.target.value)"
						/>

						<!-- Field description -->
						<small
							v-if="getFieldDescription(fieldname)"
							class="dfr-field-desc text-muted"
						>
							{{ getFieldDescription(fieldname) }}
						</small>
					</div>
				</div>
			</div>

			<!-- Validation errors -->
			<div v-if="validationErrors.length" class="dfr-errors mt-3">
				<div v-for="(err, idx) in validationErrors" :key="idx" class="dfr-error-item">
					<i class="fa fa-times-circle text-danger"></i>
					{{ err }}
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";

const props = defineProps({
	/** Action type for schema lookup */
	actionType: { type: String, required: true },
	/** Optional operation name */
	operation: { type: String, default: null },
	/** Optional process name */
	processName: { type: String, default: null },
	/** Current field values (v-model binding) */
	modelValue: { type: Object, default: () => ({}) },
	/** Whether fields are read-only */
	readOnly: { type: Boolean, default: false },
	/** Pre-loaded schema (skip API call) */
	schema: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue", "update:field", "validate"]);

// ── State ──
const loading = ref(false);
const error = ref(null);
const schemaData = ref(null);
const validationErrors = ref([]);

// Track which sections are expanded
const expandedSections = ref({
	identity: true,
	configuration: true,
	flow: false,
	data: false,
	advanced: false,
});

// ── Schema loading ──
async function loadSchema() {
	// Use pre-loaded schema if provided
	if (props.schema) {
		schemaData.value = props.schema;
		return;
	}

	if (!props.actionType) return;

	loading.value = true;
	error.value = null;

	try {
		const result = await frappe.call({
			method: "flexirule.ruleflow.api.get_node_config_schema",
			args: {
				action_type: props.actionType,
				operation: props.operation,
				process_name: props.processName,
			},
		});
		schemaData.value = result.message;
	} catch (e) {
		console.error("DynamicFieldRenderer: Schema load failed", e);
		error.value = e.message || __("Failed to load configuration schema");
	} finally {
		loading.value = false;
	}
}

// ── Field helpers ──
const fieldsMap = computed(() => {
	if (!schemaData.value?.fields) return {};
	const map = {};
	for (const f of schemaData.value.fields) {
		map[f.fieldname] = f;
	}
	return map;
});

const visibleSections = computed(() => {
	if (!schemaData.value?.sections) return [];
	return schemaData.value.sections.filter((s) => s.fields.length > 0);
});

function getFieldDef(fieldname) {
	return fieldsMap.value[fieldname] || {};
}

function getFieldLabel(fieldname) {
	return getFieldDef(fieldname).label || fieldname;
}

function getFieldType(fieldname) {
	return getFieldDef(fieldname).fieldtype || "Data";
}

function getFieldOptions(fieldname) {
	const opts = getFieldDef(fieldname).options;
	if (!opts) return [];
	if (Array.isArray(opts)) return opts;
	return opts.split("\n").filter(Boolean);
}

function getFieldDescription(fieldname) {
	return getFieldDef(fieldname).description || "";
}

function isRequired(fieldname) {
	return !!getFieldDef(fieldname).reqd;
}

function isHidden(fieldname) {
	const df = getFieldDef(fieldname);
	if (df.hidden) return true;

	// Evaluate depends_on if present
	if (df.depends_on) {
		return !_evalDependsOn(df.depends_on, props.modelValue);
	}
	return false;
}

// ── Section toggle ──
function toggleSection(key) {
	expandedSections.value[key] = !expandedSections.value[key];
}

// ── Field updates ──
function emitUpdate(fieldname, value) {
	emit("update:field", fieldname, value);

	// Also emit full model update
	const updated = { ...props.modelValue, [fieldname]: value };
	emit("update:modelValue", updated);
}

// ── Depends-on evaluation (simplified) ──
function _evalDependsOn(expr, doc) {
	if (!expr) return true;
	if (typeof expr === "boolean") return expr;

	if (expr.startsWith("eval:")) {
		try {
			return frappe.utils.eval(expr.substr(5), { doc });
		} catch {
			return true;
		}
	}

	// Simple fieldname check
	return !!doc[expr];
}

// ── Lifecycle ──
onMounted(() => {
	loadSchema();
});

// Reload schema when action type or operation changes
watch(
	() => [props.actionType, props.operation, props.processName],
	() => {
		loadSchema();
	}
);
</script>

<style scoped>
.dynamic-field-renderer {
	font-size: 12px;
}

.dfr-loading,
.dfr-error {
	padding: 20px;
	text-align: center;
	color: var(--text-muted);
}

.dfr-error {
	color: var(--red-500, #ef4444);
}

.dfr-section {
	border: 1px solid var(--border-color);
	border-radius: 6px;
	margin-bottom: 8px;
	overflow: hidden;
}

.dfr-section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 12px;
	background: var(--bg-light, #f8fafc);
	cursor: pointer;
	user-select: none;
}

.dfr-section-header:hover {
	background: var(--bg-color, #f1f5f9);
}

.dfr-section-title {
	font-weight: 600;
	font-size: 11px;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--text-color);
}

.dfr-section-title .fa {
	margin-right: 6px;
	font-size: 10px;
	width: 12px;
	text-align: center;
}

.dfr-section-desc {
	font-size: 10px;
	font-weight: 400;
}

.dfr-section-body {
	padding: 8px 12px 12px;
}

.dfr-field {
	margin-bottom: 10px;
}

.dfr-field:last-child {
	margin-bottom: 0;
}

.dfr-field-label {
	display: block;
	font-size: 11px;
	font-weight: 500;
	margin-bottom: 4px;
	color: var(--text-light);
}

.dfr-field--required .dfr-field-label {
	font-weight: 600;
}

.dfr-field-desc {
	display: block;
	margin-top: 2px;
	font-size: 10px;
	line-height: 1.3;
}

.dfr-textarea {
	font-family: monospace;
	font-size: 11px;
	resize: vertical;
	min-height: 60px;
}

.dfr-check-field {
	display: flex;
	align-items: center;
	gap: 6px;
}

.dfr-check-label {
	font-size: 12px;
}

.dfr-errors {
	padding: 8px;
	background: #fef2f2;
	border: 1px solid #fecaca;
	border-radius: 6px;
}

.dfr-error-item {
	font-size: 11px;
	padding: 2px 0;
	color: #991b1b;
}

.dfr-error-item .fa {
	margin-right: 4px;
}

.form-control-sm {
	font-size: 12px;
	padding: 4px 8px;
	height: auto;
	border-radius: 4px;
}
</style>
