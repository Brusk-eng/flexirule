/**
 * Canonical JSON serialization for persisted Rule Builder state.
 *
 * Object key order is ignored, while array order and JSON value semantics are
 * preserved. The output is suitable for stable equality checks and snapshots.
 * Non-JSON values follow JSON.stringify semantics; circular structures throw.
 */
export function stableStringify(value) {
	const ancestors = new Set();

	function serialize(current, key = "") {
		if (current === null || typeof current !== "object") {
			return JSON.stringify(current);
		}

		if (ancestors.has(current)) {
			throw new TypeError("Converting circular structure to JSON");
		}

		if (typeof current.toJSON === "function") {
			ancestors.add(current);
			try {
				return serialize(current.toJSON(key), key);
			} finally {
				ancestors.delete(current);
			}
		}

		ancestors.add(current);
		try {
			if (Array.isArray(current)) {
				return (
					"[" +
					current
						.map((item, index) => {
							const serialized = serialize(item, String(index));
						return serialized === undefined ? "null" : serialized;
						})
						.join(",") +
					"]"
				);
			}

			const parts = [];
			for (const property of Object.keys(current).sort()) {
				const serialized = serialize(current[property], property);
				if (serialized !== undefined) {
					parts.push(JSON.stringify(property) + ":" + serialized);
				}
			}
			return "{" + parts.join(",") + "}";
		} finally {
			ancestors.delete(current);
		}
	}

	return serialize(value);
}
