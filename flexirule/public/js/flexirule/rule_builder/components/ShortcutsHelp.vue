<template>
	<div v-if="modelValue" class="shortcuts-help-overlay" @click.self="$emit('update:modelValue', false)">
		<div class="shortcuts-help-container">
			<header class="shortcuts-help-header">
				<h5><i class="fa fa-keyboard-o"></i> {{ __("Keyboard Shortcuts") }}</h5>
				<button class="btn-close" @click="$emit('update:modelValue', false)">×</button>
			</header>
			<div class="shortcuts-help-body">
				<div class="shortcut-section">
					<h6>{{ __("General") }}</h6>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Ctrl</kbd> + <kbd>S</kbd></span>
						<span class="shortcut-desc">{{ __("Save Rule") }}</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Ctrl</kbd> + <kbd>Z</kbd></span>
						<span class="shortcut-desc">{{ __("Undo") }}</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Shift</kbd> + <kbd>?</kbd></span>
						<span class="shortcut-desc">{{ __("Toggle this help") }}</span>
					</div>
				</div>

				<div class="shortcut-section">
					<h6>{{ __("Navigation") }}</h6>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Alt</kbd> + <kbd>1</kbd></span>
						<span class="shortcut-desc">{{ __("Jump to Variables") }}</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Alt</kbd> + <kbd>2</kbd></span>
						<span class="shortcut-desc">{{ __("Jump to Configuration") }}</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Alt</kbd> + <kbd>3</kbd></span>
						<span class="shortcut-desc">{{ __("Toggle Settings Bar") }}</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Ctrl</kbd> + <kbd>Arrows</kbd></span>
						<span class="shortcut-desc">{{ __("Previous / Next Action") }}</span>
					</div>
				</div>

				<div class="shortcut-section">
					<h6>{{ __("Inside Lists") }}</h6>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>↑ / ↓</kbd></span>
						<span class="shortcut-desc">{{ __("Navigate variables/fields") }}</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Enter</kbd></span>
						<span class="shortcut-desc">{{ __("Insert variable/field") }}</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>C</kbd></span>
						<span class="shortcut-desc">{{ __("Copy variable to clipboard") }}</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
defineProps({
	modelValue: Boolean
});
defineEmits(['update:modelValue']);
</script>

<style scoped>
.shortcuts-help-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background: rgba(0,0,0,0.4);
	backdrop-filter: blur(4px);
	z-index: 2000;
	display: flex;
	justify-content: center;
	align-items: center;
}

.shortcuts-help-container {
	background: #fff;
	width: 400px;
	border-radius: 12px;
	box-shadow: 0 10px 25px rgba(0,0,0,0.2);
	overflow: hidden;
}

.shortcuts-help-header {
	padding: 15px 20px;
	border-bottom: 1px solid var(--border-color);
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.shortcuts-help-header h5 {
	margin: 0;
	font-size: 16px;
}

.btn-close {
	background: none;
	border: none;
	font-size: 20px;
	cursor: pointer;
	color: var(--text-muted);
}

.shortcuts-help-body {
	padding: 20px;
	max-height: 500px;
	overflow-y: auto;
}

.shortcut-section {
	margin-bottom: 20px;
}

.shortcut-section h6 {
	font-size: 11px;
	text-transform: uppercase;
	color: var(--text-muted);
	margin-bottom: 10px;
	letter-spacing: 0.5px;
}

.shortcut-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 8px;
	font-size: 13px;
}

.shortcut-keys {
	display: flex;
	gap: 4px;
}

kbd {
	background: #f1f5f9;
	border: 1px solid #cbd5e1;
	border-radius: 4px;
	padding: 2px 6px;
	font-size: 11px;
	font-family: inherit;
	box-shadow: 0 1px 0 rgba(0,0,0,0.1);
}

.shortcut-desc {
	color: #475569;
}
</style>
