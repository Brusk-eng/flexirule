/**
 * Shared client-side predicate for the permission-bypass audit requirement.
 *
 * Keep Rule Builder modal validation and whole-rule prechecks aligned with the
 * backend policy: legacy and current flags are accepted and audit reasons must
 * contain non-whitespace text. The server remains authoritative for access.
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
