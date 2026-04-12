import { ref, readonly } from "vue";
import { useFrappe } from "frappe-ui";

/**
 * useFuzzySearch wrapper
 * Calls frappe backend API for rapidfuzz matching of Actions/Operations
 */
export function useFuzzySearch() {
	const isSearching = ref(false);
	const searchResults = ref([]);
	const error = ref(null);

	const frappe = useFrappe(); // Assuming typical frappe-ui usage or window.frappe

	/**
	 * Search actions using backend rapidfuzz API
	 * @param {string} query
	 * @param {object} filters
	 * @param {number} limit
	 */
	async function searchActions(query, filters = {}, limit = 20) {
		if (!query || query.length < 2) {
			searchResults.value = [];
			return [];
		}

		isSearching.value = true;
		error.value = null;

		try {
			// Using typical window.frappe.call or fetching
			const res = await window.frappe.call({
				method: "flexirule.ruleflow.api.search_actions",
				args: {
					query,
					filters: typeof filters === "object" ? JSON.stringify(filters) : filters,
					limit,
				},
			});

			searchResults.value = res.message || [];
			return searchResults.value;
		} catch (e) {
			error.value = e.message || "Search failed";
			console.error(error.value);
			return [];
		} finally {
			isSearching.value = false;
		}
	}

	return {
		isSearching: readonly(isSearching),
		searchResults: readonly(searchResults),
		error: readonly(error),
		searchActions,
	};
}
