import { getOperationFieldOverride as getOperationFieldOverrideFromContract } from "../../core/contracts.js";

/**
 * Normalize the isolated candidate before validation and commit.
 *
 * Reuse the backend-supplied operation contract (the same policy used by
 * useRuleStore.save_changes) instead of duplicating version-specific defaults.
 * Never mutate the live editing draft while a validator is awaiting.
 */
export function normalizeCandidateDraft(candidateDraft, options = {}) {
	if (!candidateDraft?.data) return candidateDraft;

	const data = candidateDraft.data;
	const getFieldOverride =
		options.getOperationFieldOverride || getOperationFieldOverrideFromContract;
	const permissionPolicy = getFieldOverride(data.action_type, "ignore_permissions", {
		operation: data.operation,
	});

	if (permissionPolicy?.default === 1 && ![true, 1, "1"].includes(data.ignore_permissions)) {
		data.ignore_permissions = 1;
	}

	return candidateDraft;
}
