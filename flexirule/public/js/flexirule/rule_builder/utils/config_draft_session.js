import { stableStringify } from "./stable_serialization.mjs";

/**
 * Clone graph-node configuration data without importing Vue. This module is
 * also exercised by the repository's dependency-free Node unit-test job.
 */
function cloneDraftValue(value, seen = new WeakMap()) {
	if (value === null || typeof value !== "object") return value;
	if (seen.has(value)) return seen.get(value);

	if (value instanceof Date) return new Date(value.getTime());
	if (value instanceof RegExp) return new RegExp(value.source, value.flags);

	if (Array.isArray(value)) {
		const clone = [];
		seen.set(value, clone);
		for (const item of value) clone.push(cloneDraftValue(item, seen));
		return clone;
	}

	if (value instanceof Map) {
		const clone = new Map();
		seen.set(value, clone);
		value.forEach((item, key) => {
			clone.set(cloneDraftValue(key, seen), cloneDraftValue(item, seen));
		});
		return clone;
	}

	if (value instanceof Set) {
		const clone = new Set();
		seen.set(value, clone);
		value.forEach((item) => clone.add(cloneDraftValue(item, seen)));
		return clone;
	}

	const prototype = Object.getPrototypeOf(value);
	const clone = Object.create(prototype);
	seen.set(value, clone);
	for (const key of Object.keys(value)) {
		clone[key] = cloneDraftValue(value[key], seen);
	}
	return clone;
}

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
		draftNode: cloneDraftValue(sourceNode),
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
