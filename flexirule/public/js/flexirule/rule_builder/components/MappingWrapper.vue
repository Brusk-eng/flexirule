<template>
	<div class="mapping-wrapper">
		<div class="d-flex justify-content-between align-items-center mb-1">
			<label class="mb-0">
				{{ label }}
				<span v-if="reqd" class="text-danger">*</span>
			</label>
			<div class="mode-toggle">
				<span class="mode-label" :class="{ active: !isMapped }">{{ __("Static") }}</span>
				<button
					class="btn btn-xs btn-default mode-switch"
					@click="toggleMode"
					:title="isMapped ? __('Compare to Static Value') : __('Compare to Field')"
				>
					<i
						class="fa"
						:class="isMapped ? 'fa-link text-primary' : 'fa-font text-muted'"
					></i>
				</button>
				<span class="mode-label" :class="{ active: isMapped }">{{ __("Field") }}</span>
			</div>
		</div>

		<div v-if="isMapped" class="mapped-input">
			<ContextPicker
				:modelValue="mappingValue"
				:docFields="docFields"
				@update:modelValue="$emit('update:mappingValue', $event)"
			/>
			<div class="hint text-primary">
				<i class="fa fa-link"></i> {{ __("Comparing to another field") }}
			</div>
		</div>
		<div v-else class="static-input">
			<slot></slot>
		</div>
	</div>
</template>

<script setup>
import ContextPicker from "./ContextPicker.vue";

const props = defineProps({
	label: String,
	reqd: [Boolean, Number],
	mappingValue: String,
	docFields: Array,
});

const emit = defineEmits(["update:mappingValue", "clearStatic"]);

const isMapped = ref(false);

watch(
	() => props.mappingValue,
	(val) => {
		if (val) isMapped.value = true;
	},
	{ immediate: true }
);

function toggleMode() {
	isMapped.value = !isMapped.value;

	if (isMapped.value) {
		// Switched to Field mode: Clear static value in parent
		emit("clearStatic");
	} else {
		// Switched to Static: Clear mapping value
		emit("update:mappingValue", undefined);
	}
}
</script>

<style scoped>
.mode-toggle {
	display: flex;
	align-items: center;
	gap: 4px;
}
.mode-label {
	font-size: 10px;
	color: var(--text-light);
	text-transform: uppercase;
}
.mode-label.active {
	color: var(--text-color);
	font-weight: 600;
}
.mode-switch {
	padding: 2px 6px;
}
.hint {
	font-size: 10px;
	margin-top: 4px;
}
.mapped-input input {
	border-color: var(--primary);
	background-color: var(--bg-light-blue);
}
</style>
