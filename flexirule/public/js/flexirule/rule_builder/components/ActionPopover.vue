<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import {
	ACTION_TYPE_CONTRACT,
	PROCESS_REGISTRY,
	getActionTypeOptions,
	getOperationOptions,
	loadContractsFromBackend,
} from "../../core/contracts";

const props = defineProps({
	active: Boolean,
	position: Object, // { x, y } in pixels relative to viewport or parent
});

const emit = defineEmits(["select", "close"]);

const searchQuery = ref("");
const showResults = ref(true);
const processOperations = ref([]);
const selectedIndex = ref(-1);
const canPaste = ref(false);

const popoverRef = ref(null);

// Fuzzy match helper
function fuzzyMatch(text, query) {
	if (!query) return true;
	const lowerText = text.toLowerCase();
	const q = query.toLowerCase().trim();
	if (lowerText.includes(q)) return true;
	const words = lowerText.split(/[\s_-]+/).filter(Boolean);
	const acronym = words.map((w) => w[0]).join("");
	if (acronym.includes(q)) return true;
	const qWords = q.split(/\s+/).filter(Boolean);
	return qWords.every((qw) => words.some((w) => w.startsWith(qw) || w.includes(qw)));
}

const ACTION_CATEGORIES = {
	"Control Flow": ["Condition", "Stop", "Wait", "Sub-Rule"],
	"Data Actions": ["Set Value", "Query Records", "Document Action"],
	Notifications: ["Notify"],
	Processes: ["Process"],
};

const actionTypes = computed(() => {
	try {
		const meta = window.frappe ? frappe.get_meta("Rule Action") : null;
		if (!meta || !meta.fields) {
			// Fallback if meta is not loaded
			return getActionTypeOptions().map((t) => {
				const contract = ACTION_TYPE_CONTRACT[t] || {};
				return {
					label: t,
					value: t,
					actionType: t,
					icon: contract.css?.icon || "fa fa-cog",
					color: contract.css?.color || "#6b7280",
					description: contract.description || "",
					category:
						Object.entries(ACTION_CATEGORIES).find(([, types]) =>
							types.includes(t)
						)?.[0] || "Other",
				};
			});
		}

		const typeField = meta.fields.find((f) => f.fieldname === "action_type");
		if (!typeField || !typeField.options) return [];

		return typeField.options
			.split("\n")
			.filter(
				(t) =>
					t && t !== "Entry Action" && t !== "Start" && getActionTypeOptions().includes(t)
			)
			.map((t) => {
				const contract = ACTION_TYPE_CONTRACT[t] || {};
				return {
					label: window.__ ? __(t) : t,
					value: t,
					actionType: t,
					icon: contract.css?.icon || "fa fa-cog",
					color: contract.css?.color || "#6b7280",
					description: contract.description || "",
					category:
						Object.entries(ACTION_CATEGORIES).find(([, types]) =>
							types.includes(t)
						)?.[0] || (window.__ ? __("Other") : "Other"),
				};
			});
	} catch (e) {
		console.error("Error computing actionTypes:", e);
		return [];
	}
});

