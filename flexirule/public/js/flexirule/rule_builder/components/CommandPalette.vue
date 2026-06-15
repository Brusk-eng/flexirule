<template>
	<Teleport to="body">
		<transition name="palette-fade">
			<div v-if="modelValue" class="palette-overlay" @click.self="close">
				<div class="palette-container" ref="paletteRef" @keydown.tab="handleTab">
					<div class="palette-search-wrapper">
						<i class="fa fa-search palette-search-icon"></i>
						<input
							ref="inputRef"
							v-model="query"
							type="text"
							class="palette-input"
							:placeholder="__('Search nodes, actions, or settings...')"
							@keydown="onKeydown"
						/>
						<div class="palette-esc-badge">ESC</div>
					</div>

					<div class="palette-results v2-scrollbar" ref="resultsRef">
						<div v-if="!filteredResults.length" class="palette-no-results">
							{{ __("No results found for '{0}'", [query]) }}
						</div>

						<div
							v-for="(item, idx) in filteredResults"
							:key="item.id || idx"
							class="palette-item"
							:class="{ active: idx === activeIndex }"
							@click="selectItem(item)"
							@mouseover="activeIndex = idx"
						>
							<div class="palette-item-icon" :style="{ color: item.color }">
								<i :class="['fa', item.icon]"></i>
							</div>
							<div class="palette-item-content">
								<div class="palette-item-title">{{ item.label }}</div>
								<div class="palette-item-subtitle" v-if="item.description">
									{{ item.description }}
								</div>
							</div>
							<div class="palette-item-shortcut" v-if="item.shortcut">
								{{ item.shortcut }}
							</div>
						</div>
					</div>

					<div class="palette-footer">
						<div class="footer-tip"><kbd>↑↓</kbd> {{ __("to navigate") }}</div>
						<div class="footer-tip"><kbd>ENTER</kbd> {{ __("to select") }}</div>
					</div>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from "vue";
import { useRuleStore, useGraphStore, useUIStore } from "../stores";
import { useKeyboardRegistry } from "../composables/useKeyboardRegistry";
import { useFocusTrap } from "../composables/useFocusTrap";

const props = defineProps({
	modelValue: Boolean,
});

const emit = defineEmits(["update:modelValue"]);

const ruleStore = useRuleStore();
const graphStore = useGraphStore();
const uiStore = useUIStore();
const { registerShortcut, pushContext, popContext } = useKeyboardRegistry();
const { handleTab: trapTab, trapFocus, untrapFocus } = useFocusTrap();

const query = ref("");
const activeIndex = ref(0);
const inputRef = ref(null);
const paletteRef = ref(null);
const resultsRef = ref(null);
const unregisterEsc = ref(null);

const items = computed(() => {
	const allItems = [];

	// Nodes
	graphStore.nodes.forEach((node) => {
		allItems.push({
			id: `node-${node.id}`,
			type: "node",
			label: node.data?.action_label || node.label || node.id,
			description: node.data?.action_type || node.type,
			icon: node.data?.icon || "fa-square-o",
			color: node.data?.color,
			action: () => {
				uiStore.selected_id = node.id;
				ruleStore.open_config(node.id);
			},
		});
	});

	// Global Actions
	allItems.push(
		{
			id: "action-save",
			label: __("Save Rule"),
			description: __("Persist all changes to the server"),
			icon: "fa-floppy-o",
			shortcut: "Ctrl S",
			action: () => ruleStore.save_changes(),
		},
		{
			id: "action-layout",
			label: __("Auto Layout"),
			description: __("Automatically organize nodes in the canvas"),
			icon: "fa-sitemap",
			action: () => {
				const dir = ruleStore.settings?.layout_direction === "Top to Bottom" ? "TB" : "LR";
				// Assuming layoutGraph is accessible via window or a store
				window.fxrRuleBuilder?.layoutGraph?.(dir);
			},
		},
		{
			id: "action-shortcuts",
			label: __("Keyboard Shortcuts"),
			description: __("View all available keyboard shortcuts"),
			icon: "fa-keyboard-o",
			shortcut: "Shift ?",
			action: () => (uiStore.show_shortcuts_help = true),
		}
	);

	return allItems;
});

const filteredResults = computed(() => {
	if (!query.value) return items.value.slice(0, 10);
	const q = query.value.toLowerCase();
	return items.value
		.filter(
			(item) =>
				item.label.toLowerCase().includes(q) || item.description?.toLowerCase().includes(q)
		)
		.sort((a, b) => {
			const aLabel = a.label.toLowerCase();
			const bLabel = b.label.toLowerCase();
			if (aLabel.startsWith(q) && !bLabel.startsWith(q)) return -1;
			if (!aLabel.startsWith(q) && bLabel.startsWith(q)) return 1;
			return 0;
		});
});

