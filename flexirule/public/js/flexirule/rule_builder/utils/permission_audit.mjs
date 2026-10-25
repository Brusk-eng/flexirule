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

function getPermissionAuditReason(action = {}) {
	if (action.permission_audit_reason) return String(action.permission_audit_reason).trim();

	let config = action.config;
	if (typeof config === "string") {
		try {
			config = JSON.parse(config);
		} catch {
			return "";
		}
	}

	if (!config || typeof config !== "object" || Array.isArray(config)) return "";
	return String(config.permission_audit_reason ?? "").trim();
}

export function requiresPermissionAuditReason(action = {}) {
	return hasPermissionBypass(action) && !getPermissionAuditReason(action);
}