const filteredResults = computed(() => {
	try {
		const q = searchQuery.value;
		const results = [];

		(actionTypes.value || []).forEach((t) => {
			const ops = getOperationOptions(t.value) || [];
			const matchAction =
				fuzzyMatch(t.label, q) || fuzzyMatch(t.description, q) || fuzzyMatch(t.value, q);
			if (matchAction) {
				results.push({ type: "header", label: t.label });
				results.push({ type: "action", ...t });
			}

			const matchingOps = ops.filter(
				(op) => fuzzyMatch(op.label || op.value, q) || fuzzyMatch(op.value, q)
			);
			if (matchingOps.length) {
				if (!matchAction) results.push({ type: "header", label: t.label });
				matchingOps.forEach((op) => {
					results.push({
						type: "op",
						label: `${t.label} → ${
							window.__ ? __(op.label || op.value) : op.label || op.value
						}`,
						value: t.value,
						operation: op.value,
						process_name: t.value === "Process" ? op.process_name || null : null,
						icon: t.icon,
						color: t.color,
						description: t.description,
					});
				});
			}
		});

		const matchingProcessOps = (processOperations.value || []).filter(
			(op) =>
				fuzzyMatch(op.label, q) ||
				fuzzyMatch(op.process, q) ||
				fuzzyMatch(op.description || "", q)
		);

		if (matchingProcessOps.length) {
			results.push({
				type: "header",
				label: window.__ ? __("Process Operations") : "Process Operations",
			});
			matchingProcessOps.forEach((op) =>
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
	} catch (e) {
		console.error("Error computing filteredResults:", e);
		return [];
	}
});

async function loadProcessOperations() {
	await loadContractsFromBackend();
	if (Array.isArray(PROCESS_REGISTRY) && PROCESS_REGISTRY.length) {
		processOperations.value = PROCESS_REGISTRY.flatMap((proc) =>
			(proc.operations || [])
				.filter((op) => op.enabled !== 0 && op.visible_in_builder !== 0 && op.func_name)
				.map((op) => ({
					process: proc.name,
					module: proc.module,
					operation: op.func_name,
					label: op.label || op.func_name,
					description: op.description || "",
				}))
		);
		return;
	}
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
	const selection = {
		action_type: item.value || "Process",
		operation: item.operation || null,
		process_name: item.process_name || null,
		label: item.label || item.value || "Process",
	};
	emit("select", selection);
}

function onKeydown(e) {
	if (e.key === "Escape") emit("close");
	if (!filteredResults.value.length) return;

	if (e.key === "ArrowDown") {
		e.preventDefault();
		selectedIndex.value = (selectedIndex.value + 1) % filteredResults.value.length;
		if (filteredResults.value[selectedIndex.value]?.type === "header") onKeydown(e);
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		selectedIndex.value =
			(selectedIndex.value - 1 + filteredResults.value.length) % filteredResults.value.length;
		if (filteredResults.value[selectedIndex.value]?.type === "header") onKeydown(e);
	} else if (e.key === "Enter" && selectedIndex.value !== -1) {
		e.preventDefault();
		selectItem(filteredResults.value[selectedIndex.value]);
	}
}

function onClickOutside(e) {
	if (popoverRef.value && !popoverRef.value.contains(e.target)) {
		emit("close");
	}
}

function checkClipboard() {
	try {
		const local = localStorage.getItem("flexirule-clipboard");
		if (local) {
			const parsed = JSON.parse(local);
			canPaste.value = parsed.type === "flexirule-clipboard" && parsed.nodes?.length > 0;
		} else {
			canPaste.value = false;
		}
	} catch (e) {
		canPaste.value = false;
	}
}

function onPasteClick() {
	emit("paste");
}

onMounted(() => {
	loadProcessOperations();
	checkClipboard();
	document.addEventListener("mousedown", onClickOutside);
	// Search input focus
	setTimeout(() => {
		const input = popoverRef.value?.querySelector("input");
		if (input) input.focus();
	}, 100);
});

onUnmounted(() => {
	document.removeEventListener("mousedown", onClickOutside);
});
</script>

<template>
	<div
		ref="popoverRef"
		class="action-popover"
		:style="{
			left: position.x + 'px',
			top: position.y + 'px',
		}"
		@keydown="onKeydown"
	>
		<div class="popover-header">
			<i class="fa fa-plus-circle"></i>
			<span>{{ __("Add Action") }}</span>
		</div>
		<div class="popover-search">
			<i class="fa fa-search"></i>
			<input
				type="text"
				v-model="searchQuery"
				:placeholder="__('Search actions...')"
				class="form-control"
			/>
		</div>
		<div class="popover-body" @wheel.stop>
			<!-- Paste Option -->
			<div
				v-if="canPaste"
				class="result-item is-option paste-option"
				@mousedown.prevent="onPasteClick"
			>
				<div class="item-icon" style="color: var(--blue-500, #3b82f6)">
					<i class="fa fa-paste"></i>
				</div>
				<div class="item-content">
					<div class="item-label">{{ __("Paste Action") }}</div>
					<div class="item-desc">{{ __("Insert from clipboard") }}</div>
				</div>
			</div>

			<div v-if="!filteredResults.length && !canPaste" class="no-results">
				{{ __("No matching actions found") }}
			</div>
			<div
				v-for="(item, idx) in filteredResults"
				:key="idx"
				:class="[
					'result-item',
					item.type === 'header' ? 'is-header' : 'is-option',
					{ active: idx === selectedIndex },
				]"
				@mousedown.prevent="selectItem(item)"
				@mouseover="selectedIndex = idx"
			>
				<template v-if="item.type === 'header'">
					{{ item.label }}
				</template>
				<template v-else>
					<div class="item-icon" :style="{ color: item.color }">
						<i :class="['fa', item.icon?.replace('fa ', '')]"></i>
					</div>
					<div class="item-content">
						<div class="item-label">{{ item.label }}</div>
						<div v-if="item.description" class="item-desc">{{ item.description }}</div>
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<style scoped>
.action-popover {
	position: fixed;
	width: 280px;
	max-height: 400px;
	background: #fff;
	border: 1px solid var(--border-color, #dfe3e8);
	border-radius: 8px;
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
	z-index: 2147483647; /* Maximum possible z-index */
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.popover-header {
	padding: 10px 12px;
	background: #f8f9fa;
	border-bottom: 1px solid #f0f4f7;
	display: flex;
	align-items: center;
	gap: 8px;
	font-weight: 700;
	font-size: 11px;
	color: var(--primary, #3b82f6);
}

.popover-search {
	padding: 8px;
	position: relative;
	border-bottom: 1px solid #f0f4f7;
}

.popover-search i {
	position: absolute;
	left: 16px;
	top: 50%;
	transform: translateY(-50%);
	color: #adb5bd;
	font-size: 10px;
}

.popover-search input {
	padding-left: 28px !important;
	height: 32px;
	font-size: 12px;
	border-radius: 4px;
	border: 1px solid var(--border-color, #dfe3e8);
}

.popover-body {
	flex: 1;
	overflow-y: auto;
	padding: 4px 0;
}

.result-item {
	padding: 8px 12px;
	cursor: pointer;
}

.is-header {
	font-size: 10px;
	font-weight: 700;
	color: #94a3b8;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	padding: 12px 12px 4px;
	cursor: default;
	background: #fff;
	position: sticky;
	top: 0;
	z-index: 1;
}

.is-option {
	display: flex;
	align-items: center;
	gap: 10px;
	transition: background 0.1s;
}

.is-option:hover,
.is-option.active {
	background: #f1f5f9;
}

.item-icon {
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
}

.item-content {
	flex: 1;
	min-width: 0;
}

.item-label {
	font-size: 12px;
	font-weight: 500;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-desc {
	font-size: 10px;
	color: #64748b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.no-results {
	padding: 20px;
	text-align: center;
	color: #94a3b8;
	font-size: 12px;
}

.paste-option {
	border-bottom: 1px solid #f1f5f9;
	background: #f8fafc;
}

.paste-option:hover {
	background: #f1f5f9;
}

/* Custom Scrollbar */
.popover-body::-webkit-scrollbar {
	width: 6px;
}
.popover-body::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 3px;
}
</style>