watch(query, () => {
	activeIndex.value = 0;
});

function close() {
	emit("update:modelValue", false);
}

function selectItem(item) {
	item.action();
	close();
}

function onKeydown(e) {
	if (e.key === "ArrowDown") {
		e.preventDefault();
		activeIndex.value = (activeIndex.value + 1) % filteredResults.value.length;
		scrollToActive();
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		activeIndex.value =
			(activeIndex.value - 1 + filteredResults.value.length) % filteredResults.value.length;
		scrollToActive();
	} else if (e.key === "Enter") {
		e.preventDefault();
		const item = filteredResults.value[activeIndex.value];
		if (item) selectItem(item);
	}
}

function scrollToActive() {
	nextTick(() => {
		const activeEl = resultsRef.value?.querySelector(".palette-item.active");
		activeEl?.scrollIntoView({ block: "nearest" });
	});
}

function handleTab(e) {
	trapTab(e, paletteRef.value);
}

watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			pushContext("palette");
			unregisterEsc.value = registerShortcut({
				key: "Escape",
				context: "palette",
				priority: 100,
				callback: () => close(),
			});
			query.value = "";
			activeIndex.value = 0;
			trapFocus(paletteRef.value);
		} else {
			popContext("palette");
			if (unregisterEsc.value) unregisterEsc.value();
			untrapFocus();
		}
	}
);
</script>

<style scoped>
.palette-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background-color: rgba(15, 23, 42, 0.65);
	backdrop-filter: blur(8px);
	z-index: 200000;
	display: flex;
	justify-content: center;
	padding-top: 15vh;
}

.palette-container {
	background-color: var(--fxr-surface-elevated);
	width: 100%;
	max-width: 640px;
	max-height: 480px;
	border-radius: 16px;
	box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
	display: flex;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid var(--fxr-border-subtle);
}

.palette-search-wrapper {
	padding: 16px;
	display: flex;
	align-items: center;
	gap: 12px;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.palette-search-icon {
	font-size: 18px;
	color: var(--fxr-text-soft);
}

.palette-input {
	flex: 1;
	background: transparent;
	border: none;
	outline: none;
	font-size: 16px;
	color: var(--fxr-text-strong);
	padding: 4px 0;
}

.palette-esc-badge {
	padding: 4px 8px;
	background: var(--fxr-surface-2);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 6px;
	font-size: 10px;
	font-weight: 700;
	color: var(--fxr-text-soft);
}

.palette-results {
	flex: 1;
	overflow-y: auto;
	padding: 8px;
}

.palette-no-results {
	padding: 32px;
	text-align: center;
	color: var(--fxr-text-soft);
	font-size: 14px;
}

.palette-item {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 10px 12px;
	border-radius: 10px;
	cursor: pointer;
	transition: background 0.15s ease;
}

.palette-item.active {
	background-color: var(--fxr-accent-soft);
}

.palette-item-icon {
	width: 32px;
	height: 32px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 8px;
	background: var(--fxr-surface-2);
	font-size: 14px;
}

.palette-item.active .palette-item-icon {
	background: var(--fxr-surface);
}

.palette-item-content {
	flex: 1;
	min-width: 0;
}

.palette-item-title {
	font-size: 14px;
	font-weight: 600;
	color: var(--fxr-text-strong);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.palette-item-subtitle {
	font-size: 11px;
	color: var(--fxr-text-soft);
	margin-top: 1px;
}

.palette-item-shortcut {
	font-size: 10px;
	font-weight: 600;
	color: var(--fxr-text-soft);
	opacity: 0.7;
}

.palette-footer {
	padding: 10px 16px;
	background: var(--fxr-surface-2);
	display: flex;
	gap: 20px;
	border-top: 1px solid var(--fxr-border-subtle);
}

.footer-tip {
	font-size: 11px;
	color: var(--fxr-text-soft);
	display: flex;
	align-items: center;
	gap: 6px;
}

kbd {
	background: var(--fxr-surface);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 4px;
	padding: 1px 4px;
	font-size: 9px;
}

.palette-fade-enter-active,
.palette-fade-leave-active {
	transition: all 0.2s ease;
}

.palette-fade-enter-from,
.palette-fade-leave-to {
	opacity: 0;
	transform: scale(0.98);
}
</style>
