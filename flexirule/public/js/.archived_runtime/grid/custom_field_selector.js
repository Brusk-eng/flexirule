/**
 * Custom Field Selector that works within Frappe's grid system
 */
frappe.provide("flexirule.grid");

flexirule.grid.CustomFieldSelector = class CustomFieldSelector {
	constructor(opts) {
		this.parent = opts.parent;
		this.fieldname = opts.fieldname;
		this.context = opts.context;
		this.on_change = opts.on_change;
		this.row_doc = opts.row_doc;

		this.$wrapper = null;
		this.field_options = [];
		this.fields_by_name = {};
	}

	render($container, row_doc, context) {
		this.row_doc = row_doc;
		this.context = context;

		this.$wrapper = $(`
            <div class="custom-field-selector-wrapper">
                <select class="form-control input-xs field-selector-control">
                    <option value="">Select Field...</option>
                </select>
            </div>
        `);

		$container.append(this.$wrapper);
		this.$select = this.$wrapper.find(".field-selector-control");

		// Load field options based on context
		this._load_field_options();
		this._bind_events();

		// Set initial value
		if (row_doc[this.fieldname]) {
			this.$select.val(row_doc[this.fieldname]);
		}
	}

	_load_field_options() {
		// Get doctype from context
		const doctype = this.context.document_type;

		if (doctype) {
			frappe.model.with_doctype(doctype, () => {
				this._build_field_options(doctype);
			});
		}
	}

	_build_field_options(doctype) {
		const meta = frappe.get_meta(doctype);
		if (!meta) return;

		const valid_types = [
			"Data",
			"Link",
			"Text",
			"Phone",
			"Email",
			"Small Text",
			"Date",
			"Datetime",
			"Int",
			"Float",
			"Currency",
			"Select",
		];

		// Add standard fields
		const std_fields = frappe.model.std_fields.filter((f) => valid_types.includes(f.fieldtype));

		std_fields.forEach((df) => {
			this._add_option(df.fieldname, `${df.label} (${df.fieldtype})`);
		});

		// Add doctype fields
		(meta.fields || []).forEach((df) => {
			if (valid_types.includes(df.fieldtype) && !df.is_virtual) {
				this._add_option(df.fieldname, `${df.label} (${df.fieldtype})`);
			}
		});
	}

	_add_option(value, label) {
		this.$select.append(`<option value="${value}">${label}</option>`);
	}

	_bind_events() {
		this.$select.on("change", (e) => {
			const value = e.target.value;
			if (this.on_change) {
				this.on_change(this.fieldname, value, this.row_doc);
			}
		});
	}

	destroy() {
		if (this.$wrapper) {
			this.$wrapper.remove();
		}
	}
};
