/**
 * useAutoLayout — Dagre-based auto-layout for the rule graph.
 *
 * Phase 5: Provides top-down (TB) or left-right (LR) auto-layout
 * using dagre's layered graph algorithm.
 *
 * Usage:
 *   const { layoutGraph, insertBetween } = useAutoLayout()
 *   const layoutedNodes = layoutGraph(nodes, edges, 'TB')
 */

/**
 * Load dagre dynamically. If dagre is not available as a module,
 * falls back to a simple grid layout.
 */
function getDagre() {
	try {
		// dagre may be available via node_modules or global
		if (window.dagre) return window.dagre;
		// Try dynamic import path (bundled apps)
		return require("dagre");
	} catch {
		return null;
	}
}

const NODE_WIDTH = 260;
const NODE_HEIGHT = 80;
const DECISION_HEIGHT = 100;
const NODE_SEP = 60; // Horizontal spacing between nodes
const RANK_SEP = 100; // Vertical spacing between ranks

export function useAutoLayout() {
	/**
	 * Apply dagre layout to the graph.
	 *
	 * @param {Array} nodes - VueFlow nodes
	 * @param {Array} edges - VueFlow edges
	 * @param {string} direction - 'TB' (top-bottom) or 'LR' (left-right)
	 * @returns {Array} Nodes with updated positions
	 */
	function layoutGraph(nodes, edges, direction = "TB") {
		const dagre = getDagre();

		if (!dagre) {
			// Fallback: simple vertical stack layout
			return _fallbackLayout(nodes, edges, direction);
		}

		const g = new dagre.graphlib.Graph();
		g.setGraph({
			rankdir: direction,
			nodesep: NODE_SEP,
			ranksep: RANK_SEP,
			marginx: 40,
			marginy: 40,
		});
		g.setDefaultEdgeLabel(() => ({}));

		nodes.forEach((node) => {
			const isDecision =
				node.type === "condition" ||
				node.data?.action_type === "Condition" ||
				node.data?.action_type === "Switch";
			const height = isDecision ? DECISION_HEIGHT : NODE_HEIGHT;
			g.setNode(node.id, { width: NODE_WIDTH, height });
		});

		edges.forEach((edge) => {
			if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
				g.setEdge(edge.source, edge.target);
			}
		});

		dagre.layout(g);

		return nodes.map((node) => {
			const dagreNode = g.node(node.id);
			if (!dagreNode) return node;

			return {
				...node,
				position: {
					x: dagreNode.x - NODE_WIDTH / 2,
					y:
						dagreNode.y -
						(node.type === "condition" ? DECISION_HEIGHT : NODE_HEIGHT) / 2,
				},
			};
		});
	}

	/**
	 * Insert a node between two connected nodes.
	 * Splits the edge source→target into source→newNode→target.
	 *
	 * @param {string} sourceId
	 * @param {string} targetId
	 * @param {string} newNodeId
	 * @param {Array} edges - Current edges
	 * @returns {Array} Updated edges
	 */
	function insertBetween(sourceId, targetId, newNodeId, edges) {
		const oldEdge = edges.find((e) => e.source === sourceId && e.target === targetId);
		if (!oldEdge) return edges;

		const filteredEdges = edges.filter((e) => e.id !== oldEdge.id);

		return [
			...filteredEdges,
			{
				id: `e-${sourceId}-${newNodeId}-${oldEdge.sourceHandle || "default"}`,
				source: sourceId,
				target: newNodeId,
				sourceHandle: oldEdge.sourceHandle,
			},
			{
				id: `e-${newNodeId}-${targetId}-default`,
				source: newNodeId,
				target: targetId,
				sourceHandle: "default",
			},
		];
	}

	/**
	 * Fallback layout: simple vertical/horizontal stacking
	 * when dagre is not available.
	 */
	function _fallbackLayout(nodes, edges, direction) {
		// Build adjacency for BFS ordering
		const adj = new Map();
		edges.forEach((e) => {
			if (!adj.has(e.source)) adj.set(e.source, []);
			adj.get(e.source).push(e.target);
		});

		// BFS from start node
		const startNode = nodes.find(
			(n) => n.id === "start" || n.id === "root" || n.type === "start"
		);
		const ordered = [];
		const visited = new Set();
		const queue = [startNode?.id || nodes[0]?.id].filter(Boolean);

		while (queue.length > 0) {
			const id = queue.shift();
			if (visited.has(id)) continue;
			visited.add(id);
			ordered.push(id);
			(adj.get(id) || []).forEach((childId) => {
				if (!visited.has(childId)) queue.push(childId);
			});
		}

		// Add any unvisited nodes
		nodes.forEach((n) => {
			if (!visited.has(n.id)) ordered.push(n.id);
		});

		const isVertical = direction === "TB";
		const spacing = isVertical ? RANK_SEP + NODE_HEIGHT : RANK_SEP + NODE_WIDTH;
		const offset = 40;

		return nodes.map((node) => {
			const idx = ordered.indexOf(node.id);
			const pos = idx === -1 ? 0 : idx;

			return {
				...node,
				position: {
					x: isVertical ? 250 : offset + pos * spacing,
					y: isVertical ? offset + pos * spacing : 250,
				},
			};
		});
	}

	return {
		layoutGraph,
		insertBetween,
		NODE_WIDTH,
		NODE_HEIGHT,
	};
}
