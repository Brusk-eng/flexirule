/**
 * FlexiRule DocField Widget
 *
 * A single-field selector that picks a field from a DocType.
 * Used for custom fieldtype 'DocField' in process adapters.
 *
 * Simpler than FieldSelector - only selects from a single DocType source.
 * Value is the fieldname string.
 */

frappe.provide("flexirule");

flexirule.DocFieldWidget = class DocFieldWidget {
	/**
	 * Create DocField widget.
	 *
	 * @param {Object} opts - Options
	 * @param {HTMLElement|jQuery} opts.parent - Container element
	 * @param {Object} opts.df - Field definition with 'options' as DocType
	 * @param {string} opts.value - Initial value (fieldname)
	 * @param {Function} opts.on_change - Change callback (fieldname)
	 * @param {Object} opts.context - Context with doc, row, etc.
	 */
	constructor(opts) {
		this.parent = opts.parent instanceof jQuery ? opts.parent : $(opts.parent);
		this.df = opts.df || {};
		this.value = opts.value || "";
		this.on_change = opts.on_change;
		this.context = opts.context || {};

		// Resolve doctype from options
		this.doctype = this._resolve_doctype();

		// DOM
		this.$input = null;
		this.awesomplete = null;

		// Options cache
		this.field_options = [];
		this.fields_by_name = {};
	}

	/**
	 * Resolve the doctype from df.options.
	 * @private
	 */
	_resolve_doctype() {
		let options = this.df.options || "";

		// Handle "parent.document_type" pattern
		if (typeof options === "string" && options.startsWith("parent.")) {
			const field = options.replace("parent.", "");
			// Look in context.doc (parent document)
			return this.context.doc?.[field] || this.context[field] || "";
		}

		return options;
	}

	/**
	 * Render the widget.
	 */
	render() {
		this.$input = $(
			'<input class="form-control input-xs" placeholder="' + __("Select Field") + '">'
		).appendTo(this.parent);

		this.awesomplete = new Awesomplete(this.$input.get(0), {
			minChars: 0,
			maxItems: 99,
			autoFirst: true,
			list: [],
			item: (item) => {
				return $(`<li class="filter-field-select"><p>${item.label}</p></li>`)
					.data("item.autocomplete", item)
					.get(0);
			},
		});

		this.$input.on("click", () => {
			this.$input.select();
			if (this.field_options.length > 0) {
				this.awesomplete.evaluate();
			}
		});

		this.$input.on("awesomplete-select", (e) => {
			const item = this.awesomplete.get_item(e.originalEvent.text.value);
			this._on_select(item);
		});

		this.$input.on("awesomplete-selectcomplete", (e) => {
			const item = this.awesomplete.get_item(e.originalEvent.text.value);
			this.$input.val(item.label);
		});

		// Load fields if doctype is known
		if (this.doctype) {
			this._load_fields();
		}

		// Set initial value
		if (this.value) {
			this._set_display_value(this.value);
		}
	}

	/**
	 * Load fields from doctype.
	 * @private
	 */
	_load_fields() {
		frappe.model.with_doctype(this.doctype, () => {
			this._build_options();
			this._set_display_value(this.value);
		});
	}

	/**
	 * Build field options.
	 * @private
	 */
	_build_options() {
		this.field_options = [];
		this.fields_by_name = {};

		const meta = frappe.get_meta(this.doctype);
		if (!meta) return;

		// Valid fieldtypes
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
			"Check",
			"Dynamic Link",
			"Percent",
			"Rating",
			"Duration",
		];

		// Add 'name' field
		this.field_options.push({
			value: "name",
			label: __("Name (ID)"),
			fieldname: "name",
			fieldtype: "Data",
		});
		this.fields_by_name["name"] = this.field_options[0];

		// Add doctype fields
		(meta.fields || []).forEach((df) => {
			if (!valid_types.includes(df.fieldtype)) return;
			if (df.is_virtual) return;

			const option = {
				value: df.fieldname,
				label: `${__(df.label)} (${df.fieldtype})`,
				fieldname: df.fieldname,
				fieldtype: df.fieldtype,
			};

			this.field_options.push(option);
			this.fields_by_name[df.fieldname] = option;
		});

		this.awesomplete.list = this.field_options;
	}

	/**
	 * Handle field selection.
	 * @private
	 */
	_on_select(item) {
		this.value = item.fieldname;

		if (this.on_change) {
			this.on_change(this.value);
		}
	}

	/**
	 * Set display value from fieldname.
	 * @private
	 */
	_set_display_value(fieldname) {
		if (!fieldname) {
			this.$input.val("");
			return;
		}

		const item = this.fields_by_name[fieldname];
		if (item) {
			this.$input.val(item.label);
		} else {
			this.$input.val(fieldname);
		}
	}

	/**
	 * Get current value.
	 */
	get_value() {
		return this.value;
	}

	/**
	 * Set value.
	 */
	set_value(value) {
		this.value = value;
		this._set_display_value(value);
	}

	/**
	 * Refresh with new context.
	 */
	refresh(opts = {}) {
		if (opts.context) {
			this.context = opts.context;
			const new_doctype = this._resolve_doctype();

			if (new_doctype !== this.doctype) {
				this.doctype = new_doctype;
				this._load_fields();
			}
		}

		if (opts.value !== undefined) {
			this.set_value(opts.value);
		}
	}

	/**
	 * Destroy widget.
	 */
	destroy() {
		if (this.awesomplete) {
			this.awesomplete.destroy();
		}
		if (this.$input) {
			this.$input.remove();
		}
		this.field_options = [];
		this.fields_by_name = {};
	}
};

