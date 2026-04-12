import dagre from "dagre";
import { useVueFlow } from "@vue-flow/core";

export function useRuleGraph() {
	const { nodes, edges, setNodes, setEdges, fitView } = useVueFlow();

	const layoutGraph = (direction = "TB") => {
		const dagreGraph = new dagre.graphlib.Graph();
		dagreGraph.setDefaultEdgeLabel(() => ({}));

		// Top to Bottom layout by default to match Salesforce
		dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 100 });

		nodes.value.forEach((node) => {
			// standardizing node width/height for dagre layout
			dagreGraph.setNode(node.id, { width: 300, height: 120 });
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
