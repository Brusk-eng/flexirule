/**
 * Normalize metadata for Rule Action.resolved_output_schema.
 *
 * Frappe names requiredness \`reqd\`. Legacy \`mandatory\` values are accepted when
 * loading old schemas, then removed from the canonical representation.
 * Every canonical field has a provenance object with a \`kind\`. Missing lineage
 * is marked \`unknown\` unless a calling context can identify it as \`manual\`.
 * Metadata never changes runtime result values or output-key validation.
 */
function normalizeFlag(value) {
	if (value === true || value === 1) return 1;
	return ["1", "true", "yes"].includes(
		String(value ?? "")
			.trim()
			.toLowerCase()
	)
		? 1
		: 0;
}

function normalizeSourceKind(value, fallbackSourceKind = "unknown") {
	const fallback =
		typeof fallbackSourceKind === "string" && fallbackSourceKind.trim()
			? fallbackSourceKind.trim()
			: "unknown";
	return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

export function normalizeResolvedOutputSource(source, fallbackSourceKind = "unknown") {
	if (!source || typeof source !== "object" || Array.isArray(source)) {
		return { kind: normalizeSourceKind(null, fallbackSourceKind) };
	}

	return {
		...source,
		kind: normalizeSourceKind(source.kind, fallbackSourceKind),
	};
}

export function normalizeResolvedOutputField(field, options = {}) {
	if (!field || typeof field !== "object" || Array.isArray(field)) return field;

	const { fallbackSourceKind = "unknown" } = options || {};
	const canonicalField = { ...field };
	delete canonicalField.mandatory;

	return {
		...canonicalField,
		reqd: normalizeFlag(field.reqd ?? field.mandatory ?? 0),
		source: normalizeResolvedOutputSource(field.source, fallbackSourceKind),
	};
}

export function normalizeResolvedOutputSchema(value, options = {}) {
	let schema = value;
	if (typeof schema === "string") {
		try {
			schema = JSON.parse(schema);
		} catch {
			// Preserve an in-progress manual JSON edit.
			return value;
		}
	}
	if (schema == null) return [];
	if (!Array.isArray(schema)) return schema;

	return schema.map((field) => normalizeResolvedOutputField(field, options));
}
