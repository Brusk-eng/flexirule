/**
 * useHistoryStore — Undo/Redo history management.
 *
 * Follows Frappe builder pattern (form_builder/store.js, workflow_builder/store.js):
 *   - Uses @vueuse/core for ref history
 *   - Exposes canUndo/canRedo and undo/redo
 *
 * Separated so other stores can call `commit()` without circular deps.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const useHistoryStore = defineStore("rule-builder-history", () => {
	// ── Snapshot-based history ──
	const history_stack = ref([]);
	const history_index = ref(-1);
	const MAX_HISTORY = 50;

	const can_undo = computed(() => history_index.value > 0);
	const can_redo = computed(() => history_index.value < history_stack.value.length - 1);

	/**
	 * Capture a snapshot for history.
	 * @param {Function} getSnapshot — returns serializable state
	 */
	function commit(getSnapshot) {
		if (typeof getSnapshot !== "function") return;

		const snapshot = getSnapshot();
		if (!snapshot) return;

		const serialized = JSON.stringify(snapshot);

		// Deduplicate: skip if identical to current position
		if (history_index.value >= 0 && history_stack.value[history_index.value] === serialized) {
			return;
		}

		// Truncate any redo entries
		history_stack.value = history_stack.value.slice(0, history_index.value + 1);

		// Push new snapshot
		history_stack.value.push(serialized);

		// Enforce max size
		if (history_stack.value.length > MAX_HISTORY) {
			history_stack.value.shift();
		} else {
			history_index.value++;
		}
	}

	/**
	 * Undo to previous state.
	 * @param {Function} applySnapshot — receives parsed snapshot object
	 */
	function undo(applySnapshot) {
		if (!can_undo.value) return;
		history_index.value--;
		const snapshot = JSON.parse(history_stack.value[history_index.value]);
		if (typeof applySnapshot === "function") {
			applySnapshot(snapshot);
		}
	}

	/**
	 * Redo to next state.
	 * @param {Function} applySnapshot — receives parsed snapshot object
	 */
	function redo(applySnapshot) {
		if (!can_redo.value) return;
		history_index.value++;
		const snapshot = JSON.parse(history_stack.value[history_index.value]);
		if (typeof applySnapshot === "function") {
			applySnapshot(snapshot);
		}
	}

	/**
	 * Reset history (e.g., after save or initial load).
	 */
	function reset(getSnapshot) {
		history_stack.value = [];
		history_index.value = -1;
		if (getSnapshot) {
			commit(getSnapshot);
		}
	}

	return {
		// State
		history_stack,
		history_index,

		// Computed
		can_undo,
		can_redo,

		// Actions
		commit,
		undo,
		redo,
		reset,
	};
});
