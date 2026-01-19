<template>
	<div class="control-factory">
		<!-- Link -->
		<LinkControl
			v-if="df?.fieldtype === 'Link'"
			:df="df"
			:modelValue="modelValue"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Autocomplete -->
		<AutocompleteControl
			v-else-if="df?.fieldtype === 'Autocomplete'"
			:df="df"
			:modelValue="modelValue"
			:options="df?.autocomplete_options"
			:get_options="df?.get_options"
			:doc="doc"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Select -->
		<SelectControl
			v-else-if="df?.fieldtype === 'Select'"
			:df="df"
			:modelValue="modelValue"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Check -->
		<CheckControl
			v-else-if="df?.fieldtype === 'Check'"
			:df="df"
			:modelValue="Boolean(modelValue)"
			:hideLabel="hideLabel"
			@update:modelValue="$emit('update:modelValue', $event ? 1 : 0)"
		/>

		<!-- Number (Int, Float, Currency, Percent) -->
		<div
			v-else-if="['Int', 'Float', 'Currency', 'Percent'].includes(df?.fieldtype)"
			class="control frappe-control"
		>
			<div v-if="df.label && !hideLabel" class="control-label label" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</div>
			<input
				type="number"
				step="any"
				class="form-control input-sm"
				:value="modelValue"
				:disabled="df.read_only"
				@input="
					$emit(
						'update:modelValue',
						df.fieldtype === 'Int'
							? parseInt($event.target.value)
							: parseFloat($event.target.value)
					)
				"
			/>
			<div
				v-if="df.description"
				class="description text-muted mt-1"
				v-html="__(df.description)"
			></div>
		</div>

		<!-- Date / Datetime -->
		<div
			v-else-if="['Date', 'Datetime'].includes(df?.fieldtype)"
			class="control frappe-control"
		>
			<div v-if="df.label && !hideLabel" class="control-label label" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</div>
			<input
				:type="df.fieldtype === 'Date' ? 'date' : 'datetime-local'"
				class="form-control input-sm"
				:value="modelValue"
				:disabled="df.read_only"
				@input="$emit('update:modelValue', $event.target.value)"
			/>
			<div
				v-if="df.description"
				class="description text-muted mt-1"
				v-html="__(df.description)"
			></div>
		</div>

		<!-- Time -->
		<div v-else-if="df?.fieldtype === 'Time'" class="control frappe-control">
			<div v-if="df.label && !hideLabel" class="control-label label" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</div>
			<input
				type="time"
				step="1"
				class="form-control input-sm"
				:value="modelValue"
				:disabled="df.read_only"
				@input="$emit('update:modelValue', $event.target.value)"
			/>
			<div
				v-if="df.description"
				class="description text-muted mt-1"
				v-html="__(df.description)"
			></div>
		</div>

		<!-- Text / Code / multiline -->
		<div
			v-else-if="
				[
					'Text',
					'Small Text',
					'Text Editor',
					'Code',
					'JSON',
					'HTML Editor',
					'Markdown Editor',
				].includes(df?.fieldtype)
			"
			class="control frappe-control"
		>
			<div v-if="df.label && !hideLabel" class="control-label label" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</div>
			<textarea
				class="form-control"
				rows="3"
				:value="modelValue"
				:disabled="df.read_only"
				@input="$emit('update:modelValue', $event.target.value)"
			></textarea>
			<div
				v-if="df.description"
				class="description text-muted mt-1"
				v-html="__(df.description)"
			></div>
		</div>

		<!-- Table -->
		<FlexiGrid
			v-else-if="df?.fieldtype === 'Table'"
			:df="df"
			:modelValue="modelValue"
			:engine="engine"
			:read_only="df.read_only"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Default (Data, Duration, Valid types defaulting to text) -->
		<DataControl
			v-else-if="!['Table', 'Signature', 'Button', 'Heading'].includes(df?.fieldtype)"
			:df="df || { fieldtype: 'Data' }"
			:modelValue="modelValue"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Fallback for unsupported/unsafe types -->
		<div v-else class="text-muted small p-2 border rounded bg-light">
			{{ df?.fieldtype }} {{ __("not supported in this context") }}
		</div>
	</div>
</template>

<script setup>
import LinkControl from "./LinkControl.vue";
import SelectControl from "./SelectControl.vue";
import CheckControl from "./CheckControl.vue";
import DataControl from "./DataControl.vue";
import MultiSelectControl from "./MultiSelectControl.vue";
import AutocompleteControl from "./AutocompleteControl.vue";
import FlexiGrid from "./FlexiGrid.vue";

const props = defineProps({
	df: Object,
	modelValue: [String, Number, Boolean, Array],
	doc: { type: Object, default: null }, // Context doc for autocomplete
	engine: { type: Object, default: null }, // Passed down to components like FlexiGrid
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

defineEmits(["update:modelValue"]);
</script>
