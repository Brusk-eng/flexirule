<script setup>
import { ref, computed, onMounted } from "vue";
import { Handle, Position } from "@vue-flow/core";
import {
	ACTION_TYPE_CONTRACT,
	RELEASE_DISABLED_ACTION_TYPES,
	getActionTypeOptions,
} from "../../../core/contracts";
import { useStore } from "../../store";

const props = defineProps(["data", "label", "id", "selected"]);
const store = useStore();

const selectedType = ref("Process");
const customLabel = ref("");
const searchQuery = ref("");
const showResults = ref(false);
const processOperations = ref([]);

// Fuzzy match helper — matches each query word independently against the text
function fuzzyMatch(text, query) {
	if (!query) return true;
	const lowerText = text.toLowerCase();
	const words = query.toLowerCase().split(/\s+/).filter(Boolean);
	return words.every((w) => lowerText.includes(w));
}

// Categorize action types into groups for display
const ACTION_CATEGORIES = {
	"Control Flow": ["Condition", "Stop", "Wait", "Sub-Rule"],
	"Data Actions": ["Set Value", "Query Records", "Document Action"],
	Notifications: ["Raise Error", "Notify"],
	Processes: ["Process"],
};

const actionTypes = computed(() => {
	const meta = frappe.get_meta("Rule Action");
	if (!meta || !meta.fields) return [];

	const typeField = meta.fields.find((f) => f.fieldname === "action_type");
	if (!typeField || !typeField.options) return [];

	return typeField.options
		.split("\n")
		.filter(
			(t) => t && t !== "Entry Action" && t !== "Start" && getActionTypeOptions().includes(t)
		)
		.map((t) => {
			const contract = ACTION_TYPE_CONTRACT[t] || {};
			return {
				label: __(t),
				value: t,
				actionType: t,
				icon: contract.css?.icon || "fa fa-cog",
				color: contract.css?.color || "#6b7280",
				description: contract.description || "",
				category:
					Object.entries(ACTION_CATEGORIES).find(([, types]) => types.includes(t))?.[0] ||
					__("Other"),
			};
		});
});

// Filtered results for fuzzy search
const filteredResults = computed(() => {
	const q = searchQuery.value;
	const results = [];

	// 1. Filter action types
	const matchingActions = actionTypes.value.filter(
		(t) => fuzzyMatch(t.label, q) || fuzzyMatch(t.description, q) || fuzzyMatch(t.value, q)
	);

	// Group by category
	const grouped = {};
	matchingActions.forEach((a) => {
		if (!grouped[a.category]) grouped[a.category] = [];
		grouped[a.category].push(a);
	});

	Object.entries(grouped).forEach(([cat, items]) => {
		results.push({ type: "header", label: cat });
		items.forEach((item) => results.push({ type: "action", ...item }));
	});

	// 2. Filter process operations
	const matchingOps = processOperations.value.filter(
		(op) =>
			fuzzyMatch(op.label, q) ||
			fuzzyMatch(op.process, q) ||
			fuzzyMatch(op.description || "", q)
	);

	if (matchingOps.length) {
		results.push({ type: "header", label: __("Process Operations") });
		matchingOps.forEach((op) =>
			results.push({
				type: "process_op",
				label: `${op.process} → ${op.label}`,
				value: "Process",
				process_name: op.process,
				operation: op.operation,
				icon: "fa fa-cog",
				color: "#8b5cf6",
				description: op.description || "",
			})
		);
	}

	return results;
});

async function loadProcessOperations() {
	try {
		const res = await frappe.call({
			method: "flexirule.ruleflow.api.get_all_process_operations",
		});
		processOperations.value = res.message || [];
	} catch (e) {
		processOperations.value = [];
	}
}

function selectItem(item) {
	if (item.type === "header") return;
	selectedType.value = item.value;
	if (item.type === "process_op") {
		// Pre-fill process_name and operation
		selectedType.value = "Process";
		// Store for later use in onCreate
		selectedType._process_name = item.process_name;
		selectedType._operation = item.operation;
	}
	searchQuery.value = item.label;
	showResults.value = false;
}

function onSearchFocus() {
	showResults.value = true;
}

function onSearchBlur() {
	// Delay to allow click on results
	setTimeout(() => {
		showResults.value = false;
	}, 200);
}

function onCreate() {
	const typeConfig = actionTypes.value.find((t) => t.value === selectedType.value);
	const nodeIndex = store.nodes.findIndex((n) => n.id === props.id);

	if (nodeIndex === -1) return;

	const action_type = selectedType.value;
	const label = customLabel.value || searchQuery.value || selectedType.value;
	// Map Action Type to VueFlow node type
	const nodeType = action_type
		.toLowerCase()
		.replace(/ records| docs/g, (m) =>
			m.includes("query") ? "query" : m.includes("aggregate") ? "aggregate" : "createdoc"
		);

	const nodeData = store.get_default_node_data(action_type.toLowerCase(), label);
	const suggestedParentId = store.nodes[nodeIndex].data?.suggested_parent_id;
	const suggestedSourceHandle = store.nodes[nodeIndex].data?.suggested_source_handle || "default";

	// Pre-fill process data if selected from process operations
	if (selectedType._process_name) {
		nodeData.process_name = selectedType._process_name;
		nodeData.operation = selectedType._operation;
		selectedType._process_name = null;
		selectedType._operation = null;
	}

	// Upgrade the node
	store.nodes[nodeIndex].type = nodeType;
	store.nodes[nodeIndex].label = label;
	store.nodes[nodeIndex].data = {
		...nodeData,
		action_id: props.id,
		action_label: label,
		suggested_parent_id: null,
		suggested_source_handle: null,
	};

	if (suggestedParentId) {
		const edgeId = `e-${suggestedParentId}-${props.id}-${suggestedSourceHandle}`;
		const hasIncoming = store.edges.some((edge) => edge.target === props.id);
		if (!hasIncoming) {
			store.edges.push({
				id: edgeId,
				source: suggestedParentId,
				target: props.id,
				sourceHandle: suggestedSourceHandle,
				animated: suggestedParentId === "root",
			});
		}
	}

	store.selected_id = props.id;
	store.touch_node(props.id);
	store.mark_dirty();
}

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}

