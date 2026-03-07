<script setup>
import { computed, ref, watch } from "vue";
import { getContract } from "../../../core/contracts.js";
import { useStore } from "../../store";

const props = defineProps({
	node: Object,
});

const store = useStore();

const actionType = computed(() => props.node?.data?.action_type);
const contract = computed(() => (actionType.value ? getContract(actionType.value) : null));

const operationDescription = ref("");

watch(
	() => [props.node?.data?.process_name, props.node?.data?.operation],
	async ([processName, opName]) => {
		if (processName && opName) {
			const ops = await store.get_process_operations(processName);
			const op = ops.find((o) => o.func_name === opName);
			operationDescription.value = op?.description || "";
		} else {
			operationDescription.value = "";
		}
	},
	{ immediate: true }
);
</script>

<template>
	<div class="v2-preview-panel">
		<div class="panel-content">
			<!-- Configuration Guide Section -->
			<div class="guide-section mb-5">
				<div class="d-flex align-items-center mb-4">
					<div
						class="guide-icon"
						:style="{ background: contract?.color || 'var(--primary)' }"
					>
						<i :class="contract?.icon || 'fa fa-info-circle'"></i>
					</div>
					<div>
						<h4 class="mb-0">{{ __("Configuration Guide") }}</h4>
						<span class="text-muted small"
							>{{ __("Understanding") }} {{ actionType }}</span
						>
					</div>
				</div>

				<div class="guide-card">
					<div class="guide-item mb-4">
						<label class="guide-label">{{ __("Action Role") }}</label>
						<p class="guide-text">
							{{
								contract?.description ||
								__("No description available for this action type.")
							}}
						</p>
					</div>

					<div class="guide-item" v-if="actionType === 'Process' && operationDescription">
						<label class="guide-label">{{ __("Operation Insight") }}</label>
						<div class="operation-guide">
							<i class="fa fa-lightbulb-o mr-2"></i>
							<p class="guide-text italic mb-0">{{ operationDescription }}</p>
						</div>
					</div>
				</div>
			</div>

			<div class="vision-section">
				<div class="vision-header mb-4">
					<div class="experimental-v2-icon">
						<i class="fa fa-flask"></i>
					</div>
					<h4>{{ __("V2 Vision") }}</h4>
				</div>

				<p class="text-muted mb-4">
					{{
						__(
							"We are moving towards a fully reactive, schema-aware builder where every action is a micro-process with its own inputs, internal state, and structured outputs."
						)
					}}
				</p>

				<div class="v2-features">
					<div class="feature-card">
						<i class="fa fa-magic"></i>
						<span>{{ __("AI-Assisted Mapping") }}</span>
					</div>
					<div class="feature-card">
						<i class="fa fa-code"></i>
						<span>{{ __("Advanced Expressions") }}</span>
					</div>
					<div class="feature-card">
						<i class="fa fa-history"></i>
						<span>{{ __("Action History") }}</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.v2-preview-panel {
	height: 100%;
	display: flex;
	flex-direction: column;
	background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
	padding: 40px;
	overflow-y: auto;
}

.panel-content {
	max-width: 800px;
	margin: 0 auto;
	width: 100%;
}

.guide-section {
	text-align: left;
}

.guide-icon {
	width: 48px;
	height: 48px;
	border-radius: 12px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #fff;
	font-size: 20px;
	margin-right: 16px;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.guide-card {
	background: #fff;
	border: 1px solid var(--border-color);
	border-radius: 16px;
	padding: 24px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.guide-label {
	font-size: 11px;
	font-weight: 800;
	text-transform: uppercase;
	color: var(--primary);
	letter-spacing: 0.5px;
	display: block;
	margin-bottom: 8px;
}

.guide-text {
	font-size: 14px;
	line-height: 1.6;
	color: #4a5568;
}

.operation-guide {
	display: flex;
	align-items: flex-start;
	background: #f0f7ff;
	padding: 16px;
	border-radius: 12px;
	border-left: 4px solid var(--primary);
}

.operation-guide i {
	color: var(--primary);
	font-size: 18px;
	margin-top: 2px;
}

.vision-section {
	text-align: center;
	border-top: 1px solid #edf2f7;
	padding-top: 40px;
}

.vision-header {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 12px;
}

.experimental-v2-icon {
	width: 50px;
	height: 50px;
	background: var(--primary);
	color: #fff;
	border-radius: 12px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 24px;
	box-shadow: 0 10px 20px rgba(var(--primary-rgb, 59, 130, 246), 0.2);
}

.v2-features {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 16px;
}

.feature-card {
	padding: 20px;
	background: #fff;
	border: 1px solid var(--border-color);
	border-radius: 12px;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 12px;
	font-size: 11px;
	font-weight: 600;
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.feature-card:hover {
	transform: translateY(-5px);
	border-color: var(--primary);
	box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
}

.feature-card i {
	font-size: 24px;
	color: var(--primary);
}
</style>
