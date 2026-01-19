<template>
	<div class="v2-preview-panel">
		<div class="empty-state">
			<div class="experimental-v2-icon">
				<i class="fa fa-flask fa-3x"></i>
			</div>
			<h4>{{ __("Experimental V2 Configuration") }}</h4>
			<p class="text-muted">
				{{ __("This is a preview of the upcoming flow-oriented configuration interface.") }}
			</p>
			
			<div class="v2-features mt-4">
				<div class="feature-card">
					<i class="fa fa-magic"></i>
					<span>{{ __("AI-Assisted Mapping") }}</span>
				</div>
				<div class="feature-card">
					<i class="fa fa-code"></i>
					<span>{{ __("Advanced Expression Editor") }}</span>
				</div>
				<div class="feature-card">
					<i class="fa fa-history"></i>
					<span>{{ __("Action History & Undo") }}</span>
				</div>
			</div>

			<div class="alert alert-info mt-5 text-left">
				<h5 class="alert-heading">{{ __("V2 Vision") }}</h5>
				<p class="small mb-0">
					{{ __("We are moving towards a fully reactive, schema-aware builder where every action is a micro-process with its own inputs, internal state, and structured outputs.") }}
				</p>
			</div>
		</div>
	</div>
</template>

<style scoped>
.v2-preview-panel {
	height: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
	padding: 40px;
}

.empty-state {
	max-width: 600px;
	text-align: center;
}

.experimental-v2-icon {
	width: 80px;
	height: 80px;
	background: var(--primary);
	color: #fff;
	border-radius: 20px;
	display: flex;
	align-items: center;
	justify-content: center;
	margin: 0 auto 24px;
	box-shadow: 0 10px 25px rgba(var(--primary-rgb, 59, 130, 246), 0.3);
}

.v2-features {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 16px;
}

.feature-card {
	padding: 16px;
	background: #fff;
	border: 1px solid var(--border-color);
	border-radius: 12px;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 10px;
	font-size: 11px;
	font-weight: 600;
	transition: all 0.2s;
}

.feature-card:hover {
	transform: translateY(-5px);
	border-color: var(--primary);
	box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
}

.feature-card i {
	font-size: 20px;
	color: var(--primary);
}

.alert-info {
	background: #ebf5ff;
	border: 1px solid #cce5ff;
	border-radius: 12px;
}
</style>
