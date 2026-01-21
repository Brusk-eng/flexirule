<template>
	<div class="flexi-grid" :class="{ 'is-readonly': read_only }">
		<div v-if="df.label" class="grid-label">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</div>

		<div class="grid-container" ref="container">
			<div class="grid-table" :style="tableStyle">
				<!-- Header -->
				<div class="grid-header">
					<div class="header-row">
						<div class="header-cell static-col first-col sticky-col sticky-left" style="left: 0; width: 40px; flex: 0 0 40px;">#</div>
						<div
							v-for="col in stickyColumns"
							:key="col.fieldname"
							class="header-cell resizable"
							:class="{ 'sticky-col': col.isSticky }"
							:style="{
								width: getColumnWidth(col.fieldname),
								minWidth: getColumnWidth(col.fieldname),
								flex: col.isSticky ? `0 0 ${getColumnWidth(col.fieldname)}` : '0 0 auto',
								left: col.isSticky ? col.left : 'auto'
							}"
							:title="__(col.description || '')"
						>
							<div class="header-text">
								{{ __(col.label) }}
								<i v-if="col.description" class="fa fa-info-circle text-muted ml-1 info-icon" :title="__(col.description)"></i>
							</div>
							<div
								class="resize-handle"
								@mousedown="startResize($event, col.fieldname)"
							></div>
						</div>
						<div v-if="!read_only" class="header-cell static-col last-col sticky-col sticky-right" style="right: 0; width: 40px; flex: 0 0 40px;"></div>
					</div>
				</div>

				<!-- Body -->
				<div class="grid-body">
					<div
						v-for="(row, idx) in localRows"
						:key="row.name || idx"
						class="grid-row"
					>
						<div class="grid-cell static-col text-center first-col sticky-col sticky-left" style="left: 0; width: 40px; flex: 0 0 40px;">
							<span class="row-index text-muted">{{ idx + 1 }}</span>
						</div>

						<div
							v-for="col in stickyColumns"
							:key="col.fieldname"
							class="grid-cell field-cell"
							:class="getCellClasses(row, col)"
							:style="{
								width: getColumnWidth(col.fieldname),
								minWidth: getColumnWidth(col.fieldname),
								flex: col.isSticky ? `0 0 ${getColumnWidth(col.fieldname)}` : '0 0 auto',
								left: col.isSticky ? col.left : 'auto'
							}"
						>
							<ControlFactory
								v-if="!isCellHidden(row, col.fieldname)"
								:df="getEffectiveDf(row, col)"
								:modelValue="row[col.fieldname]"
								:doc="row"
								:engine="engine"
								:hideLabel="true"
								:hideDescription="true"
								@update:modelValue="updateCell(idx, col.fieldname, $event)"
							/>
							<div v-else class="cell-placeholder"></div>
						</div>

						<div v-if="!read_only" class="grid-cell static-col text-center last-col sticky-col sticky-right" style="right: 0; width: 40px; flex: 0 0 40px;">
							<button
								class="btn-remove"
								@click="removeRow(idx)"
								:title="__('Remove Row')"
							>
								<i class="fa fa-times"></i>
							</button>
						</div>
					</div>

					<!-- Empty State -->
					<div v-if="localRows.length === 0" class="empty-state">
						<p class="text-muted">{{ __("No rows added.") }}</p>
					</div>
				</div>
			</div>
		</div>

		<div v-if="!read_only" class="grid-footer">
			<button class="btn btn-xs btn-default btn-add" @click="addRow">
				<i class="fa fa-plus"></i> {{ __("Add Row") }}
			</button>
		</div>

		<div v-if="df.description" class="grid-description text-muted">
			{{ df.description }}
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, reactive, watch, nextTick } from "vue";
import ControlFactory from "./ControlFactory.vue";

const props = defineProps({
	df: { type: Object, required: true },
	modelValue: { type: [Array, String], default: () => [] },
	engine: { type: Object, required: true }, 
	read_only: { type: Boolean, default: false }
});

const emit = defineEmits(["update:modelValue"]);

// Internal state for rows
const localRows = ref([]);
let is_updating_local = false;

/**
 * Robust Sync: Minimal diffing to avoid infinite loops and browser freeze.
 */
