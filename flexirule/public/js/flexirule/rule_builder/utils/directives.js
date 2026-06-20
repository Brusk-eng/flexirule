
export const fieldRevealDirective = {
	mounted(el, binding) {
		const fieldname = binding.value;
		if (!fieldname) return;

		let isHovered = false;
		let originalText = "";
		let originalHTML = "";
		let isRevealed = false;

		const reveal = () => {
			if (isRevealed) return;
			originalHTML = el.innerHTML;
			originalText = el.innerText;

			// Use a span to maintain some styling if needed, but replace content
			el.innerText = fieldname;
			el.classList.add("fxr-field-revealed");
			isRevealed = true;
		};

		const reset = () => {
			if (!isRevealed) return;
			el.innerHTML = originalHTML;
			el.classList.remove("fxr-field-revealed");
			isRevealed = false;
		};

		const handleMouseMove = (e) => {
			isHovered = true;
			if (e.shiftKey) {
				reveal();
			} else {
				reset();
			}
		};

		const handleMouseLeave = () => {
			isHovered = false;
			reset();
		};

		const handleGlobalKeyDown = (e) => {
			if (e.key === "Shift" && isHovered) {
				reveal();
			}
		};

		const handleGlobalKeyUp = (e) => {
			if (e.key === "Shift") {
				reset();
			}
		};

		const handleClick = (e) => {
			if (e.shiftKey && isRevealed) {
				e.preventDefault();
				e.stopPropagation();

				navigator.clipboard.writeText(fieldname).then(() => {
					// Visual feedback
					const prevText = el.innerText;
					el.innerText = window.__ ? __("Copied!") : "Copied!";
					el.classList.add("fxr-copy-success");

					setTimeout(() => {
						el.classList.remove("fxr-copy-success");
						if (isRevealed) {
							el.innerText = fieldname;
						} else {
							reset();
						}
					}, 1000);

					if (window.frappe && frappe.show_alert) {
						frappe.show_alert({
							message: __ ? __("Fieldname copied to clipboard: {0}", [fieldname]) : `Fieldname copied: ${fieldname}`,
							indicator: "green"
						}, 3);
					}
				});
			}
		};

		el.addEventListener("mousemove", handleMouseMove);
		el.addEventListener("mouseleave", handleMouseLeave);
		el.addEventListener("click", handleClick, { capture: true });
		window.addEventListener("keydown", handleGlobalKeyDown);
		window.addEventListener("keyup", handleGlobalKeyUp);

		// Store cleanup function
		el._cleanupFieldReveal = () => {
			el.removeEventListener("mousemove", handleMouseMove);
			el.removeEventListener("mouseleave", handleMouseLeave);
			el.removeEventListener("click", handleClick, { capture: true });
			window.removeEventListener("keydown", handleGlobalKeyDown);
			window.removeEventListener("keyup", handleGlobalKeyUp);
		};
	},
	unmounted(el) {
		if (el._cleanupFieldReveal) {
			el._cleanupFieldReveal();
		}
	},
};