/**
 * FlexiRule MultiDocField Widget
 *
 * Multi-select field picker for selecting multiple fields from a DocType.
 * Value is an array of fieldnames.
 */
frappe.provide("flexirule");

flexirule.MultiDocFieldWidget = class MultiDocFieldWidget {
	/**
	 * Create MultiDocField widget.
	 */
	constructor(opts) {
		this.parent = opts.parent instanceof jQuery ? opts.parent : $(opts.parent);
		this.df = opts.df || {};
		this.value = opts.value || [];
		this.on_change = opts.on_change;
		this.context = opts.context || {};

		this.doctype = this._resolve_doctype();

		// DOM
		this.$wrapper = null;
		this.$input = null;
		this.$tags = null;
		this.awesomplete = null;

		// Options
		this.field_options = [];
		this.fields_by_name = {};
	}

	_resolve_doctype() {
		let options = this.df.options || "";
		if (typeof options === "string" && options.startsWith("parent.")) {
			const field = options.replace("parent.", "");
			return this.context.doc?.[field] || this.context[field] || "";
		}
		return options;
	}

	render() {
		this.$wrapper = $('<div class="multi-docfield-widget">');
		this.parent.append(this.$wrapper);

		// Tags container
		this.$tags = $(
			'<div class="multi-docfield-tags mb-2" style="display: flex; flex-wrap: wrap; gap: 4px;">'
		);
		this.$wrapper.append(this.$tags);

		// Input
		this.$input = $(
			'<input class="form-control input-xs" placeholder="' + __("Add Field") + '">'
		);
		this.$wrapper.append(this.$input);

		this.awesomplete = new Awesomplete(this.$input.get(0), {
			minChars: 0,
			maxItems: 99,
			autoFirst: true,
			list: [],
			filter: (text, input) => {
				// Exclude already selected
				if (this.value.includes(text.value)) return false;
				return Awesomplete.FILTER_CONTAINS(text, input);
			},
			item: (item) => {
				return $(`<li class="filter-field-select"><p>${item.label}</p></li>`)
					.data("item.autocomplete", item)
					.get(0);
			},
		});

		this.$input.on("click", () => {
			this.$input.select();
			this.awesomplete.evaluate();
		});

		this.$input.on("awesomplete-select", (e) => {
			const item = this.awesomplete.get_item(e.originalEvent.text.value);
			this._add_field(item.fieldname);
			this.$input.val("");
		});

		if (this.doctype) {
			this._load_fields();
		}

		this._render_tags();
	}

	_load_fields() {
		frappe.model.with_doctype(this.doctype, () => {
			this._build_options();
		});
	}

	_build_options() {
		this.field_options = [];
		this.fields_by_name = {};

		const meta = frappe.get_meta(this.doctype);
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
			"Check",
			"Dynamic Link",
			"Percent",
			"Rating",
			"Duration",
		];

		this.field_options.push({
			value: "name",
			label: __("Name (ID)"),
			fieldname: "name",
		});
		this.fields_by_name["name"] = this.field_options[0];

		(meta.fields || []).forEach((df) => {
			if (!valid_types.includes(df.fieldtype)) return;
			if (df.is_virtual) return;

			const option = {
				value: df.fieldname,
				label: `${__(df.label)} (${df.fieldtype})`,
				fieldname: df.fieldname,
			};

			this.field_options.push(option);
			this.fields_by_name[df.fieldname] = option;
		});

		this.awesomplete.list = this.field_options;
	}

	_add_field(fieldname) {
		if (this.value.includes(fieldname)) return;

		this.value.push(fieldname);
		this._render_tags();
		this._emit_change();
	}

	_remove_field(fieldname) {
		const idx = this.value.indexOf(fieldname);
		if (idx !== -1) {
			this.value.splice(idx, 1);
			this._render_tags();
			this._emit_change();
		}
	}

	_render_tags() {
		this.$tags.empty();

		this.value.forEach((fieldname) => {
			const item = this.fields_by_name[fieldname];
			const label = item ? item.label : fieldname;

			const $tag =
				$(`<span class="badge badge-secondary" style="padding: 4px 8px; cursor: pointer;">
                ${label}
                <span class="remove-tag" style="margin-left: 4px;">&times;</span>
            </span>`);

			$tag.find(".remove-tag").on("click", () => {
				this._remove_field(fieldname);
			});

			this.$tags.append($tag);
		});
	}

	_emit_change() {
		if (this.on_change) {
			this.on_change(this.value);
		}
	}

	get_value() {
		return this.value;
	}

	set_value(value) {
		this.value = Array.isArray(value) ? value : [];
		this._render_tags();
	}

	refresh(opts = {}) {
		if (opts.context) {
			this.context = opts.context;
			const new_doctype = this._resolve_doctype();
			if (new_doctype !== this.doctype) {
				this.doctype = new_doctype;
				this._load_fields();
			}
		}
		if (opts.value !== undefined) {
			this.set_value(opts.value);
		}
	}

	destroy() {
		if (this.awesomplete) {
			this.awesomplete.destroy();
		}
		if (this.$wrapper) {
			this.$wrapper.remove();
		}
		this.field_options = [];
		this.fields_by_name = {};
	}
};

