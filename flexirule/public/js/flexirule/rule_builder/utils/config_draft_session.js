import { deepClone } from "./serialization.js";
import { stableStringify } from "./stable_serialization.mjs";

/**
 * Return the in-session draft for a node, creating it on first visit.
 *
 * A source-data signature is kept separately from the draft baseline because
 * mounted panels may initialize defaults in the draft after it is created.
 * Comparing against the draft baseline would mistake those defaults for an
 * external graph change.
 */
export function getOrCreateConfigDraftEntry(entries, sourceNode) {
	if (!sourceNode?.id) return null;

	const sourceDataSignature = stableStringify(sourceNode.data || {});
	const existing = entries.get(sourceNode.id);

	if (existing) {
		const sourceIsUnchanged = sourceDataSignature === existing.sourceDataSignature;
		if (sourceIsUnchanged) {
			existing.sourceNode = sourceNode;
			existing.isStale = false;
			return existing;
		}

		if (isConfigDraftEntryDirty(existing)) {
			// Preserve the user's draft, but don't allow it to overwrite newer
			// graph data. The editor can explain the conflict on Save.
			existing.isStale = true;
			return existing;
		}

		// There are no local edits to preserve, so follow the newer graph state.
		entries.delete(sourceNode.id);
	}

	const entry = {
		nodeId: sourceNode.id,
		sourceNode,
		sourceDataSignature,
		draftNode: deepClone(sourceNode),
		initialDraftState: null,
		isStale: false,
	};
	entries.set(sourceNode.id, entry);
	// Return the map's canonical value. Vue's reactive Map wraps stored values
	// when read; returning that same value keeps strict identity guards reliable.
	return entries.get(sourceNode.id);
}

export function isConfigDraftEntryDirty(entry) {
	if (!entry || entry.initialDraftState == null || !entry.draftNode) return false;
	return stableStringify(entry.draftNode.data || {}) !== entry.initialDraftState;
}

export function getDirtyConfigDraftEntries(entries, exceptNodeId = null) {
	return [...entries.values()].filter(
		(entry) => entry.nodeId !== exceptNodeId && isConfigDraftEntryDirty(entry)
	);
}
