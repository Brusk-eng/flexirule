/**
 * Domain stores barrel export.
 *
 * Architecture (following Frappe builder patterns):
 *
 *   useRuleStore    — Rule document lifecycle, fetch/save, processes
 *     ├── useGraphStore   — Nodes, edges, topology, operations
 *     ├── useMetaStore    — DocType metadata cache
 *     ├── useHistoryStore — Undo/redo
 *     └── useUIStore      — Selection, modals, test visualization
 */

export { useRuleStore } from "./useRuleStore";
export { useGraphStore } from "./useGraphStore";
export { useMetaStore } from "./useMetaStore";
export { useHistoryStore } from "./useHistoryStore";
export { useUIStore } from "./useUIStore";
