import { getOperationFieldOverride as getOperationFieldOverrideFromContract } from "../../core/contracts.js";

/**
 * Normalize the isolated candidate before validation and commit.
 *
 * Use the backend-supplied operation contract (also used by useRuleStore.save_changes)
 * rather than duplicating the version-specific default in the modal save path.
 * Never mutate the live editing draft while validation is awaiting.
 */
export function normalizeCandidateDraft(candidateDraft, options = {}) {
	if (!candidateDraft?.data) return candidateDraft;

	const data = candidateDraft.data;
	const getFieldOverride =
		options.getOperationFieldOverride || getOperationFieldOverrideFromContract;
	const permissionPolicy = getFieldOverride(data.action_type, "ignore_permissions", {
		operation: data.operation,
	});

	// Contracts use defaults for new/unset fields. Preserve an explicit false
	// when editing an existing action; the backend may reject it for this operation,
	// but normalization must not silently mutate a saved user choice.
	if (
		permissionPolicy?.default === 1 &&
		(data.ignore_permissions === undefined ||
			data.ignore_permissions === null ||
			data.ignore_permissions === "")
	) {
		data.ignore_permissions = 1;
	}

	return candidateDraft;
}
