/**
 * FlexiRule Utils: DOM Helpers
 *
 * Utility functions for DOM manipulation with proper cleanup.
 * Follows Frappe patterns using jQuery where appropriate.
 */

frappe.provide("flexirule.utils.dom");

flexirule.utils = flexirule.utils || {};
flexirule.utils.dom = {};

/**
 * Safely remove an element from the DOM.
 *
 * @param {HTMLElement|jQuery} el - Element to remove
 */
flexirule.utils.dom.remove_element = function (el) {
	if (!el) return;

	if (el instanceof jQuery) {
		el.remove();
	} else if (el instanceof HTMLElement) {
		el.remove();
	} else if (el.wrapper) {
		// Frappe control pattern
		$(el.wrapper).remove();
	}
};

/**
 * Empty all children from an element.
 *
 * @param {HTMLElement|jQuery} el - Element to empty
 */
flexirule.utils.dom.empty_element = function (el) {
	if (!el) return;

	if (el instanceof jQuery) {
		el.empty();
	} else if (el instanceof HTMLElement) {
		el.innerHTML = "";
	}
};

/**
 * Create an HTML element with classes and attributes.
 *
 * @param {string} tag - HTML tag name
 * @param {Object} opts - Options { classes: [], attrs: {}, text: '' }
 * @returns {jQuery} - jQuery-wrapped element
 */
flexirule.utils.dom.create_element = function (tag, opts = {}) {
	const $el = $(`<${tag}>`);

	if (opts.classes) {
		if (Array.isArray(opts.classes)) {
			$el.addClass(opts.classes.join(" "));
		} else {
			$el.addClass(opts.classes);
		}
	}

	if (opts.attrs) {
		for (const key in opts.attrs) {
			if (opts.attrs.hasOwnProperty(key)) {
				$el.attr(key, opts.attrs[key]);
			}
		}
	}

	if (opts.text) {
		$el.text(opts.text);
	}

	if (opts.html) {
		$el.html(opts.html);
	}

	return $el;
};

/**
 * Create a table structure for FlexiTable.
 *
 * @param {Object} opts - Options { parent: $el }
 * @returns {Object} - { $table, $thead, $tbody }
 */
flexirule.utils.dom.create_table = function (opts) {
	const $table = $('<table class="table table-bordered flexi-table">');
	const $thead = $("<thead>").appendTo($table);
	const $tbody = $("<tbody>").appendTo($table);

	if (opts.parent) {
		$table.appendTo(opts.parent);
	}

	return { $table, $thead, $tbody };
};

/**
 * Create a table header row.
 *
 * @param {Array} columns - Array of column definitions with 'label' property
 * @param {Object} opts - Options { include_actions: boolean }
 * @returns {jQuery} - Header row element
 */
flexirule.utils.dom.create_header_row = function (columns, opts = {}) {
	const $tr = $("<tr>");

	columns.forEach((col) => {
		const label = col.label || frappe.unscrub(col.fieldname || "");
		$("<th>").text(__(label)).attr("data-fieldname", col.fieldname).appendTo($tr);
	});

	if (opts.include_actions) {
		$('<th class="flexi-table-actions">').text("").css("width", "40px").appendTo($tr);
	}

	return $tr;
};

/**
 * Create a table body row container.
 *
 * @param {Object} opts - Options { row_idx: number }
 * @returns {jQuery} - Row element
 */
flexirule.utils.dom.create_body_row = function (opts = {}) {
	const $tr = $('<tr class="flexi-table-row">');

	if (opts.row_idx !== undefined) {
		$tr.attr("data-row-idx", opts.row_idx);
	}

	return $tr;
};

/**
 * Create a table cell.
 *
 * @param {Object} opts - Options { fieldname: string }
 * @returns {jQuery} - Cell element
 */
flexirule.utils.dom.create_cell = function (opts = {}) {
	const $td = $('<td class="flexi-table-cell">');

	if (opts.fieldname) {
		$td.attr("data-fieldname", opts.fieldname);
	}

	return $td;
};
