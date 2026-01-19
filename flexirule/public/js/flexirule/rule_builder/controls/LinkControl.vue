<!-- Used as Link Control -->
<script setup>
import { onMounted, onUnmounted, ref, useSlots, watch, nextTick } from "vue";

const props = defineProps({
	df: { type: Object, required: true },
	modelValue: [String, Number],
	read_only: { type: Boolean, default: false },
	args: { type: Object, default: () => ({}) },
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);
const slots = useSlots();

const link = ref(null);
let link_control = null;

// Initialize control
async function init_control() {
	if (!link.value) return;

	// Cleanup previous control
	destroy_control();

	link.value.innerHTML = "";

	link_control = frappe.ui.form.make_control({
		parent: link.value,
		df: {
			...props.df,
			hidden: 0,
			read_only: props.read_only,
			change: () => {
				if (link_control) {
					const val = link_control.get_value();
					emit("update:modelValue", val);
				}
			},
		},
		value: props.modelValue,
		render_input: true,
		only_input: Boolean(slots.label),
	});

	// Handle table field logic
	apply_table_logic();
}

function destroy_control() {
	if (link_control) {
		if (link_control.$wrapper) {
			link_control.$wrapper.remove();
		}
		link_control = null;
	}
}

function apply_table_logic() {
	if (!link_control) return;

	if (props.args?.is_table_field) {
		if (link_control.df.filters) {
			link_control.df.filters.istable = 1;
		} else {
			link_control.df.filters = { istable: 1 };
		}
	} else {
		if (link_control.df.filters && "istable" in link_control.df.filters) {
			delete link_control.df.filters.istable;
		}
	}
}

onMounted(async () => {
	await nextTick();
	init_control();
});

onUnmounted(() => {
	destroy_control();
});

// Sync value changes from parent
watch(
	() => props.modelValue,
	(val) => {
		if (link_control && link_control.get_value() !== val) {
			link_control.set_value(val);
		}
	}
);

// Watch for read_only changes
watch(
	() => props.read_only,
	(val) => {
		if (link_control) {
			link_control.df.read_only = val;
			link_control.toggle_enable(!val);
		}
	}
);

// Watch for args changes
watch(
	() => props.args,
	() => {
		apply_table_logic();
	},
	{ deep: true }
);

// Handle DF changes gracefully
watch(
	() => props.df,
	async (newDf, oldDf) => {
		if (!link_control) return;

		// Re-initialize only if critical properties change
		if (newDf.fieldname !== oldDf?.fieldname || newDf.fieldtype !== oldDf?.fieldtype) {
			await init_control();
			return;
		}

		// Update mutable properties
		let changed = false;

		// Update mandatory/reqd
		if (link_control.df.reqd !== newDf.reqd) {
			link_control.df.reqd = newDf.reqd;
			link_control.toggle_reqd(newDf.reqd);
			changed = true;
		}

		// Update filters if changed
		if (JSON.stringify(link_control.df.filters) !== JSON.stringify(newDf.filters)) {
			link_control.df.filters = newDf.filters;
			apply_table_logic();
			changed = true;
		}

		// If description changed
		if (link_control.df.description !== newDf.description) {
			link_control.df.description = newDf.description;
			link_control.refresh(); // This might redraw
		}
	},
	{ deep: true }
);
</script>

<template>
	<div
		v-if="slots.label || (df.label && !hideLabel)"
		class="control frappe-control"
		:data-fieldtype="df?.fieldtype"
		:class="{ editable: slots.label }"
	>
		<!-- label -->
		<div class="field-controls">
			<slot name="label" />
			<div v-if="!slots.label && df.label && !hideLabel" class="control-label label" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</div>
			<slot name="actions" />
		</div>

		<!-- link input mounting point -->
		<div ref="link"></div>

		<!-- description -->
		<div
			v-if="df.description && !hideDescription"
			class="mt-2 description"
			v-html="__(df.description)"
		/>
	</div>
	<div v-else ref="link"></div>
</template>

<style scoped>
.field-controls {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 4px;
}

.description {
	font-size: 11px;
	color: var(--text-muted);
}
</style>
