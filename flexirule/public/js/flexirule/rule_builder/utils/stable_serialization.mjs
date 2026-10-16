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
		// JSON.stringify calls toJSON once for the current property, then serializes
		// the returned value directly. Do not recurse through serialize() here,
		// which would invoke toJSON a second time if it returns an object.
		if (
			current !== null &&
			(typeof current === "object" || typeof current === "function") &&
			typeof current.toJSON === "function"
		) {
			current = current.toJSON(key);
		}

		if (current === null || typeof current !== "object") {
			return JSON.stringify(current);
		}

		if (ancestors.has(current)) {
			throw new TypeError("Converting circular structure to JSON");
		}

		ancestors.add(current);
		try {
			if (Array.isArray(current)) {
				return (
					"[" +
					Array.from(current, (item, index) => {
						const serialized = serialize(item, String(index));
						return serialized === undefined ? "null" : serialized;
					}).join(",") +
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
