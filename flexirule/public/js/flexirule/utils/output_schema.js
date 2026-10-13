/**
 * Normalize metadata for Rule Action.resolved_output_schema.
 *
 * Frappe names requiredness `reqd`. Legacy `mandatory` values are accepted when
 * loading old schemas, then removed from the canonical representation.
 * The optional `source` object is preserved as provenance metadata and must not
 * alter runtime result values or output-key validation.
 */
function normalizeFlag(value) {
	if (value === true || value === 1) return 1;
	return ["1", "true", "yes"].includes(String(value ?? "").trim().toLowerCase()) ? 1 : 0;
}

export function normalizeResolvedOutputSchema(value) {
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

	return schema.map((field) => {
		if (!field || typeof field !== "object" || Array.isArray(field)) return field;
		const { mandatory, ...canonicalField } = field;
		return {
			...canonicalField,
			reqd: normalizeFlag(field.reqd ?? mandatory ?? 0),
		};
	});
}
