/**
 * Pure functions for visual layout payload formatting and layout merging.
 */

/**
 * Formats visual_data payload for persistence in Rule.visual_data.
 * Strictly retains layout and positioning metadata; excludes complete action data
 * and redundant type/label fields for action nodes.
 *
 * @param {Array} nodes
 * @param {Array} edges
 * @param {string|null} layoutDirection
 * @param {string|null} uiLayoutPreference
 * @returns {Array}
 */
export function formatVisualDataPayload(
	nodes,
	edges,
	layoutDirection = null,
	uiLayoutPreference = null
) {
	const nodePayload = (nodes || []).map((node) => {
		const payload = {
			id: node.id,
			position: {
				x: Math.round(node.position?.x || 0),
				y: Math.round(node.position?.y || 0),
			},
			direction: layoutDirection || node.direction || null,
		};
		if (node.is_visual_only) {
			payload.is_visual_only = true;
			payload.type = node.type;
			payload.label = node.label;
		}
		return payload;
	});

	const metaPayload = {
		type: "ui_preferences",
		layout: layoutDirection || uiLayoutPreference || "LR",
	};

	const edgePayload = (edges || []).map((edge) => ({
		id: edge.id,
		source: edge.source,
		target: edge.target,
		sourceHandle: edge.sourceHandle || "default",
		targetHandle: edge.targetHandle || null,
	}));

	return [...nodePayload, ...edgePayload, metaPayload];
}

/**
 * Merges visual layout metadata (positions, directions, edges) onto current nodes/edges.
 * Action node data and labels are never overwritten from visual_data.
 * Stale orphan action nodes in visual_data are ignored.
 *
 * @param {Array} currentNodes
 * @param {Array} currentEdges
 * @param {Array} visualData
 * @returns {{ nodes: Array, edges: Array, layoutPreference: string|null }}
 */
export function mergeVisualLayout(currentNodes, currentEdges, visualData) {
	const visualNodes = new Map(
		(visualData || []).filter((el) => el?.position).map((node) => [node.id, node])
	);
	const visualEdges = new Map(
		(visualData || [])
			.filter((el) => el?.source)
			.map((edge) => [
				`${edge.source}:${edge.target}:${edge.sourceHandle || "default"}`,
				edge,
			])
	);

	const uiPreference =
		(visualData || []).find((el) => el?.type === "ui_preferences")?.layout || null;

	const seenNodeIds = new Set();
	const mergedNodes = (currentNodes || []).map((node) => {
		seenNodeIds.add(node.id);
		const visualNode = visualNodes.get(node.id);
		if (!visualNode) return node;

		const {
			position,
			type: _visualType,
			label: _visualLabel,
			id: _visualId,
			data: _visualData,
			...visualNodeMeta
		} = visualNode;

		const direction = visualNode.direction || visualNode.layout_direction || null;
		return {
			...node,
			...visualNodeMeta,
			position: position || node.position,
			direction: direction || node.direction,
			data: { ...(node.data || {}) },
			type: node.type,
			label: node.label,
		};
	});

	// Add orphaned visual nodes ONLY if explicitly marked as visual-only
	visualNodes.forEach((vNode, id) => {
		if (!seenNodeIds.has(id)) {
			if (vNode.is_visual_only) {
				mergedNodes.push({
					...vNode,
					data: { ...(vNode.data || {}) },
				});
				seenNodeIds.add(id);
			}
		}
	});

	const seenEdgeKeys = new Set();
	const mergedEdges = (currentEdges || []).map((edge) => {
		const key = `${edge.source}:${edge.target}:${edge.sourceHandle || "default"}`;
		seenEdgeKeys.add(key);
		const visualEdge = visualEdges.get(key);
		if (!visualEdge) return edge;

		const {
			id: _vId,
			source: _vSource,
			target: _vTarget,
			sourceHandle: _vSourceHandle,
			data: _vData,
			...visualEdgeMeta
		} = visualEdge;

		return { ...edge, ...visualEdgeMeta, type: "add" };
	});

	// Add orphaned edges with valid endpoints
	visualEdges.forEach((vEdge, key) => {
		if (!seenEdgeKeys.has(key)) {
			if (seenNodeIds.has(vEdge.source) && seenNodeIds.has(vEdge.target)) {
				mergedEdges.push({ ...vEdge, type: "add" });
				seenEdgeKeys.add(key);
			}
		}
	});

	return {
		nodes: mergedNodes,
		edges: mergedEdges,
		layoutPreference: uiPreference,
	};
}