function syncFromProps() {
	if (is_updating_local) return;
	
	const val = props.modelValue;
	let parsed = [];
	if (Array.isArray(val)) {
		parsed = val;
	} else if (typeof val === 'string' && val) {
		try { parsed = JSON.parse(val); } catch (e) { parsed = []; }
	}
	
    // Only update if array length changes or we have no local state
	if (parsed.length !== localRows.value.length || localRows.value.length === 0) {
		localRows.value = parsed.map((row, idx) => ({
			...(localRows.value[idx] || {}),
			...row,
			name: row.name || (localRows.value[idx]?.name) || frappe.utils.get_random(10),
			__table_fieldname: props.df.fieldname
		}));
	} else {
        // Just sync individual fields if we have same length, but avoid full replacement
        parsed.forEach((newRow, i) => {
            const local = localRows.value[i];
            Object.keys(newRow).forEach(key => {
                if (local[key] !== newRow[key]) local[key] = newRow[key];
            });
        });
    }
}

watch(() => props.modelValue, syncFromProps, { immediate: true });

// Column definitions from df
const columns = computed(() => {
	return props.df.fields || props.df.table_fields || [];
});

const visibleColumns = computed(() => {
	const layoutTypes = ['Section Break', 'Column Break', 'HTML', 'Button', 'Heading'];
	return columns.value.filter(c => {
		if (c.hidden) return false;
		if (layoutTypes.includes(c.fieldtype)) return false;
		return c.in_list_view !== 0 && c.in_list_view !== false;
	});
});

/**
 * Sticky Column Logic - FIXED
 * Calculate cumulative left positions for sticky columns, accounting for the index column
 */
const stickyColumns = computed(() => {
    let currentLeft = 40; // Start after the index column (40px)
    return visibleColumns.value.map(col => {
        const isSticky = col.sticky === 1;
        const leftPosition = isSticky ? currentLeft + 'px' : 'auto';
        if (isSticky) {
            currentLeft += parseInt(getColumnWidth(col.fieldname));
        }
        return { ...col, isSticky, left: leftPosition };
    });
});

// Column Width Mapping & Resizing
const columnWidths = reactive({});

function getColumnWidth(fieldname) {
	if (columnWidths[fieldname]) return columnWidths[fieldname];
	
	const col = columns.value.find(c => c.fieldname === fieldname);
	if (!col) return '180px';

	let widthInput = col.columns || col.width;
	if (widthInput) {
		const w = parseInt(widthInput);
		if (!isNaN(w) && w <= 12) return (w * 80 + 40) + 'px';
		return (typeof widthInput === 'number' ? widthInput + 'px' : widthInput); 
	}

	const typeWidths = {
		'Check': '70px',
		'Int': '100px',
		'Float': '100px',
		'Currency': '120px',
		'Link': '220px',
		'Autocomplete': '240px',
		'Select': '200px',
		'Data': '200px',
		'DocField': '240px'
	};
	return typeWidths[col.fieldtype] || '180px';
}

// Resizing Logic
const isResizing = ref(false);
const activeResizer = ref(null);
const startX = ref(0);
const startWidth = ref(0);

function startResize(e, fieldname) {
	isResizing.value = true;
	activeResizer.value = fieldname;
	startX.value = e.pageX;
	const currentWidth = getColumnWidth(fieldname);
	startWidth.value = parseInt(currentWidth);

	document.addEventListener('mousemove', handleMouseMove);
	document.addEventListener('mouseup', stopResize);
	
	e.preventDefault();
}

function handleMouseMove(e) {
	if (!isResizing.value) return;
	const delta = e.pageX - startX.value;
	const newWidth = Math.max(60, startWidth.value + delta);
	columnWidths[activeResizer.value] = newWidth + 'px';
}

function stopResize() {
	if (!isResizing.value) return;
	isResizing.value = false;
	activeResizer.value = null;
	document.removeEventListener('mousemove', handleMouseMove);
	document.removeEventListener('mouseup', stopResize);
}

const tableStyle = computed(() => {
	let totalWidth = 80; // Account for both index (40px) and delete button (40px) columns
	visibleColumns.value.forEach(c => {
		totalWidth += parseInt(getColumnWidth(c.fieldname));
	});
	return { width: totalWidth + 'px' };
});

// Row Management
async function addRow() {
	const newRow = reactive({ 
		name: frappe.utils.get_random(10),
		__table_fieldname: props.df.fieldname 
	});
	
	columns.value.forEach(f => {
		if (f.default !== undefined) newRow[f.fieldname] = f.default;
	});

	localRows.value.push(newRow);
	emitUpdate();

	await props.engine.evaluate_dependencies(props.engine.config, newRow, props.df.fieldname);
}

