import { unref } from "vue";
import dagre from "dagre";
import { useVueFlow } from "@vue-flow/core";
import { useGraphStore } from "../stores/useGraphStore";

/**
 * useGraphManager wrapper
 * Handles Vue Flow specific logic, Dagre auto-layout, and edge splicing
 */
export function useGraphManager() {
	const graphStore = useGraphStore();
	const { getNodes, getEdges, addEdges, removeEdges, fitView, updateEdge } = useVueFlow();

	/**
	 * Compute and apply dagre auto-layout (Top to Bottom)
	 */
	async function layoutGraph(direction = "TB") {
		const nodes = getNodes.value;
		const edges = getEdges.value;

		if (!nodes.length) return;

		const dagreGraph = new dagre.graphlib.Graph();
		dagreGraph.setDefaultEdgeLabel(() => ({}));

		const isHorizontal = direction === "LR";
		dagreGraph.setGraph({
			rankdir: direction,
			ranker: "network-simplex",
			nodesep: 60,
			edgesep: 30,
			ranksep: 100,
		});

		nodes.forEach((node) => {
			// Vue Flow nodes usually have dimensions, default to 250x100 if none
			const width = node.dimensions?.width || 250;
			const height = node.dimensions?.height || 100;
			dagreGraph.setNode(node.id, { width, height });
		});

		edges.forEach((edge) => {
			dagreGraph.setEdge(edge.source, edge.target);
		});

		dagre.layout(dagreGraph);

		nodes.forEach((node) => {
			const nodeWithPosition = dagreGraph.node(node.id);
			node.targetPosition = isHorizontal ? "left" : "top";
			node.sourcePosition = isHorizontal ? "right" : "bottom";

			// Shift position by center calculation since Dagre gives center points
			node.position = {
				x: nodeWithPosition.x - (node.dimensions?.width || 250) / 2,
				y: nodeWithPosition.y - (node.dimensions?.height || 100) / 2,
			};
		});

		// Trigger reactive update
		graphStore.nodes = [...nodes];

		setTimeout(() => {
			fitView({ padding: 0.1, duration: 500 });
		}, 50);
	}

	/**
	 * Splice a new Action Node into the selected edge
	 *
	 * Edge A -> B becomes A -> NewNode -> B
	 */
	async function insertNodeOnEdge(edgeId, actionType, label, options = {}) {
		const edge = getEdges.value.find((e) => e.id === edgeId);
		if (!edge) return null;

		const sourceId = edge.source;
		const targetId = edge.target;
		const sourceHandle = edge.sourceHandle;

		// Create new Node definition from GraphStore defaults
		const newNodeData = graphStore.get_default_node_data(actionType, label);

		// Link New Node -> Original Target
		newNodeData.next_step_if_true = targetId;

		// Apply any overrides from config modal
		if (options.process_name) newNodeData.process_name = options.process_name;
		if (options.operation) newNodeData.operation = options.operation;

		const newNode = {
			id: newNodeData.action_id,
			type: options.nodeType || "actionType",
			position: { x: 0, y: 0 }, // Dagre will position
			label: newNodeData.action_label,
			data: newNodeData,
		};

		// Add node
		graphStore.nodes.push(newNode);

		// Update Original Source Node to point to New Node
		const sourceNodeStore = graphStore.nodes.find((n) => n.id === sourceId);
		if (sourceNodeStore && sourceNodeStore.data) {
			if (sourceHandle === "false") {
				sourceNodeStore.data.next_step_if_false = newNode.id;
			} else {
				sourceNodeStore.data.next_step_if_true = newNode.id;
			}
		}

		// Re-sync edges array completely to reflect next_step links via store graph sync
		// Or simply manually build the replaced edges:
		graphStore.delete_edge(edgeId, false);

		graphStore.edges.push({
			id: `e-${sourceId}-${newNode.id}-${sourceHandle || "default"}`,
			source: sourceId,
			target: newNode.id,
			sourceHandle: sourceHandle || "default",
		});

		graphStore.edges.push({
			id: `e-${newNode.id}-${targetId}-true`,
			source: newNode.id,
			target: targetId,
			sourceHandle: "true", // Assuming new node true handle proceeds
		});

		// Layout automatically
		await layoutGraph("TB");

		return newNode;
	}

	return {
		layoutGraph,
		insertNodeOnEdge,
	};
}
