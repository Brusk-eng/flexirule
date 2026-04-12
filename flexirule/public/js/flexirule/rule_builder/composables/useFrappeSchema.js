import { ref, reactive } from "vue";

const schemaCache = reactive({});

export function useFrappeSchema() {
	const loading = ref(false);

	const fetchSchema = async (doctype) => {
		if (!doctype) return null;

		// Return from cache if we already fetched it
		if (schemaCache[doctype]) {
			return schemaCache[doctype];
		}

		loading.value = true;
		try {
			const response = await frappe.call({
				method: "flexirule.ruleflow.api.schema.get_node_schema_meta",
				args: { doctype },
			});

			const meta = response.message;
			if (meta) {
				schemaCache[doctype] = meta;
				return meta;
			}
		} catch (e) {
			console.warn("Failed to fetch schema dynamically for:", doctype, e);
			// Fallback
			if (frappe.get_meta(doctype)) {
				return frappe.get_meta(doctype);
			}
		} finally {
			loading.value = false;
		}
		return null;
	};

	const getFields = (doctype) => {
		return schemaCache[doctype]?.fields || [];
	};

	return {
		fetchSchema,
		getFields,
		schemaCache,
		loading,
	};
}
