<template>
	<div
		class="tree-leaf"
		:class="{ 'is-dragging': dragging }"
		:draggable="!readOnly"
		@pointerdown.capture="rememberDragOrigin"
		@dragstart="startDrag"
		@dragend="endDrag"
	>
		<div class="tree-leaf__content">
			<slot :node="node" :context="context" :index="index" :parent="parent" />
		</div>
		<button
			v-if="!readOnly"
			type="button"
			class="fxr-btn fxr-btn--icon fxr-btn--danger tree-leaf__remove"
			:title="__('Remove')"
			@click="$emit('remove')"
		>
			<i class="fa fa-trash"></i>
		</button>
	</div>
</template>
<script setup>
import { inject, ref } from "vue";

const props = defineProps({
	node: { type: Object, required: true },
	context: { type: Object, default: () => ({ scopes: [], path: [] }) },
	index: { type: Number, required: true },
	parent: { type: Object, required: true },
	readOnly: Boolean,
});
defineEmits(["remove"]);

const api = inject("treeBuilderContext", null);
const dragging = ref(false);
let dragOriginWasInteractive = false;

const interactiveSelector = [
	"button",
	"input",
	"select",
	"textarea",
	"option",
	"a",
	'[contenteditable="true"]',
	'[role="button"]',
	'[role="combobox"]',
	"[data-no-drag]",
	".combobox-container",
	".flex-value-control-button",
	".form-control",
].join(", ");

function rememberDragOrigin(event) {
	const target = event.target;
	dragOriginWasInteractive =
		target instanceof Element && Boolean(target.closest(interactiveSelector));
}

function startDrag(event) {
	if (props.readOnly || dragOriginWasInteractive) {
		event.preventDefault();
		dragOriginWasInteractive = false;
		return;
	}

	dragging.value = true;
	api?.beginDrag(props.node.id);
	if (event.dataTransfer) {
		event.dataTransfer.effectAllowed = "move";
		event.dataTransfer.setData("text/plain", props.node.id || "");
	}
}

function endDrag() {
	dragging.value = false;
	dragOriginWasInteractive = false;
	api?.endDrag();
}
</script>
<style scoped>
.tree-leaf {
	display: grid;
	grid-template-columns: minmax(0, 1fr) 32px;
	gap: var(--fxr-space-2);
	align-items: stretch;
	width: 100%;
	min-width: 0;
	cursor: grab;
}
.tree-leaf.is-dragging {
	cursor: grabbing;
	opacity: 0.82;
}
.tree-leaf__content {
	width: 100%;
	min-width: 0;
}
.tree-leaf__remove {
	display: inline-flex;
	align-self: center;
	align-items: center;
	justify-content: center;
	width: 30px;
	min-width: 30px;
	height: var(--fxr-input-height);
	margin: 0;
	padding: 0;
	border: 1px solid transparent;
	border-radius: var(--fxr-radius-md);
	background: transparent;
	color: var(--fxr-text-danger);
	transition: background-color var(--fxr-transition-fast), border-color var(--fxr-transition-fast);
}
.tree-leaf__remove:hover,
.tree-leaf__remove:focus-visible {
	border-color: var(--fxr-border-danger);
	background: var(--fxr-bg-danger);
	color: var(--fxr-text-danger);
}
</style>
