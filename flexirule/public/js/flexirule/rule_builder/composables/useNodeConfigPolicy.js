import { computed, ref, watch } from "vue";

const schema_cache = new Map();

function normalize_options(field_def, fallback) {
	if (!field_def) return fallback;
	if (field_def.options === undefined || field_def.options === null || field_def.options === "") {
		return fallback;
	}
	return field_def.options;
}

export function useNodeConfigPolicy(params = {}) {
	const schema = ref(null);
	const loading = ref(false);
	const error = ref(null);

	const actionType = computed(() =>
		typeof params.actionType === "function"
			? params.actionType()
			: params.actionType?.value || ""
	);
	const operation = computed(() =>
		typeof params.operation === "function" ? params.operation() : params.operation?.value || ""
	);
	const processName = computed(() =>
		typeof params.processName === "function"
			? params.processName()
			: params.processName?.value || ""
	);

	const cache_key = computed(
		() => `${actionType.value || ""}::${operation.value || ""}::${processName.value || ""}`
	);

	const field_map = computed(() => {
		const out = {};
		const fields = schema.value?.fields || [];
		fields.forEach((f) => {
			if (f?.fieldname) out[f.fieldname] = f;
		});
		return out;
	});

	async function load_schema() {
		if (!actionType.value) {
			schema.value = null;
			return;
		}

		const key = cache_key.value;
		if (schema_cache.has(key)) {
			schema.value = schema_cache.get(key);
			return;
		}

		loading.value = true;
		error.value = null;
		try {
			const res = await frappe.call({
				method: "flexirule.ruleflow.api.get_node_config_schema",
				args: {
					action_type: actionType.value,
					operation: operation.value || null,
					process_name: processName.value || null,
				},
			});
			schema.value = res.message || null;
			schema_cache.set(key, schema.value);
		} catch (e) {
			error.value = e;
			console.warn("FlexiRule: Node config policy load failed", e);
			schema.value = null;
		} finally {
			loading.value = false;
		}
	}

	function getPolicyField(fieldname, fallback = {}) {
		const server_df = field_map.value[fieldname];
		if (!server_df) return fallback;

		return {
			...fallback,
			...server_df,
			options: normalize_options(server_df, fallback.options),
		};
	}

	function getPolicyValue(fieldname, key, fallback = undefined) {
		const df = field_map.value[fieldname];
		if (!df) return fallback;
		const value = df[key];
		return value === undefined ? fallback : value;
	}

	watch([actionType, operation, processName], () => load_schema(), {
		immediate: true,
	});

	return {
		schema,
		loading,
		error,
		field_map,
		getPolicyField,
		getPolicyValue,
		reloadPolicy: load_schema,
	};
}
