import { normalizeActionType } from "../../core/contracts";

/**
 * Shared mapper from Action Type (Rule Action value) to VueFlow node type.
 * Keep this as the single mapping source across builder components/store.
 */
export function mapActionTypeToNodeType(actionType) {
	if (!actionType) return "process";
	const normalized = String(normalizeActionType(actionType) || "")
		.toLowerCase()
		.replace(/[_-]+/g, " ")
		.replace(/\s+/g, " ")
		.trim();
	const compact = normalized.replace(/\s+/g, "");

	if (compact === "selector") return "selector";
	if (compact === "entryaction" || compact === "start") return "start";
	if (compact === "condition") return "condition";
	if (compact === "loop") return "loop";
	if (compact === "wait") return "wait";
	if (compact === "stop") return "stop";
	if (compact === "raiseerror") return "raise-error";
	if (compact === "notify") return "notify";
	if (compact === "subrule") return "sub-rule";
	if (compact === "queryrecords") return "query";
	if (compact === "documentaction") return "documentaction";
	if (compact === "assignment" || compact === "setvalue") return "assignment";

	return "process";
}
