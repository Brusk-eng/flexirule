import { ref, nextTick } from "vue";

export function useFocusTrap() {
	const lastFocusedElement = ref(null);

	const getFocusableElements = (container) => {
		if (!container) return [];
		return Array.from(
			container.querySelectorAll(
				'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
			)
		).filter((el) => el.offsetWidth > 0 || el.offsetHeight > 0);
	};

	const handleTab = (e, container) => {
		const focusable = getFocusableElements(container);
		if (focusable.length === 0) return;

		const first = focusable[0];
		const last = focusable[focusable.length - 1];

		if (e.shiftKey && document.activeElement === first) {
			e.preventDefault();
			last.focus();
		} else if (!e.shiftKey && document.activeElement === last) {
			e.preventDefault();
			first.focus();
		}
	};

	const trapFocus = (container) => {
		lastFocusedElement.value = document.activeElement;
		nextTick(() => {
			const focusable = getFocusableElements(container);
			if (focusable.length > 0) {
				focusable[0].focus();
			}
		});
	};

	const untrapFocus = () => {
		if (lastFocusedElement.value && document.body.contains(lastFocusedElement.value)) {
			lastFocusedElement.value.focus();
		}
	};

	return {
		handleTab,
		trapFocus,
		untrapFocus,
	};
}
