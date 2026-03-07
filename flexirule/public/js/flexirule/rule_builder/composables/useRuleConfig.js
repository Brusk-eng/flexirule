import { ref, reactive, computed, watch } from "vue";
import { useStore } from "../store";

/**
 * useRuleConfig
 *
 * Composable to manage the state and lifecycle of a rule node configuration.
 *
 * @param {Object} props - Component props containing the source node
 * @param {Object} emit - Component emit function
 */
export function useRuleConfig(props, emit) {
	const store = useStore();
	const draftNode = ref(null);
	const config = computed(() => draftNode.value?.data || {});

	// Refs for panel validation
	const panelRefs = {
		input: ref(null),
		config: ref(null),
		output: ref(null),
		logic: ref(null),
	};

	/**
	 * Create a draft copy of the node for editing.
	 */
	function createDraft() {
		if (!props.node) return;
		// Deep clone the node
		draftNode.value = JSON.parse(JSON.stringify(props.node));
	}

	/**
	 * Update a field value in the draft config.
	 */
	function updateField(fieldname, value, row = null) {
		if (!draftNode.value?.data) return;

		if (row) {
			row[fieldname] = value;
		} else {
			draftNode.value.data[fieldname] = value;
		}

		// We don't mark dirty in the store until Save is clicked
	}

	/**
	 * Validate the entire configuration.
	 * Checks all panels and returns { valid, errors }.
	 */
	async function validate() {
		const errors = [];

		// 1. Basic node data validation (action_label)
		if (!draftNode.value?.label && !draftNode.value?.data?.action_label) {
			// errors.push("Action label is required");
		}

		// 2. Panel-specific validation
		for (const [name, panelRef] of Object.entries(panelRefs)) {
			if (panelRef.value && typeof panelRef.value.validate === "function") {
				const res = await panelRef.value.validate();
				if (!res.valid) {
					if (res.errors) errors.push(...res.errors);
					if (res.message) errors.push(res.message);
				}
			}
		}

		return {
			valid: errors.length === 0,
			errors: errors,
		};
	}

	/**
	 * Save changes back to the source node and close.
	 */
	async function save() {
		const validation = await validate();
		if (!validation.valid) {
			const message = validation.errors.map((e) => `<li>${e}</li>`).join("");
			frappe.msgprint({
				title: __("Validation Error"),
				message: `<ul class="text-left" style="list-style-type: disc; padding-left: 20px;">${message}</ul>`,
				indicator: "red",
			});
			return false;
		}

		// Commit changes
		if (props.node && draftNode.value) {
			props.node.data = JSON.parse(JSON.stringify(draftNode.value.data));
			props.node.label = draftNode.value.label || draftNode.value.data?.action_label;
			store.mark_dirty();
		}

		emit("save", props.node.data);
		emit("update:modelValue", false);
		return true;
	}

	function cancel() {
		emit("update:modelValue", false);
	}

	// Watch for node changes or modal open to refresh draft
	watch(
		() => [props.node, props.modelValue],
		([newNode, isOpen]) => {
			if (isOpen && newNode) {
				createDraft();
			}
		},
		{ immediate: true }
	);

	return {
		draftNode,
		config,
		panelRefs,
		updateField,
		validate,
		save,
		cancel,
	};
}
