<script setup>
/**
 * ConditionGroupUI - Nested group editor with AND/OR toggle
 */
import { inject } from "vue";
import ConditionNode from "./ConditionNode.vue";

const props = defineProps({
	group: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
});

const emit = defineEmits(["remove"]);

const { addCondition, addGroup, addCollection, removeNode } = inject("conditionActions");
</script>

<template>
	<div class="condition-group-ui p-3 border rounded bg-light">
		<!-- Header -->
		<div class="d-flex justify-content-between align-items-center mb-3">
			<div class="btn-group btn-group-sm">
				<button
					class="btn btn-xs"
					:class="group.op === 'and' ? 'btn-primary' : 'btn-outline-secondary'"
					@click="group.op = 'and'"
				>
					{{ __("AND") }}
				</button>
				<button
					class="btn btn-xs"
					:class="group.op === 'or' ? 'btn-primary' : 'btn-outline-secondary'"
					@click="group.op = 'or'"
				>
					{{ __("OR") }}
				</button>
			</div>
			<div class="d-flex gap-2">
				<button class="btn btn-xs btn-default" @click="addCondition(group)">
					<i class="fa fa-plus"></i>
				</button>
				<button class="btn btn-xs btn-default" @click="addGroup(group)">
					<i class="fa fa-folder-open-o"></i>
				</button>
				<button class="btn btn-xs btn-default" @click="addCollection(group)">
					<i class="fa fa-table"></i>
				</button>
				<button class="btn btn-xs btn-link text-danger" @click="emit('remove')">
					<i class="fa fa-times"></i>
				</button>
			</div>
		</div>

		<!-- Children -->
		<div class="pl-3 border-left border-primary">
			<div v-if="!group.conditions?.length" class="text-muted py-2 text-sm">
				{{ __("Empty group") }}
			</div>
			<div v-for="(node, idx) in group.conditions" :key="node.id || idx" class="mb-2">
				<ConditionNode
					:node="node"
					:index="idx"
					:parentGroup="group"
					:docFields="docFields"
				/>
			</div>
		</div>
	</div>
</template>

<style scoped>
.condition-group-ui {
	background: rgba(0, 0, 0, 0.02);
}
</style>