function removeRow(idx) {
	const row = localRows.value[idx];
	if (row?.name && props.engine.dependency_states[row.name]) {
		delete props.engine.dependency_states[row.name];
	}
	localRows.value.splice(idx, 1);
	emitUpdate();
}

function updateCell(idx, fieldname, value) {
	const row = localRows.value[idx];
	if (!row) return;

	row[fieldname] = value;
	props.engine.handleFieldChange(fieldname, value, row);
	
	is_updating_local = true;
	emitUpdate();
	nextTick(() => { is_updating_local = false; });
}

function emitUpdate() {
	const data = localRows.value.map(r => {
		const { name, __table_fieldname, ...rest } = r;
		return { ...rest };
	});
	emit("update:modelValue", data);
}

// State helpers (Optimized)
function getCellState(row, fieldname) {
	const contextId = row.name || "unknown";
	return props.engine.dependency_states[contextId]?.[fieldname] || {};
}

function isCellHidden(row, fieldname) {
	return getCellState(row, fieldname).hidden === 1;
}

function getEffectiveDf(row, col) {
	const state = getCellState(row, col.fieldname);
	return {
		...col,
		reqd: state.reqd !== undefined ? state.reqd : col.reqd,
		read_only: (state.read_only !== undefined ? state.read_only : col.read_only) || props.read_only,
		options: (state.options !== undefined && state.options !== null) ? state.options : col.options,
		label: col.label 
	};
}

function getCellClasses(row, col) {
	const state = getCellState(row, col.fieldname);
	return {
		'is-required': state.reqd,
		'is-readonly': state.read_only || props.read_only,
		'has-error': state.reqd && !row[col.fieldname],
		'sticky-col': col.isSticky
	};
}

onMounted(async () => {
	for (const row of localRows.value) {
		await props.engine.evaluate_dependencies(props.engine.config, row, props.df.fieldname);
	}
});
</script>

