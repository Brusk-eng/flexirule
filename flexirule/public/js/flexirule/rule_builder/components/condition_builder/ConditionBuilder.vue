<script setup>
/**
 * ConditionBuilder - Main container for condition editing
 * Owns the root condition group state and provides methods via inject
 */
import { provide, reactive, ref, computed, watch, onMounted } from "vue";
import { useStore } from "../../store";
import ConditionNode from "./ConditionNode.vue";

const props = defineProps({
	modelValue: { type: Object, default: () => ({ op: "and", conditions: [] }) },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const store = useStore();

// Create a reactive copy of the model
const rootGroup = reactive(JSON.parse(JSON.stringify(props.modelValue)));

// Sync with parent when rootGroup changes
watch(
	rootGroup,
	(newVal) => {
		emit("update:modelValue", JSON.parse(JSON.stringify(newVal)));
	},
	{ deep: true }
);

// Sync from parent when modelValue changes externally
watch(
	() => props.modelValue,
	(newVal) => {
		if (newVal) {
			// Compare JSON strings to detect logical changes
			const currentJSON = JSON.stringify(rootGroup);
			const newJSON = JSON.stringify(newVal);
			
			if (newJSON !== currentJSON) {
				Object.assign(rootGroup, JSON.parse(newJSON));
			}
		}
	},
	{ deep: true }
);

// UUID generator
function uuid() {
	return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
		const r = (Math.random() * 16) | 0;
		return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
	});
}

// Action methods - provided to children via inject
function addCondition(targetGroup, fieldPrefix = "doc") {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		left: { ref: fieldPrefix + "." },
		op: "==",
		right: { value: "" },
	});
}

function addGroup(targetGroup) {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		op: "and",
		conditions: [],
	});
}

function addCollection(targetGroup) {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		op: "any",
		collection: "",
		alias: "row",
		where: { op: "and", conditions: [] },
	});
}

function removeNode(targetGroup, index) {
	if (targetGroup.conditions && targetGroup.conditions[index] !== undefined) {
		targetGroup.conditions.splice(index, 1);
	}
}

// Operator config from backend
const operatorConfig = ref({
	fieldtype_operators: {},
	operator_labels: {},
});

async function loadOperatorConfig() {
	try {
		const result = await frappe.call({
			method: "flexirule.ruleflow.api.get_operator_config",
		});
		if (result.message) {
			operatorConfig.value = result.message;
		}
	} catch (e) {
		console.error("Failed to load operator config:", e);
	}
}

onMounted(loadOperatorConfig);

// Provide actions and config to all descendant components
provide("conditionActions", { addCondition, addGroup, addCollection, removeNode });
provide(
	"docFields",
	computed(() => props.docFields)
);
provide("operatorConfig", operatorConfig);
provide("store", store);
provide("readOnly", computed(() => props.readOnly));
</script>

<template>
	<div class="condition-builder">
		<div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom">
			<div class="btn-group btn-group-sm">
				<button
					class="btn btn-xs"
					:class="rootGroup.op === 'and' ? 'btn-primary' : 'btn-outline-secondary'"
					@click="rootGroup.op = 'and'"
					:disabled="readOnly"
				>
					{{ __("AND") }}
				</button>
				<button
					class="btn btn-xs"
					:class="rootGroup.op === 'or' ? 'btn-primary' : 'btn-outline-secondary'"
					@click="rootGroup.op = 'or'"
					:disabled="readOnly"
				>
					{{ __("OR") }}
				</button>
			</div>
			<div class="d-flex gap-2" v-if="!readOnly">
				<button class="btn btn-xs btn-default" @click="addCondition(rootGroup)">
					<i class="fa fa-plus"></i> {{ __("Condition") }}
				</button>
				<button class="btn btn-xs btn-default" @click="addGroup(rootGroup)">
					<i class="fa fa-folder-open-o"></i> {{ __("Group") }}
				</button>
				<button class="btn btn-xs btn-default" @click="addCollection(rootGroup)">
					<i class="fa fa-table"></i> {{ __("Collection") }}
				</button>
			</div>
		</div>

		<div
			v-if="!rootGroup.conditions?.length"
			class="text-muted text-center py-4 border-dashed rounded"
		>
			{{ __("No conditions. Click buttons above to add.") }}
		</div>

		<div v-for="(node, idx) in rootGroup.conditions" :key="node.id || idx" class="mb-3">
			<ConditionNode
				:node="node"
				:index="idx"
				:parentGroup="rootGroup"
				:docFields="docFields"
				:readOnly="readOnly"
			/>
		</div>
	</div>
</template>

<style scoped>
.condition-builder {
	padding: 16px;
	background: var(--bg-light-gray, #f9f9f9);
	border-radius: 8px;
}
.border-dashed {
	border: 2px dashed var(--border-color);
}
</style>
