import { stableStringify } from "./stable_serialization.mjs";

/**
 * Compare persisted graph state using the same canonical JSON semantics across
 * modal drafts and the page-level graph store.
 */
export function hasGraphStateChanged(initialState, currentSnapshot) {
	if (initialState === null || initialState === undefined) return false;
	return initialState !== stableStringify(currentSnapshot);
}

/**
 * Decide whether an explicit user commit should create a dirty graph state.
 * Unlike automatic graph mutations, an explicit commit intentionally ignores
 * transient initialization/layout flags; the store still suppresses those
 * flags in its automatic mark_dirty() path.
 */
export function shouldRecordExplicitGraphCommit({ isReadOnly, initialState, currentSnapshot }) {
	if (isReadOnly) return false;
	if (initialState === null || initialState === undefined) return true;
	return hasGraphStateChanged(initialState, currentSnapshot);
}
