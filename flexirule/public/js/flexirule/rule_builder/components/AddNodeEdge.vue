<script setup>
import { computed } from "vue";
import { BaseEdge, getSmoothStepPath, EdgeLabelRenderer } from "@vue-flow/core";

const props = defineProps({
	id: {
		type: String,
		required: true,
	},
	source: {
		type: String,
		required: true,
	},
	target: {
		type: String,
		required: true,
	},
	sourceX: {
		type: Number,
		required: true,
	},
	sourceY: {
		type: Number,
		required: true,
	},
	targetX: {
		type: Number,
		required: true,
	},
	targetY: {
		type: Number,
		required: true,
	},
	sourcePosition: {
		type: String,
		required: true,
	},
	targetPosition: {
		type: String,
		required: true,
	},
	data: {
		type: Object,
		required: false,
	},
	markerEnd: {
		type: String,
		required: false,
	},
	style: {
		type: Object,
		required: false,
	},
});

const emit = defineEmits(["insert-node"]);

const path = computed(() =>
	getSmoothStepPath({
		sourceX: props.sourceX,
		sourceY: props.sourceY,
		sourcePosition: props.sourcePosition,
		targetX: props.targetX,
		targetY: props.targetY,
		targetPosition: props.targetPosition,
	})
);

function onAddClick(event) {
	event.stopPropagation();
	emit("insert-node", { edgeId: props.id });
}
</script>

<template>
	<BaseEdge :id="id" :style="style" :path="path[0]" :marker-end="markerEnd" />
	<EdgeLabelRenderer>
		<div
			:style="{
				pointerEvents: 'all',
				position: 'absolute',
				transform: `translate(-50%, -50%) translate(${path[1]}px,${path[2]}px)`,
			}"
			class="nodrag nopan"
		>
			<button class="edge-add-button" @click="onAddClick" :title="__('Insert Action')">
				<i class="fa fa-plus"></i>
			</button>
		</div>
	</EdgeLabelRenderer>
</template>

<style scoped>
.edge-add-button {
	width: 20px;
	height: 20px;
	background: #fff;
	border: 1px solid var(--border-color, #dfe3e8);
	border-radius: 50%;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
	color: var(--text-muted);
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	transition: all 0.2s ease;
	z-index: 10;
}

.edge-add-button:hover {
	transform: scale(1.2);
	border-color: var(--primary);
	color: var(--primary);
	box-shadow: 0 2px 5px rgba(0, 0, 0, 0.15);
}

.edge-add-button i {
	pointer-events: none;
}
</style>
