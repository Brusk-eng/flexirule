import { normalizeActionType } from "../../core/contracts";

/**
 * Shared mapper from Action Type (Rule Action value) to VueFlow node type.
 * Keep this as the single mapping source across builder components/store.
 */
export function mapActionTypeToNodeType(actionType) {
	if (!actionType) return "process";
	const type = normalizeActionType(actionType).toLowerCase().trim();

	if (type === "selector") return "selector";
	if (type === "entry action" || type === "start") return "start";
	if (type === "condition") return "condition";
	if (type === "loop") return "loop";
	if (type === "wait") return "wait";
	if (type === "stop") return "stop";
	if (type === "notify") return "notify";
	if (type === "sub-rule") return "sub-rule";
	if (type === "query records") return "query";
	if (type === "document action") return "documentaction";
	if (type === "set value") return "set-value";

	return "process";
}
