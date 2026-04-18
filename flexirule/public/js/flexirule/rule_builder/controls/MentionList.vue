<template>
	<div class="tg-mention-list" v-if="items.length">
		<button
			v-for="(item, index) in items"
			:key="item.value || item"
			class="tg-mention-item"
			:class="{ 'is-selected': index === selectedIndex }"
			@click="selectItem(index)"
		>
			<code>{{ item.value || item }}</code>
			<span v-if="item.label && item.label !== item.value" class="tg-ml-label">{{
				item.label
			}}</span>
		</button>
	</div>
	<div v-else class="tg-mention-list tg-mention-empty">
		{{ __("No variables found") }}
	</div>
</template>

<script>
export default {
	props: {
		items: { type: Array, required: true },
		command: { type: Function, required: true },
	},
	data() {
		return { selectedIndex: 0 };
	},
	watch: {
		items() {
			this.selectedIndex = 0;
		},
	},
	methods: {
		onKeyDown({ event }) {
			if (event.key === "ArrowUp") {
				this.upHandler();
				return true;
			}
			if (event.key === "ArrowDown") {
				this.downHandler();
				return true;
			}
			if (event.key === "Enter") {
				this.enterHandler();
				return true;
			}
			return false;
		},
		upHandler() {
			this.selectedIndex = (this.selectedIndex + this.items.length - 1) % this.items.length;
		},
		downHandler() {
			this.selectedIndex = (this.selectedIndex + 1) % this.items.length;
		},
		enterHandler() {
			this.selectItem(this.selectedIndex);
		},
		selectItem(index) {
			const item = this.items[index];
			if (item) {
				this.command({ id: item.value || item, label: item.label || item.value || item });
			}
		},
	},
};
</script>

<style scoped>
.tg-mention-list {
	background: var(--bg-light, #fff);
	border: 1px solid var(--border-color);
	border-radius: 8px;
	box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
	padding: 4px;
	max-height: 200px;
	overflow-y: auto;
	min-width: 180px;
}

.tg-mention-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 5px 10px;
	width: 100%;
	border: none;
	background: transparent;
	border-radius: 4px;
	cursor: pointer;
	font-size: 12px;
	text-align: left;
	transition: background 0.1s;
}

.tg-mention-item:hover,
.tg-mention-item.is-selected {
	background: var(--bg-blue, #e8f0fe);
}

.tg-mention-item code {
	font-size: 11px;
	color: var(--primary, #2490ef);
	background: var(--control-bg, #f4f5f6);
	padding: 1px 5px;
	border-radius: 3px;
}

.tg-ml-label {
	color: var(--text-muted);
	font-size: 11px;
}

.tg-mention-empty {
	padding: 10px;
	text-align: center;
	color: var(--text-muted);
	font-size: 11px;
}
</style>
