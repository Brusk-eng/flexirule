/**
 * useMetaStore — DocType metadata cache.
 *
 * Follows Frappe builder pattern (workflow_builder/store.js L16-53):
 *   - Uses frappe.model.with_doctype + frappe.get_meta
 *   - Caches metadata per doctype
 *   - Pre-fetches child table metadata
 */
import { defineStore } from "pinia";
import { ref, computed, reactive } from "vue";

export const useMetaStore = defineStore("rule-builder-meta", () => {
	// ── State ──
	const doc_meta = reactive({}); // { [doctype]: field[] }
	const fetch_counter = ref(0); // in-flight metadata requests

	// ── Derived ──
	const meta_loading = computed(() => fetch_counter.value > 0);

	// ── Excluded field types for visual builder ──
	const EXCLUDED_FIELDTYPES = new Set([
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Button",
		"Image",
		"Fold",
		"Heading",
		"Spacer",
	]);

	// ── Standard fields available on all documents ──
	const STANDARD_FIELDS = [
		{ label: "Name (name)", fieldname: "name", fieldtype: "Data" },
		{ label: "Owner (owner)", fieldname: "owner", fieldtype: "Data" },
		{ label: "Creation (creation)", fieldname: "creation", fieldtype: "Datetime" },
		{ label: "Modified (modified)", fieldname: "modified", fieldtype: "Datetime" },
		{ label: "Modified By (modified_by)", fieldname: "modified_by", fieldtype: "Data" },
		{ label: "DocStatus (docstatus)", fieldname: "docstatus", fieldtype: "Int" },
	];

	/**
	 * Fetch metadata for a DocType and cache it.
	 * Follows Frappe pattern: frappe.model.with_doctype → frappe.get_meta
	 *
	 * @param {string} doctype - DocType name
	 * @returns {Promise<void>}
	 */
	async function fetch_metadata(doctype) {
		if (!doctype || doc_meta[doctype]) return;

		fetch_counter.value++;
		try {
			await new Promise((resolve) => {
				frappe.model.with_doctype(doctype, resolve);
			});

			const meta = frappe.get_meta(doctype);
			if (!meta) return;

			const fields = [];

			// Main table fields (doc.*)
			meta.fields.forEach((f) => {
				if (!EXCLUDED_FIELDTYPES.has(f.fieldtype)) {
					fields.push({
						label: `doc.${f.fieldname} (${f.label})`,
						value: `doc.${f.fieldname}`,
						fieldname: f.fieldname,
						fieldtype: f.fieldtype,
						options: f.options,
						is_main: true,
					});
				}
			});

			// Standard fields
			STANDARD_FIELDS.forEach((f) => {
				fields.push({
					label: `doc.${f.fieldname} (${f.label})`,
					value: `doc.${f.fieldname}`,
					fieldname: f.fieldname,
					fieldtype: f.fieldtype,
					is_std: true,
				});
			});

			// Assign reactively (spread for deep reactivity)
			doc_meta[doctype] = fields;

			// Pre-fetch child table metadata
			const tableFields = meta.fields.filter((f) => f.fieldtype === "Table" && f.options);
			for (const tf of tableFields) {
				await fetch_metadata(tf.options);
			}
		} catch (e) {
			console.warn("FlexiRule: Metadata fetch failed:", e);
			frappe.show_alert({
				message: __("Failed to fetch metadata for {0}", [doctype]),
				indicator: "orange",
			});
		} finally {
			fetch_counter.value--;
		}
	}

	/**
	 * Get fields for a DocType with an optional alias prefix.
	 *
	 * @param {string} doctype
	 * @param {string} alias - Variable prefix (default "doc")
	 * @returns {Array}
	 */
	function get_fields_for_doctype(doctype, alias = "doc") {
		if (!doctype || !doc_meta[doctype]) return [];

		return doc_meta[doctype].map((f) => ({
			...f,
			label: `${alias}.${f.fieldname} (${
				f.label.split("(")[1] ? f.label.split("(")[1].replace(")", "") : f.label
			})`,
			value: `${alias}.${f.fieldname}`,
		}));
	}

	/**
	 * Get raw Frappe meta for a DocType.
	 * @param {string} doctype
	 * @returns {Object|null}
	 */
	function get_raw_meta(doctype) {
		if (!doctype) return null;
		return frappe.get_meta(doctype);
	}

	return {
		// State
		doc_meta,
		fetch_counter,

		// Computed
		meta_loading,

		// Actions
		fetch_metadata,
		get_fields_for_doctype,
		get_raw_meta,
	};
});
