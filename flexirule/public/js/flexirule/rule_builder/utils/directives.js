export const fieldRevealDirective = {
	mounted(el, binding) {
		el._revealState = {
			fieldname: binding.value,
			isHovered: false,
			originalHTML: "",
			isRevealed: false,
		};

		const reveal = () => {
			const state = el._revealState;
			if (state.isRevealed || !state.fieldname) return;
			state.originalHTML = el.innerHTML;

			el.innerText = state.fieldname;
			el.classList.add("fxr-field-revealed");
			state.isRevealed = true;
		};

		const reset = () => {
			const state = el._revealState;
			if (!state.isRevealed) return;
			el.innerHTML = state.originalHTML;
			el.classList.remove("fxr-field-revealed");
			state.isRevealed = false;
		};

		const handleMouseMove = (e) => {
			el._revealState.isHovered = true;
			if (e.shiftKey) {
				reveal();
			} else {
				reset();
			}
		};

		const handleMouseLeave = () => {
			el._revealState.isHovered = false;
			reset();
		};

		const handleGlobalKeyDown = (e) => {
			if (e.key === "Shift" && el._revealState.isHovered) {
				reveal();
			}
		};

		const handleGlobalKeyUp = (e) => {
			if (e.key === "Shift") {
				reset();
			}
		};

		const handleClick = (e) => {
			const state = el._revealState;
			if (e.shiftKey && state.isRevealed) {
				e.preventDefault();
				e.stopPropagation();

				navigator.clipboard.writeText(state.fieldname).then(() => {
					const prevText = el.innerText;
					el.innerText = window.__ ? __("Copied!") : "Copied!";
					el.classList.add("fxr-copy-success");

					setTimeout(() => {
						el.classList.remove("fxr-copy-success");
						if (state.isRevealed) {
							el.innerText = state.fieldname;
						} else {
							reset();
						}
					}, 800);

					if (window.frappe && frappe.show_alert) {
						frappe.show_alert(
							{
								message: __
									? __("Fieldname copied: {0}", [state.fieldname])
									: `Fieldname copied: ${state.fieldname}`,
								indicator: "green",
							},
							3
						);
					}
				});
			}
		};

		el.addEventListener("mousemove", handleMouseMove);
		el.addEventListener("mouseleave", handleMouseLeave);
		el.addEventListener("click", handleClick, { capture: true });
		window.addEventListener("keydown", handleGlobalKeyDown);
		window.addEventListener("keyup", handleGlobalKeyUp);

		el._cleanupFieldReveal = () => {
			el.removeEventListener("mousemove", handleMouseMove);
			el.removeEventListener("mouseleave", handleMouseLeave);
			el.removeEventListener("click", handleClick, { capture: true });
			window.removeEventListener("keydown", handleGlobalKeyDown);
			window.removeEventListener("keyup", handleGlobalKeyUp);
		};
	},
	updated(el, binding) {
		el._revealState.fieldname = binding.value;
	},
	unmounted(el) {
		if (el._cleanupFieldReveal) {
			el._cleanupFieldReveal();
		}
	},
};