/**
 * frappe.ui.form.ControlDocField
 */
frappe.ui.form.ControlDocField = class ControlDocField extends frappe.ui.form.ControlData {
	make_input() {
		this.$input_wrapper.empty();
		this.widget = new flexirule.DocFieldWidget({
			parent: this.$input_wrapper,
			df: this.df,
			on_change: (val) => {
				this.set_value(val);
			},
			context: this.df.context || {},
		});
		this.widget.render();
		this.input = this.widget.$input.get(0);
	}
	get_value() {
		return this.widget ? this.widget.get_value() : this.value;
	}
	set_value(val) {
		if (this.widget) {
			this.widget.set_value(val);
		}
		return super.set_value(val);
	}
	refresh_input() {
		if (this.widget) {
			this.widget.refresh({
				context: this.df.context || {},
				value: this.value,
			});
		}
	}
	destroy() {
		if (this.widget) {
			this.widget.destroy();
		}
		super.destroy();
	}
};

/**
 * frappe.ui.form.ControlMultiDocField
 */
frappe.ui.form.ControlMultiDocField = class ControlMultiDocField extends (
	frappe.ui.form.ControlData
) {
	make_input() {
		this.$input_wrapper.empty();
		this.widget = new flexirule.MultiDocFieldWidget({
			parent: this.$input_wrapper,
			df: this.df,
			on_change: (val) => {
				this.set_value(val);
			},
			context: this.df.context || {},
		});
		this.widget.render();
		this.input = this.widget.$input.get(0);
	}
	get_value() {
		return this.widget ? this.widget.get_value() : this.value;
	}
	set_value(val) {
		if (this.widget) {
			this.widget.set_value(val);
		}
		return super.set_value(val);
	}
	refresh_input() {
		if (this.widget) {
			this.widget.refresh({
				context: this.df.context || {},
				value: this.value,
			});
		}
	}
	destroy() {
		if (this.widget) {
			this.widget.destroy();
		}
		super.destroy();
	}
};
