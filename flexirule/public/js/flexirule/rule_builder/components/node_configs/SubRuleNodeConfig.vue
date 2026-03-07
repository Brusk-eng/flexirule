<template>
	<div class="subrule-node-config">
		<div class="form-group relative">
			<label>{{ __("Select Rule") }}</label>
			<div class="input-group">
				<input
					type="text"
					class="form-control"
					v-model="subRuleSearch"
					@focus="showSuggestions = true"
					:placeholder="__('Search rule...')"
				/>
			</div>

			<div v-if="showSuggestions" class="suggestions-dropdown">
				<div
					v-for="r in filteredRules"
					:key="r.name"
					class="suggestion-item"
					@click="selectRule(r)"
				>
					<div class="d-flex justify-content-between align-items-center w-100">
						<div class="suggestion-name">{{ r.rule_name || r.name }}</div>
						<span
							v-if="r.trigger_event === 'Manual'"
							class="badge badge-info"
							style="font-size: 9px"
							>{{ __("Manual") }}</span
						>
						<span v-else class="badge border text-muted" style="font-size: 9px">{{
							r.trigger_event
						}}</span>
					</div>
					<div class="suggestion-path" style="font-size: 10px">{{ r.name }}</div>
				</div>
				<div v-if="!filteredRules.length" class="p-2 text-muted">
					{{ __("No rules found for this DocType") }}
				</div>
			</div>
			<div class="help-text text-muted" style="font-size: 11px">
				{{ __("Rule to execute. Context vars are shared.") }}
			</div>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	nodeData: Object,
	availableRules: { type: Array, default: () => [] },
});

const emit = defineEmits(["update-field"]);

const subRuleSearch = ref("");
const showSuggestions = ref(false);

const filteredRules = computed(() => {
	return props.availableRules.filter(
		(r) =>
			r.name.toLowerCase().includes(subRuleSearch.value.toLowerCase()) ||
			(r.rule_name && r.rule_name.toLowerCase().includes(subRuleSearch.value.toLowerCase()))
	);
});

watch(
	() => props.nodeData?.rule,
	(newVal) => {
		if (newVal) {
			const r = props.availableRules.find((r) => r.name === newVal);
			subRuleSearch.value = r ? r.rule_name || r.name : newVal;
		} else {
			subRuleSearch.value = "";
		}
	},
	{ immediate: true }
);

function selectRule(rule) {
	subRuleSearch.value = rule.rule_name || rule.name;
	emit("update-field", "rule", rule.name);
	showSuggestions.value = false;
}
</script>

<style scoped>
.suggestions-dropdown {
	position: absolute;
	top: 100%;
	left: 0;
	right: 0;
	background: white;
	border: 1px solid var(--border-color);
	border-radius: 4px;
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	max-height: 250px;
	overflow-y: auto;
	z-index: 100;
}

.suggestion-item {
	padding: 8px 12px;
	cursor: pointer;
	border-bottom: 1px solid #f0f0f0;
}

.suggestion-item:hover {
	background: var(--gray-100);
}

.suggestion-name {
	font-weight: 500;
}

.suggestion-path {
	color: var(--text-muted);
}
</style>
