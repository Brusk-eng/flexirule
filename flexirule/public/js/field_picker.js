frappe.provide("frappe.ui.form");

frappe.ui.form.ControlData = class ControlData extends frappe.ui.form.ControlData {
    make_input() {
        console.log("ControlData make_input called for", this.df.fieldname);
        if (this.df.options !== "Field Picker") {
            console.log("Not a Field Picker, default input");
            super.make_input();
            return;
        }

        super.make_input();
        console.log("Field Picker active for", this.df.fieldname);
        this.setup_field_picker_autocomplete();
    }


    setup_field_picker_autocomplete() {
        const me = this;

        if (!this.$input || !this.frm) return;

        const target_doctype = this.df.options_doctype || this.frm.doctype;
        const meta = frappe.get_meta(target_doctype);
        if (!meta) return;

        console.log("target_doctype:", target_doctype);
        console.log("meta fields:", meta ? meta.fields : "no meta found");

        const fields = meta.fields
            .filter(df => df.fieldname && !frappe.model.no_value_type.includes(df.fieldtype))
            .map(df => ({
                label: `${df.label} (${df.fieldname})`,
                value: `${target_doctype}.${df.fieldname}`
            }));

        console.log("fields for autocomplete:", fields);


        // Destroy old instance if any
        if (this.awesomplete) this.awesomplete.destroy();

        // Initialize Awesomplete with proper item rendering
        console.log("fields array:", fields);
        fields.forEach(f => console.log(f.label, f.value));

        this.awesomplete = new Awesomplete(this.$input.get(0), {
            list: fields,
            item: function (item) {
                console.log("Rendering item:", item);
                const li = document.createElement("li");
                li.textContent = item.label;
                return li;
            },
            replace: function (item) {
                console.log("Selected item:", item);
                me.set_value(item.value);
            }
        });


        this.$input.on("focus", () => {
            console.log("Input focused, opening Awesomplete");
            me.awesomplete.evaluate();
            me.awesomplete.open();
        });

    }
};
