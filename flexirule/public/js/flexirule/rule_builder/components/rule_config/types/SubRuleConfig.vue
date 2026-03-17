<template>
	<div class="sub-rule-config">
		<div v-if="!node.data?.rule" class="empty-mode-state text-center p-5">
			<i class="fa fa-cube fa-3x text-muted mb-3 opacity-20"></i>
			<p class="text-muted">
				{{ __("Please select a Sub-Rule in the Setup panel to proceed.") }}
			</p>
		</div>

		<div v-else class="config-container p-3">
			<div class="alert alert-info py-2 px-3 small">
				<i class="fa fa-info-circle"></i>
				{{ __("Configuring Sub-Rule: {0}").replace("{0}", node.data.rule) }}
			</div>
			<!-- Future: Add sub-rule argument mapping here -->
		</div>
	</div>
</template>

<script setup>
import { onMounted } from "vue";
import { useStore } from "../../../store";
import SubRuleNodeConfig from "../../node_configs/SubRuleNodeConfig.vue";

const props = defineProps({
	node: Object,
});

const store = useStore();

const emit = defineEmits(["update:field"]);

function updateField(key, val) {
	emit("update:field", key, val);
}

onMounted(() => {
	if (!store.available_rules.length) {
		store.fetch_available_rules();
	}
});
</script>
