<template>
	<div class="tree-leaf">
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
defineProps({
	node: { type: Object, required: true },
	context: { type: Object, default: () => ({ scopes: [], path: [] }) },
	index: { type: Number, required: true },
	parent: { type: Object, required: true },
	readOnly: Boolean,
});
defineEmits(["remove"]);
</script>
<style scoped>
.tree-leaf {
	display: grid;
	grid-template-columns: minmax(0, 1fr) 32px;
	gap: var(--fxr-space-2);
	align-items: stretch;
	width: 100%;
	min-width: 0;
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