<style scoped>
.flexi-grid {
	width: 100%;
	margin-bottom: 24px;
}
.grid-label {
	font-size: 13px;
	font-weight: 600;
	color: var(--text-color);
	margin-bottom: 8px;
}
.grid-container {
	border: 1px solid var(--border-color, #d1d8dd);
	border-radius: 8px;
	overflow-x: auto;
	overflow-y: visible !important; /* Allow panel to expand */
	background: #fff;
	box-shadow: 0 1px 3px rgba(0,0,0,0.05);
	position: relative;
}
.grid-table {
	display: block; 
	min-width: 100%;
    width: fit-content;
}
.grid-header {
	display: block;
	position: sticky;
	top: 0;
	z-index: 100;
	background: #f8f9fa;
	border-bottom: 1px solid var(--border-color, #f0f0f0);
}
.header-row, .grid-row {
	display: flex;
	width: 100%;
}
.grid-row {
	border-bottom: 1px solid var(--border-color, #f0f0f0);
    background: #fff;
    height: 40px; /* Fixed Height */
}
.header-row {
    height: 40px; /* Fixed Height */
}
.grid-row:hover {
	background: #fafafb;
}
.grid-row:last-child {
	border-bottom: none;
}
.header-cell, .grid-cell {
	padding: 0 12px;
	display: flex;
	align-items: center; /* Changed back to center for better vertical alignment */
	font-size: 13px;
	flex: 0 0 auto;
	border-right: 1px solid var(--border-color, #f0f0f0);
	position: relative;
	height: 100%; /* Fill fixed row height */
	box-sizing: border-box;
	min-width: 0; /* Allows flex items to shrink below content size */
}
.header-cell {
	font-weight: 700;
	color: var(--text-color);
	background: #f8f9fa;
	z-index: 50;
}
.grid-cell {
    background: inherit;
}
.sticky-col {
	position: sticky !important;
	z-index: 50; /* Consistent z-index for both header and body */
}
.sticky-left {
    left: 0;
    box-shadow: 2px 0 5px rgba(0,0,0,0.04);
}
.sticky-right {
    right: 0;
    box-shadow: -2px 0 5px rgba(0,0,0,0.04);
    border-left: 1px solid var(--border-color, #f0f0f0);
}
.header-cell.sticky-col {
	z-index: 55 !important; /* Header should be slightly above body sticky cols */
}
.header-cell:last-child, .grid-cell:last-child {
	border-right: none;
}
.header-text {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	flex: 1;
	display: flex;
	align-items: center;
}
.info-icon {
	font-size: 12px;
	margin-left: 6px;
	cursor: help;
	color: var(--gray-500);
}
.resize-handle {
	position: absolute;
	right: -3px;
	top: 0;
	bottom: 0;
	width: 6px;
	cursor: col-resize;
	z-index: 5;
}
.resize-handle:hover {
	background: var(--primary-color, #1071e5);
	opacity: 0.4;
}
.static-col {
	justify-content: center;
	align-items: center;
}
.first-col {
	background: #fdfdfd;
}
.last-col {
    background: #fff;
}
.grid-cell :deep(.frappe-control),
.grid-cell :deep(.form-group) {
	margin-bottom: 0 !important;
	width: 100%;
	height: 100% !important; /* Fill the cell vertically */
	display: flex;
	flex-direction: column;
	justify-content: center; /* Vertically center content */
}
.grid-cell :deep(.form-control) {
	height: calc(100% - 4px) !important; /* Account for borders/padding */
	padding: 2px 6px !important; /* Reduced padding for better fit */
	font-size: 13px !important;
	border: 1px solid transparent !important;
	background: transparent !important;
	box-shadow: none !important;
	transition: all 0.2s;
	width: 100%;
	box-sizing: border-box;
	display: flex;
	align-items: center; /* Vertically align content */
}
.grid-cell:hover :deep(.form-control),
.grid-cell :deep(.form-control:focus) {
	border-color: var(--border-color, #d1d8dd) !important;
	background: #fff !important;
	border-radius: 4px;
}
/* Adjust specific control types for better alignment */
.grid-cell :deep(input[type="text"]),
.grid-cell :deep(input[type="number"]),
.grid-cell :deep(input[type="date"]),
.grid-cell :deep(input[type="time"]),
.grid-cell :deep(input[type="datetime-local"]) {
	height: calc(100% - 4px) !important;
	padding: 2px 6px !important;
	display: flex;
	align-items: center;
}

/* Adjust textarea controls */
.grid-cell :deep(textarea.form-control) {
	resize: vertical;
	min-height: calc(100% - 4px) !important;
	height: auto !important;
	padding: 4px 6px !important;
}

/* Adjust select controls specifically */
.grid-cell :deep(select.form-control) {
	padding: 2px 20px 2px 6px !important; /* Account for dropdown arrow */
	appearance: none;
	-webkit-appearance: none;
	-moz-appearance: none;
}

/* Adjust checkbox controls */
.grid-cell :deep(.checkbox) {
	margin: 0 !important;
	display: flex;
	align-items: center;
	height: 100%;
	width: 100%;
}
.grid-cell.is-required::before {
	content: "";
	position: absolute;
	left: 0;
	top: 8px;
	bottom: 8px;
	width: 3px;
	background: var(--red-500, #ef4444);
	border-radius: 0 2px 2px 0;
	opacity: 0.8;
}

/* Ensure dropdowns pop over other rows and sticky columns */
.field-cell {
    overflow: visible !important;
}
.grid-row:hover {
    z-index: 10;
}
.grid-row:focus-within {
    z-index: 100;
}

.btn-remove {
	border: none;
	background: none;
	color: var(--text-muted);
	width: 28px;
	height: 28px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 4px;
	cursor: pointer;
	transition: all 0.2s;
}
.btn-remove:hover {
	color: var(--red-600);
	background: #fff1f2;
}
.grid-footer {
	padding: 12px 0;
	display: flex;
}
.btn-add {
	padding: 6px 16px;
	font-weight: 600;
	border-radius: 8px;
	background: #fff;
	border: 1px solid var(--border-color);
	transition: all 0.2s;
}
.btn-add:hover {
	background: #fdfdfd;
	border-color: var(--gray-400);
}
.empty-state {
	padding: 48px;
	text-align: center;
	background: #fcfcfc;
	color: var(--text-muted);
}
.is-readonly {
	pointer-events: none;
	opacity: 0.8;
}
/* Scrollbar Styling */
.grid-container::-webkit-scrollbar {
	height: 10px;
}
.grid-container::-webkit-scrollbar-track {
	background: transparent;
}
.grid-container::-webkit-scrollbar-thumb {
	background: #e5e7eb;
	border-radius: 5px;
	border: 2px solid #fff;
}
.grid-container::-webkit-scrollbar-thumb:hover {
	background: #d1d5db;
}
</style>
