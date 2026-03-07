<script setup>
/**
 * MultiCheckControl - Wrapper for Frappe's MultiCheck control
 * Provides a list of checkboxes for multiple selection.
 * Options should be an array of {label, value} or {label, value, checked}.
 */

const props = defineProps({
	df: Object,
	modelValue: [Array, String],
	read_only: Boolean,
	hideLabel: Boolean,
});

const emit = defineEmits(["update:modelValue"]);

let wrapper = ref(null);
let control = ref(null);
let processing_update = false;
let show_popover = ref(false);

const selectedValues = computed(() => {
	if (Array.isArray(props.modelValue)) return props.modelValue;
	if (typeof props.modelValue === "string" && props.modelValue) {
		return props.modelValue
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
	}
	return [];
});

const selectedCount = computed(() => selectedValues.value.length);

const summaryLabel = computed(() => {
	const count = selectedCount.value;
	if (count === 0) return __("Select options...");
	if (count === 1) return __("1 Selected");
	return __("{0} Selected", [count]);
});

function togglePopover() {
	if (props.read_only) return;
	show_popover.value = !show_popover.value;
	if (show_popover.value) {
		// Close when clicking outside
		setTimeout(() => {
			const handleOutsideClick = (e) => {
				if (
					!e.target.closest(".multi-check-popover") &&
					!e.target.closest(".dropdown-trigger")
				) {
					show_popover.value = false;
					document.removeEventListener("click", handleOutsideClick);
				}
			};
			document.addEventListener("click", handleOutsideClick);
		}, 0);
	}
}

function make_control() {
	if (!wrapper.value) return;
	wrapper.value.innerHTML = "";

	const current_selection = selectedValues.value;

	// Robust Options Parsing with Selection State
	let options = props.df.options || [];
	if (typeof options === "string") {
		options = options
			.split("\n")
			.map((o) => o.trim())
			.filter(Boolean)
			.map((o) => ({
				label: o,
				value: o,
				checked: current_selection.includes(o),
			}));
	} else if (Array.isArray(options)) {
		options = options.map((o) => {
			const val = typeof o === "object" ? o.value : o;
			const label = typeof o === "object" ? o.label : o;
			return {
				label: label,
				value: val,
				checked: current_selection.includes(val),
			};
		});
	}

	try {
		control.value = frappe.ui.form.make_control({
			parent: wrapper.value,
			df: {
				...props.df,
				fieldtype: "MultiCheck",
				label: props.df.label,
				options: options,
				read_only: props.read_only,
				on_change: () => {
					if (processing_update) return;
					const val = control.value.get_value();

					processing_update = true;
					emit("update:modelValue", val);
					// Allow vue to process update before resetting flag
					setTimeout(() => {
						processing_update = false;
					}, 50);
				},
			},
			render_input: true,
		});

		if (current_selection.length > 0) {
			processing_update = true;
			control.value.set_value(current_selection);
			setTimeout(() => {
				processing_update = false;
			}, 50);
		}
	} catch (e) {
		console.error("Failed to create MultiCheck control", e);
		wrapper.value.innerHTML = `<div class="text-danger">Error loading control: ${e.message}</div>`;
	}
}

onMounted(() => {
	make_control();
});

watch(
	() => props.modelValue,
	(val) => {
		if (!control.value || processing_update) return;

		const currentVal = control.value.get_value() || [];
		const newVal = Array.isArray(val)
			? val
			: typeof val === "string"
			? val.split(",").map((s) => s.trim())
			: [val];

		// Sort and stringify for deep comparison
		const currentSorted = [...currentVal].sort();
		const newSorted = [...newVal].sort();

		if (JSON.stringify(currentSorted) !== JSON.stringify(newSorted)) {
			processing_update = true;
			control.value.set_value(newVal);
			setTimeout(() => {
				processing_update = false;
			}, 50);
		}
	},
	{ deep: true }
);

// Watch df changes but only recreate if critical properties change
watch(
	() => [props.df.options, props.df.read_only],
	() => {
		make_control();
	}
);

onBeforeUnmount(() => {
	// Cleanup if necessary
});
</script>

<template>
	<div class="control frappe-control multi-check-control" :class="{ 'in-grid': hideLabel }">
		<div v-if="df.label && !hideLabel" class="control-label label" :class="{ reqd: df.reqd }">
			{{ __(df.label) }}
		</div>

		<!-- Dropdown Mode (for Grid) -->
		<template v-if="hideLabel">
			<div
				class="dropdown-trigger"
				:class="{ 'has-value': selectedCount > 0, disabled: read_only }"
				@click.stop="togglePopover"
			>
				<span>{{ summaryLabel }}</span>
				<i class="fa fa-chevron-down"></i>
			</div>

			<div v-show="show_popover" class="multi-check-popover">
				<div class="popover-inner" ref="wrapper"></div>
			</div>
		</template>

		<!-- Normal Mode -->
		<template v-else>
			<div class="control-wrapper" ref="wrapper"></div>
		</template>

		<div
			v-if="df.description && !hideLabel"
			class="description text-muted mt-1"
			v-html="__(df.description)"
		></div>
	</div>
</template>

<script>
export default {
	name: "MultiCheckControl",
};
</script>

<style scoped>
.multi-check-control {
	margin-bottom: var(--margin-md);
	position: relative;
}
.multi-check-control.in-grid {
	margin-bottom: 0;
	width: 100%;
}

.dropdown-trigger {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 4px 8px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background: var(--fg-color);
	cursor: pointer;
	font-size: 11px;
	min-height: 28px;
	transition: all 0.2s ease;
}

.dropdown-trigger:hover:not(.disabled) {
	border-color: var(--gray-400);
}

.dropdown-trigger.has-value {
	border-color: var(--primary);
	color: var(--primary);
	font-weight: 500;
}

.dropdown-trigger.disabled {
	cursor: default;
	background: var(--bg-color);
	opacity: 0.7;
}

.multi-check-popover {
	position: absolute;
	top: 100%;
	left: 0;
	z-index: 1000;
	background: #fff;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	box-shadow: var(--shadow-md);
	margin-top: 4px;
	min-width: 180px;
	max-width: 300px;
	max-height: 250px;
	overflow-y: auto;
}

.popover-inner {
	padding: 12px;
}

.control-wrapper {
	min-height: 35px;
	padding: 8px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background-color: var(--fg-color);
}
:deep(.form-group) {
	margin-bottom: 0 !important;
}
:deep(.unit-checkbox) {
	margin-bottom: 4px;
	display: block;
}
:deep(.checkbox) {
	margin: 0;
	display: flex;
	align-items: center;
}
:deep(.checkbox label) {
	margin: 0 0 0 8px;
	font-weight: normal;
}
</style>
