import { ref, computed, nextTick, provide } from "vue";
import transformUtils from "../utils/transform.js";

/**
 * useTransformMapper
 *
 * Composable to manage the state and logic of the visual transform mapper.
 */
export function useTransformMapper(props, emit, bodyRef) {
	const sourceSearch = ref("");
	const targetSearch = ref("");
	const activeLine = ref(null);
	const selectedMapping = ref(null);
	const expandedNodes = ref(new Set());
	const mappingLines = ref([]);
	const svgStyle = ref({ height: "100%", width: "100%" });

	// Provide state to recursive nodes
	provide("expandedNodes", expandedNodes);

	const mappings = computed({
		get: () => props.modelValue || [],
		set: (val) => emit("update:modelValue", val),
	});
	provide("mappings", mappings);

	// -- Tree Construction --

	function buildTree(flatList) {
		const root = [];
		const map = {};

		flatList.forEach((item) => {
			const parts = item.value.split(".");
			let currentLevel = root;
			let currentPath = "";

			parts.forEach((part, idx) => {
				const parentPath = currentPath;
				currentPath = currentPath ? `${currentPath}.${part}` : part;

				if (!map[currentPath]) {
					const node = {
						name: part,
						label: idx === parts.length - 1 ? item.label || part : part,
						path: currentPath,
						isLeaf: true,
						children: [],
						fieldtype: idx === parts.length - 1 ? item.fieldtype : null,
					};
					map[currentPath] = node;
					currentLevel.push(node);

					if (parentPath && map[parentPath]) {
						map[parentPath].isLeaf = false;
					}
				}
				currentLevel = map[currentPath].children;
			});
		});
		return root;
	}

	const sourceTree = computed(() => buildTree(props.sourceSchema || []));
	const targetTree = computed(() => buildTree(props.targetSchema || []));

	const filteredSourceTree = computed(() => filterTree(sourceTree.value, sourceSearch.value));
	const filteredTargetTree = computed(() => filterTree(targetTree.value, targetSearch.value));

	function filterTree(tree, query) {
		if (!query) return tree;
		const q = query.toLowerCase();
		return tree
			.map((node) => {
				const children = filterTree(node.children, query);
				const matches =
					node.label.toLowerCase().includes(q) || node.path.toLowerCase().includes(q);
				if (matches || children.length > 0) {
					return { ...node, children, isOpen: true };
				}
				return null;
			})
			.filter(Boolean);
	}

	// -- Line Calculation --

	function updateLines() {
		if (!bodyRef.value) return;

		const lines = [];
		const bodyRect = bodyRef.value.getBoundingClientRect();

		mappings.value.forEach((m) => {
			const sourceEl = bodyRef.value.querySelector(
				`[data-path="${m.source}"][data-type="source"] .anchor`
			);
			const targetEl = bodyRef.value.querySelector(
				`[data-path="${m.target}"][data-type="target"] .anchor`
			);

			if (sourceEl && targetEl) {
				const sRect = sourceEl.getBoundingClientRect();
				const tRect = targetEl.getBoundingClientRect();

				const x1 = sRect.right - bodyRect.left;
				const y1 = sRect.top + sRect.height / 2 - bodyRect.top;
				const x2 = tRect.left - bodyRect.left;
				const y2 = tRect.top + tRect.height / 2 - bodyRect.top;

				// Cubic bezier curve
				const cp1x = x1 + (x2 - x1) / 2.5;
				const cp2x = x2 - (x2 - x1) / 2.5;

				lines.push({
					path: `M ${x1} ${y1} C ${cp1x} ${y1}, ${cp2x} ${y2}, ${x2} ${y2}`,
					mapping: m,
				});
			}
		});

		mappingLines.value = lines;
	}

	// -- Expansion Management --

	function isExpanded(path) {
		return expandedNodes.value.has(path);
	}

	function toggleNode(node) {
		if (expandedNodes.value.has(node.path)) {
			expandedNodes.value.delete(node.path);
		} else {
			expandedNodes.value.add(node.path);
		}
		nextTick(updateLines);
	}

	function autoExpandMapped() {
		if (!mappings.value.length) return;

		mappings.value.forEach((m) => {
			const sParts = m.source.split(".");
			for (let i = 1; i < sParts.length; i++) {
				expandedNodes.value.add(sParts.slice(0, i).join("."));
			}
			const tParts = m.target.split(".");
			for (let i = 1; i < tParts.length; i++) {
				expandedNodes.value.add(tParts.slice(0, i).join("."));
			}
		});
		nextTick(updateLines);
	}

	function isSourceMapped(path) {
		return mappings.value.some((m) => m.source === path);
	}

	function isTargetMapped(path) {
		return mappings.value.some((m) => m.target === path);
	}
	function autoMap() {
		const suggestions = transformUtils.fuzzyMatch(props.sourceSchema, props.targetSchema);
		const existingTargets = new Set(mappings.value.map((m) => m.target));

		const newMappings = [
			...mappings.value,
			...suggestions.filter((s) => !existingTargets.has(s.target)),
		];

		mappings.value = newMappings;
		nextTick(updateLines);
	}

	return {
		sourceSearch,
		targetSearch,
		activeLine,
		selectedMapping,
		expandedNodes,
		mappingLines,
		svgStyle,
		sourceTree,
		targetTree,
		filteredSourceTree,
		filteredTargetTree,
		mappings,
		updateLines,
		toggleNode,
		isExpanded,
		isSourceMapped,
		isTargetMapped,
		autoExpandMapped,
		autoMap,
	};
}
