/**
 * Shared client-side predicate for the permission-bypass audit requirement.
 *
 * Keep the Rule Builder modal and whole-rule validation aligned with the
 * backend's accepted legacy/current field names and non-empty reason policy.
 * The server remains authoritative for role authorization and execution checks.
 */
const TRUTHY_PERMISSION_FLAGS = [true, 1, "1", "true", "True"];

export function hasPermissionBypass(action = {}) {
	return [action.ignore_permissions, action.skip_permissions].some((value) =>
		TRUTHY_PERMISSION_FLAGS.includes(value)
	);
}

export function requiresPermissionAuditReason(action = {}) {
	return (
		hasPermissionBypass(action) &&
		!String(action.permission_audit_reason ?? "").trim()
	);
}
