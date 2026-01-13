<!-- Used as Link Control -->
<script setup>
import { onMounted, ref, useSlots, watch, nextTick } from "vue";

const props = defineProps(["args", "df", "read_only", "modelValue"]);
const emit = defineEmits(["update:modelValue"]);
const slots = useSlots();

const link = ref(null);
let link_control = null;

// Initialize control
async function init_control() {
	if (!link.value) return;
	link.value.innerHTML = "";

	link_control = frappe.ui.form.make_control({
		parent: link.value,
		df: {
			...props.df,
			hidden: 0,
			read_only: Boolean(slots.label) || props.read_only,
			change: () => {
				const val = link_control.get_value();
				emit("update:modelValue", val);
			},
		},
		value: props.modelValue,
		render_input: true,
		only_input: Boolean(slots.label),
	});

	// Handle table field logic
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

// Sync value changes from parent
watch(
	() => props.modelValue,
	(val) => {
		if (link_control && link_control.get_value() !== val) {
			link_control.set_value(val);
		}
	}
);

// Handle DF changes gracefully
watch(
	() => props.df,
	(newDf, oldDf) => {
		if (!link_control) return;

		// Re-initialize only if critical properties change
		if (newDf.fieldname !== oldDf?.fieldname || newDf.fieldtype !== oldDf?.fieldtype) {
			init_control();
			return;
		}

		// Update mutable properties
		let changed = false;

		// Update read_only if changed
		const newReadOnly = Boolean(slots.label) || props.read_only || newDf.read_only;
		if (link_control.df.read_only !== newReadOnly) {
			link_control.df.read_only = newReadOnly;
			link_control.toggle_enable(!newReadOnly);
			changed = true;
		}

		// Update mandatory/reqd
		if (link_control.df.reqd !== newDf.reqd) {
			link_control.df.reqd = newDf.reqd;
			link_control.toggle_reqd(newDf.reqd);
			changed = true;
		}

		// Update filters if changed
		if (JSON.stringify(link_control.df.filters) !== JSON.stringify(newDf.filters)) {
			link_control.df.filters = newDf.filters;
			
			// Re-apply table logic if needed
			if (props.args?.is_table_field) {
				if (link_control.df.filters) {
					link_control.df.filters.istable = 1;
				} else {
					link_control.df.filters = { istable: 1 };
				}
			}
			changed = true;
			
			// If filters changed, we might want to refresh valid options? 
			// Usually link field fetches dynamically so it's fine.
		}

		// If description changed
		if (link_control.df.description !== newDf.description) {
			link_control.df.description = newDf.description;
			link_control.refresh(); // This might redraw
		}
	},
	{ deep: true } // Need deep watch because we receive a new object every time anyway
);
</script>

<template>
	<div
		v-if="slots.label"
		class="control frappe-control"
		:data-fieldtype="df?.fieldtype"
		:class="{ editable: slots.label }"
	>
		<!-- label -->
		<div class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>

		<!-- link input -->
		<input class="form-control" type="text" readonly />

		<!-- description -->
		<div v-if="df.description" class="mt-2 description" v-html="df.description" />
	</div>
	<div v-else ref="link"></div>
</template>
