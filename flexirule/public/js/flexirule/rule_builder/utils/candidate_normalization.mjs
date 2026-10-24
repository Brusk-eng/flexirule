/**
 * Normalize candidate draft state right before commit in the save lifecycle.
 * Apply operation/version defaults to the isolated candidate without mutating
 * live editing drafts during validation.
 */
export function normalizeCandidateDraft(candidateDraft, options = {}) {
	if (!candidateDraft?.data) return candidateDraft;
	const data = candidateDraft.data;
	const version =
		options.frappeVersion ||
		(typeof window !== "undefined" && window.frappe?.boot?.versions?.frappe);
	const isFrappe15 =
		options.isFrappe15 ?? (typeof version === "string" && /^15(?:\.|$)/.test(version));

	if (
		data.action_type === "Query Records" &&
		data.operation === "Fetch Records" &&
		isFrappe15 &&
		![true, 1, "1"].includes(data.ignore_permissions)
	) {
		data.ignore_permissions = 1;
	}
	return candidateDraft;
}
