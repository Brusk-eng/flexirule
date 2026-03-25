<template>
	<div class="action-settings-container">
		<div class="settings-section">
			<h6 class="section-title-mini">{{ __("Execution Settings") }}</h6>
			<div class="settings-grid">
				<div class="grid-item">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'is_enabled',
								fieldtype: 'Check',
								label: __('Enabled'),
							})
						"
						:modelValue="node.data?.is_enabled"
						@update:modelValue="(val) => update_action_field('is_enabled', val)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'is_async',
								fieldtype: 'Check',
								label: __('Run Asynchronously'),
							})
						"
						:modelValue="node.data?.is_async"
						@update:modelValue="(val) => update_action_field('is_async', val)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'skip_permissions',
								fieldtype: 'Check',
								label: __('Skip Permissions'),
							})
						"
						:modelValue="node.data?.skip_permissions"
						@update:modelValue="(val) => update_action_field('skip_permissions', val)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'on_error',
								fieldtype: 'Select',
								label: __('On Error'),
								options: 'Stop\nContinue\nRetry\nRollback\nEscalate',
							})
						"
						:modelValue="node.data?.on_error"
						@update:modelValue="(val) => update_action_field('on_error', val)"
					/>
				</div>
				<div class="grid-item" v-if="node.data?.on_error === 'Retry'">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'retry_count',
								fieldtype: 'Int',
								label: __('Retry Count'),
							})
						"
						:modelValue="node.data?.retry_count"
						@update:modelValue="(val) => update_action_field('retry_count', val)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'timeout',
								fieldtype: 'Int',
								label: __('Timeout (s)'),
							})
						"
						:modelValue="node.data?.timeout"
						@update:modelValue="(val) => update_action_field('timeout', val)"
					/>
				</div>
			</div>
		</div>

		<div class="section-divider my-4"></div>

		<div class="settings-section">
			<h6 class="section-title-mini">{{ __("Output Settings") }}</h6>
			<div class="settings-grid">
				<div class="grid-item span-2">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'return_variable',
								fieldtype: 'Data',
								label: __('Return Variable Name'),
								placeholder: __('e.g. my_result'),
								description: __(
									'The variable where the action result will be stored.'
								),
							})
						"
						:modelValue="node.data?.return_variable"
						@update:modelValue="(val) => update_action_field('return_variable', val)"
					/>
				</div>
			</div>
		</div>

		<div class="section-divider my-4"></div>

		<div class="settings-section">
			<h6 class="section-title-mini">{{ __("Flow Control") }}</h6>
			<div class="settings-grid">
				<div class="grid-item span-2">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'next_step_if_true',
								fieldtype: 'Data',
								label:
									node.data?.action_type === 'Condition'
										? __('Next Step (If True)')
										: __('Next Step'),
							})
						"
						:modelValue="node.data?.next_step_if_true"
						@update:modelValue="(val) => update_action_field('next_step_if_true', val)"
					/>
				</div>
				<div class="grid-item span-2" v-if="node.data?.action_type === 'Condition'">
					<ControlFactory
						:df="
							with_read_only({
								fieldname: 'next_step_if_false',
								fieldtype: 'Data',
								label: __('Next Step (If False)'),
							})
						"
						:modelValue="node.data?.next_step_if_false"
						@update:modelValue="(val) => update_action_field('next_step_if_false', val)"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import ControlFactory from "../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const emit = defineEmits(["update:field"]);

function with_read_only(field) {
	return { ...field, read_only: props.readOnly };
}

function update_action_field(fieldname, value) {
	emit("update:field", { fieldname, value });
}
</script>

<style scoped>
.action-settings-container {
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.settings-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16px;
}

.grid-item.span-2 {
	grid-column: 1 / -1;
}

.section-title-mini {
	font-size: 11px;
	font-weight: 800;
	color: #64748b;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	margin-bottom: 12px;
}

.section-divider {
	height: 1px;
	background: #e2e8f0;
	margin: 8px 0;
}
</style>
