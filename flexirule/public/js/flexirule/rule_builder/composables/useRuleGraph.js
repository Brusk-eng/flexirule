import dagre from "dagre";
import { useVueFlow } from "@vue-flow/core";

export function useRuleGraph() {
	const { nodes, edges, setNodes, setEdges, fitView } = useVueFlow();

	const layoutGraph = (direction = "TB") => {
		const dagreGraph = new dagre.graphlib.Graph();
		dagreGraph.setDefaultEdgeLabel(() => ({}));

		const isHorizontal = direction === "LR";
		dagreGraph.setGraph({
			rankdir: direction,
			nodesep: isHorizontal ? 60 : 80,
			ranksep: isHorizontal ? 100 : 120,
			marginx: 40,
			marginy: 40,
		});

		nodes.value.forEach((node) => {
			// Using consistent dimensions to ensure perfect center alignment
			dagreGraph.setNode(node.id, { width: 280, height: 100 });
		});

		edges.value.forEach((edge) => {
			dagreGraph.setEdge(edge.source, edge.target);
		});

		dagre.layout(dagreGraph);

		const layoutedNodes = nodes.value.map((node) => {
			const nodeWithPosition = dagreGraph.node(node.id);
			return {
				...node,
				position: {
					x: nodeWithPosition.x - 150, // shift back by half width
					y: nodeWithPosition.y - 60, // shift back by half height
				},
				// Reset source/target handles to match direction if needed
				sourcePosition: isHorizontal ? "right" : "bottom",
				targetPosition: isHorizontal ? "left" : "top",
			};
		});

		setNodes(layoutedNodes);

		setTimeout(() => {
			fitView({ padding: 0.2, duration: 500 });
		}, 100);
	};

	return {
		layoutGraph,
	};
}
