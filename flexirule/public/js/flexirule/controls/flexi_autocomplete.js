
frappe.provide("flexirule");

flexirule.ControlAutocomplete = class ControlAutocomplete extends frappe.ui.form.ControlAutocomplete {
    make_input() {
        super.make_input();
        // In standard V15, setup_awesomplete handles initialization
    }

    get_awesomplete_settings() {
        const settings = super.get_awesomplete_settings();

        // Override the item renderer to show description
        settings.item = function (item) {
            const d = this.get_item(item.value);
            let label = (d && d.label) || item.label || item.value;
            const value = (d && d.value) || item.value;

            // Handle translations if available
            if (this.translate_values) {
                label = __(label, null, d && d.parent);
            }

            let html = `<strong>${label}</strong>`;

            // Add description if available
            if (d && d.description) {
                html += `<br><span class="small text-muted">${__(d.description)}</span>`;
            }

            // Add value/variable indicator if useful (optional)
            if (d && d.is_variable) {
                html += `<br><span class="small text-muted i">${__("Variable")}</span>`;
            }

            return $("<li></li>")
                .data("item.autocomplete", d || item)
                .prop("aria-selected", "false")
                .html(`<a><p>${html}</p></a>`)
                .get(0);
        };

        return settings;
    }

    format_for_input(value) {
        // If we have data, try to find the label
        // This is important for "Value" vs "Label" display
        if (this._data && this._data.length) {
            const item = this._data.find(i => i.value == value);
            if (item) {
                return item.label;
            }
        }
        return super.format_for_input(value);
    }
};

// Register for Frappe Form usage
(function () {
    try {
        if (typeof frappe === "undefined") return;
        frappe.provide("frappe.ui.form");
        if (typeof frappe.ui.form.control_map === "undefined") {
            frappe.ui.form.control_map = {};
        }
        frappe.ui.form.control_map["FlexiAutocomplete"] = flexirule.ControlAutocomplete;
    } catch (e) {
        // eslint-disable-next-line
        console.warn("FlexiRule: Failed to register FlexiAutocomplete control", e);
    }
})();