onMounted(() => {
	loadProcessOperations();
});
</script>

<template>
	<div class="action-selector-card" :class="{ selected: selected }">
		<Handle type="target" :position="Position.Left" class="handle-target" />

		<div class="node-header">
			<i class="fa fa-plus-circle"></i>
			<span class="header-text">{{ __("New Action") }}</span>
			<button class="delete-btn" @click.stop="deleteNode" v-if="selected">
				<i class="fa fa-trash"></i>
			</button>
		</div>

		<div class="node-body" @dblclick.stop="store.selected_id = props.id">
			<div class="form-group search-group">
				<label class="small text-muted">{{ __("Action Type") }}</label>
				<div class="search-wrapper">
					<div class="search-input-group">
						<i class="fa fa-search search-icon"></i>
						<input
							type="text"
							v-model="searchQuery"
							class="form-control input-xs"
							:placeholder="__('Search actions...')"
							@focus="onSearchFocus"
							@blur="onSearchBlur"
							@keyup.enter="onCreate"
						/>
					</div>
					<div v-if="showResults && filteredResults.length" class="search-results">
						<div
							v-for="(item, idx) in filteredResults"
							:key="idx"
							:class="[
								'search-result-item',
								item.type === 'header' ? 'result-header' : 'result-option',
							]"
							@mousedown.prevent="selectItem(item)"
						>
							<template v-if="item.type === 'header'">
								<span class="header-label">{{ item.label }}</span>
							</template>
							<template v-else>
								<i
									:class="['fa', item.icon?.replace('fa ', '')]"
									:style="{ color: item.color }"
								></i>
								<div class="result-text">
									<span class="result-label">{{ item.label }}</span>
									<span v-if="item.description" class="result-desc">{{
										item.description
									}}</span>
								</div>
							</template>
						</div>
					</div>
				</div>
			</div>
			<div class="form-group">
				<label class="small text-muted">{{ __("Label") }}</label>
				<input
					type="text"
					v-model="customLabel"
					class="form-control input-xs"
					:placeholder="__('Enter label...')"
					@keyup.enter="onCreate"
				/>
			</div>
			<button class="btn btn-primary btn-xs btn-block mt-2" @click="onCreate">
				{{ __("Create") }}
			</button>
		</div>

		<div class="node-footer">
			<span class="text-muted small">{{ __("Configure to proceed") }}</span>
		</div>

		<Handle type="source" :position="Position.Right" id="default" class="handle-source" />
	</div>
</template>

<style scoped>
.action-selector-card {
	width: 220px;
	background: #fff;
	border: 2px dashed #d1d8dd;
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	transition: all 0.2s ease;
}

.action-selector-card.selected {
	border-color: var(--primary);
	border-style: solid;
	box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2);
}

.node-header {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid #f0f4f7;
	gap: 8px;
	background: #f8f9fa;
	border-radius: 8px 8px 0 0;
}

.node-header i {
	color: var(--primary);
	font-size: 14px;
}

.header-text {
	font-size: 11px;
	font-weight: 700;
	color: #6c757d;
	flex: 1;
}

.delete-btn {
	background: none;
	border: none;
	padding: 2px;
	cursor: pointer;
	color: #adb5bd;
}

.delete-btn:hover {
	color: #dc3545;
}

.node-body {
	padding: 12px;
}

.form-group {
	margin-bottom: 8px;
}

.form-group label {
	display: block;
	margin-bottom: 2px;
}

.search-wrapper {
	position: relative;
}

.search-input-group {
	position: relative;
	display: flex;
	align-items: center;
}

.search-icon {
	position: absolute;
	left: 8px;
	color: #adb5bd;
	font-size: 10px;
	z-index: 1;
	pointer-events: none;
}

.search-input-group input {
	padding-left: 24px !important;
}

.search-results {
	position: absolute;
	top: 100%;
	left: 0;
	right: 0;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
	z-index: 100;
	max-height: 240px;
	overflow-y: auto;
	margin-top: 2px;
}

.search-result-item {
	cursor: pointer;
	padding: 6px 10px;
	font-size: 11px;
	transition: background 0.15s;
}

.result-header {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	color: #94a3b8;
	padding: 6px 10px 3px;
	cursor: default;
	letter-spacing: 0.5px;
	border-top: 1px solid #f1f5f9;
}

.result-header:first-child {
	border-top: none;
}

.result-option {
	display: flex;
	align-items: flex-start;
	gap: 8px;
}

.result-option:hover {
	background: #f0f7ff;
}

.result-option i {
	margin-top: 2px;
	font-size: 12px;
	width: 14px;
	text-align: center;
}

.result-text {
	display: flex;
	flex-direction: column;
	min-width: 0;
}

.result-label {
	font-weight: 600;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.result-desc {
	font-size: 9px;
	color: #94a3b8;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.node-footer {
	padding: 6px 12px;
	background-color: #f8fcfd;
	border-bottom-left-radius: 8px;
	border-bottom-right-radius: 8px;
	border-top: 1px solid #f0f4f7;
	text-align: center;
}

.handle-target,
.handle-source {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid #d1d8dd !important;
}

.action-selector-card.selected .handle-target,
.action-selector-card.selected .handle-source {
	border-color: var(--primary) !important;
}
</style>
