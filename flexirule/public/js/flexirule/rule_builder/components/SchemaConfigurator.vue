<script setup>
import { ref, computed, watch } from "vue";

const props = defineProps({
	schema: Object,
	modelValue: [Object, String],
});

const emit = defineEmits(["update:modelValue"]);

const localValue = ref(props.modelValue || {});

watch(
	() => props.modelValue,
	(newVal) => {
		if (newVal !== localValue.value) {
			localValue.value = newVal || {};
		}
	}
);

watch(
	localValue,
	(newVal) => {
		emit("update:modelValue", newVal);
	},
	{ deep: true }
);

function updateField(fieldName, value) {
	localValue.value[fieldName] = value;
}

function getFieldType(property) {
	if (property.enum) return "select";
	if (property.type === "boolean") return "checkbox";
	if (property.type === "number" || property.type === "integer") return "number";
	if (property.type === "string") return "text";
	if (property.type === "array") return "array";
	if (property.type === "object") return "object";
	return "text";
}

function isRequired(fieldName) {
	return props.schema?.required?.includes(fieldName) || false;
}

const properties = computed(() => {
	return props.schema?.properties || {};
});
</script>

<template>
	<div class="schema-configurator">
		<div v-if="!schema || !schema.properties" class="empty-state text-muted">
			{{ __("No configuration schema available") }}
		</div>
		<div v-else class="config-fields">
			<div v-for="(property, fieldName) in properties" :key="fieldName" class="form-group">
				<label :class="{ required: isRequired(fieldName) }">
					{{ property.title || fieldName }}
				</label>
				<small v-if="property.description" class="form-text text-muted d-block mb-1">
					{{ property.description }}
				</small>

				<!-- Select for enum -->
				<select
					v-if="property.enum"
					class="form-control"
					:value="localValue[fieldName]"
					@input="updateField(fieldName, $event.target.value)"
					:required="isRequired(fieldName)"
				>
					<option value="">{{ __("Select...") }}</option>
					<option v-for="option in property.enum" :key="option" :value="option">
						{{ option }}
					</option>
				</select>

				<!-- Checkbox for boolean -->
				<div v-else-if="property.type === 'boolean'" class="checkbox">
					<label>
						<input
							type="checkbox"
							:checked="localValue[fieldName]"
							@change="updateField(fieldName, $event.target.checked)"
						/>
						{{ property.title || fieldName }}
					</label>
				</div>

				<!-- Number input -->
				<input
					v-else-if="property.type === 'number' || property.type === 'integer'"
					type="number"
					class="form-control"
					:value="localValue[fieldName]"
					@input="updateField(fieldName, parseFloat($event.target.value))"
					:required="isRequired(fieldName)"
					:min="property.minimum"
					:max="property.maximum"
				/>

				<!-- Text input -->
				<input
					v-else-if="property.type === 'string'"
					type="text"
					class="form-control"
					:value="localValue[fieldName]"
					@input="updateField(fieldName, $event.target.value)"
					:required="isRequired(fieldName)"
					:pattern="property.pattern"
				/>

				<!-- Textarea for long text -->
				<textarea
					v-else-if="property.maxLength && property.maxLength > 100"
					class="form-control"
					:value="localValue[fieldName]"
					@input="updateField(fieldName, $event.target.value)"
					:required="isRequired(fieldName)"
					rows="3"
				></textarea>

				<!-- Default text input -->
				<input
					v-else
					type="text"
					class="form-control"
					:value="localValue[fieldName]"
					@input="updateField(fieldName, $event.target.value)"
					:required="isRequired(fieldName)"
				/>
			</div>
		</div>
	</div>
</template>

<style scoped>
.schema-configurator {
	padding: 10px 0;
}

.config-fields .form-group {
	margin-bottom: 15px;
}

.config-fields label.required::after {
	content: " *";
	color: var(--red);
}

.empty-state {
	padding: 20px;
	text-align: center;
}
</style>
