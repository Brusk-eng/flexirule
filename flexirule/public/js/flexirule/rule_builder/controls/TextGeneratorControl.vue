<template>
	<div class="text-generator-control">
		<div v-if="df?.label && !hideLabel" class="control-label label" :class="{ reqd: df?.reqd }">
			{{ __(df.label) }}
		</div>

		<!-- Segment List (recursive) -->
		<div class="tg-segments">
			<div
				v-for="(segment, idx) in ui.segments"
				:key="`seg-${idx}-${segment._key}`"
				class="tg-segment"
			>
				<!-- ═══ Text Segment ═══ -->
				<div v-if="segment.type === 'text'" class="tg-segment-text">
					<div class="tg-seg-head">
						<span class="tg-seg-badge tg-badge-text">{{ __("Text") }}</span>
						<button v-if="!readOnly" class="tg-seg-remove" @click="removeSegment(idx)">
							<i class="fa fa-times"></i>
						</button>
					</div>
					<div class="tg-editor-mini" @click="focusMiniEditor($refs[`editor_${idx}`])">
						<editor-content
							:ref="`editor_${idx}`"
							:editor="getOrCreateEditor(segment, idx)"
						/>
					</div>
				</div>

				<!-- ═══ Variable Segment ═══ -->
				<div v-else-if="segment.type === 'variable'" class="tg-segment-variable">
					<div class="tg-seg-head">
						<span class="tg-seg-badge tg-badge-var">{{ __("Variable") }}</span>
						<button v-if="!readOnly" class="tg-seg-remove" @click="removeSegment(idx)">
							<i class="fa fa-times"></i>
						</button>
					</div>
					<AutocompleteControl
						:df="{ fieldtype: 'Autocomplete', label: '' }"
						:options="variableOptions"
						:modelValue="segment.path"
						:read_only="readOnly"
						:hideLabel="true"
						@update:modelValue="(val) => (segment.path = val || '')"
					/>
				</div>

				<!-- ═══ Conditional Segment ═══ -->
				<div v-else-if="segment.type === 'conditional'" class="tg-segment-cond">
					<div class="tg-seg-head">
						<span class="tg-seg-badge tg-badge-cond">
							<i class="fa fa-code-fork"></i> {{ __("If / Else") }}
						</span>
						<button v-if="!readOnly" class="tg-seg-remove" @click="removeSegment(idx)">
							<i class="fa fa-times"></i>
						</button>
					</div>

					<!-- Condition Card (uneditable preview) -->
					<div
						class="tg-cond-card"
						:class="{ 'tg-cond-card-active': expandedCondIdx === idx }"
						@click="toggleConditionEditor(idx)"
					>
						<div class="tg-cond-summary">
							<i class="fa fa-filter"></i>
							<code v-if="conditionSummary(segment.condition)">{{
								conditionSummary(segment.condition)
							}}</code>
							<span v-else class="text-muted">{{
								__("Click to define condition…")
							}}</span>
						</div>
						<i
							class="fa"
							:class="expandedCondIdx === idx ? 'fa-chevron-up' : 'fa-chevron-down'"
						></i>
					</div>

					<!-- Condition Editor (expanded) -->
					<div v-if="expandedCondIdx === idx && !readOnly" class="tg-cond-editor">
						<ConditionBuilder
							:modelValue="segment.condition || { op: 'and', conditions: [] }"
							:docFields="docFieldOptions"
							:readOnly="readOnly"
							@update:modelValue="(val) => (segment.condition = val)"
						/>
					</div>

					<!-- Then Branch -->
					<div class="tg-branch">
						<div class="tg-branch-label tg-branch-then">{{ __("Then") }}</div>
						<div class="tg-branch-content">
							<SegmentEditor
								:segments="segment.then_segments || []"
								:variableOptions="variableOptions"
								:docFieldOptions="docFieldOptions"
								:readOnly="readOnly"
								@update:segments="(s) => (segment.then_segments = s)"
							/>
						</div>
					</div>

					<!-- Elif Branches -->
					<div
						v-for="(elif_b, eIdx) in segment.elif_branches || []"
						:key="`elif-${idx}-${eIdx}`"
						class="tg-branch"
					>
						<div class="tg-branch-label tg-branch-elif">
							{{ __("Else If") }}
							<button
								v-if="!readOnly"
								class="tg-seg-remove"
								@click="removeElif(segment, eIdx)"
							>
								<i class="fa fa-times"></i>
							</button>
						</div>
						<!-- Elif Condition Card -->
						<div
							class="tg-cond-card tg-cond-card-sm"
							:class="{
								'tg-cond-card-active': expandedCondIdx === `elif-${idx}-${eIdx}`,
							}"
							@click="toggleConditionEditor(`elif-${idx}-${eIdx}`)"
						>
							<div class="tg-cond-summary">
								<i class="fa fa-filter"></i>
								<code v-if="conditionSummary(elif_b.condition)">{{
									conditionSummary(elif_b.condition)
								}}</code>
								<span v-else class="text-muted">{{
									__("Click to set condition…")
								}}</span>
							</div>
						</div>
						<div
							v-if="expandedCondIdx === `elif-${idx}-${eIdx}` && !readOnly"
							class="tg-cond-editor"
						>
							<ConditionBuilder
								:modelValue="elif_b.condition || { op: 'and', conditions: [] }"
								:docFields="docFieldOptions"
								:readOnly="readOnly"
								@update:modelValue="(val) => (elif_b.condition = val)"
							/>
						</div>
						<div class="tg-branch-content">
							<SegmentEditor
								:segments="elif_b.segments || []"
								:variableOptions="variableOptions"
								:docFieldOptions="docFieldOptions"
								:readOnly="readOnly"
								@update:segments="(s) => (elif_b.segments = s)"
							/>
						</div>
					</div>

					<!-- Add Elif Button -->
					<button v-if="!readOnly" class="tg-add-elif" @click="addElif(segment)">
						<i class="fa fa-plus"></i> {{ __("Add Else If") }}
					</button>

					<!-- Else Branch -->
					<div class="tg-branch">
						<div class="tg-branch-label tg-branch-else">{{ __("Else") }}</div>
						<div class="tg-branch-content">
							<SegmentEditor
								:segments="segment.else_segments || []"
								:variableOptions="variableOptions"
								:docFieldOptions="docFieldOptions"
								:readOnly="readOnly"
								@update:segments="(s) => (segment.else_segments = s)"
							/>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Add Segment Toolbar -->
		<div v-if="!readOnly" class="tg-add-bar">
			<button class="tg-add-btn" @click="addSegment('text')">
				<i class="fa fa-font"></i> {{ __("Text") }}
			</button>
			<button class="tg-add-btn" @click="addSegment('variable')">
				<i class="fa fa-code"></i> {{ __("Variable") }}
			</button>
			<button class="tg-add-btn tg-add-btn-cond" @click="addSegment('conditional')">
				<i class="fa fa-code-fork"></i> {{ __("If / Else") }}
			</button>
		</div>

		<!-- Jinja Preview -->
		<div class="tg-preview">
			<div class="tg-preview-title"><i class="fa fa-eye"></i> {{ __("Compiled Jinja") }}</div>
			<code class="tg-preview-code">{{ compiledJinja || __("(empty)") }}</code>
		</div>

		<div v-if="df?.description && !hideDescription" class="description text-muted mt-2">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch, defineComponent, h } from "vue";
import { EditorContent, Editor } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import Mention from "@tiptap/extension-mention";
import { VueRenderer } from "@tiptap/vue-3";
import tippy from "tippy.js";

import AutocompleteControl from "./AutocompleteControl.vue";
import MentionList from "./MentionList.vue";
import ConditionBuilder from "../components/condition_builder/ConditionBuilder.vue";
import { compileSegmentsToJinja, compileConditionTree } from "../utils/text_generator";

/**
 * SegmentEditor — Recursive inline component for nested segment lists within conditional branches.
 * Defined as a named component to allow self-reference without circular imports.
 */
const SegmentEditor = defineComponent({
	name: "SegmentEditor",
	props: {
		segments: { type: Array, default: () => [] },
		variableOptions: { type: Array, default: () => [] },
		docFieldOptions: { type: Array, default: () => [] },
		readOnly: { type: Boolean, default: false },
	},
	emits: ["update:segments"],
	setup(props, { emit }) {
		function addSeg(type) {
			const list = [...(props.segments || [])];
			if (type === "text") list.push({ type: "text", content: "", _key: Date.now() });
			else if (type === "variable")
				list.push({ type: "variable", path: "", _key: Date.now() });
			emit("update:segments", list);
		}

		function removeSeg(idx) {
			const list = [...(props.segments || [])];
			list.splice(idx, 1);
			emit("update:segments", list);
		}

		function updateSeg(idx, key, val) {
			const list = [...(props.segments || [])];
			list[idx] = { ...list[idx], [key]: val };
			emit("update:segments", list);
		}

		return { addSeg, removeSeg, updateSeg };
	},
	template: `
		<div class="tg-nested-segments">
			<div v-for="(seg, i) in segments" :key="i" class="tg-nested-seg">
				<div v-if="seg.type === 'text'" class="tg-nested-text">
					<input
						class="form-control input-xs"
						:value="seg.content || seg.text || ''"
						:disabled="readOnly"
						:placeholder="__('Text…')"
						@input="updateSeg(i, 'content', $event.target.value)"
					/>
					<button v-if="!readOnly" class="tg-seg-remove-sm" @click="removeSeg(i)">
						<i class="fa fa-times"></i>
					</button>
				</div>
				<div v-else-if="seg.type === 'variable'" class="tg-nested-var">
					<AutocompleteControl
						:df="{ fieldtype: 'Autocomplete', label: '' }"
						:options="variableOptions"
						:modelValue="seg.path"
						:read_only="readOnly"
						:hideLabel="true"
						@update:modelValue="(val) => updateSeg(i, 'path', val || '')"
					/>
					<button v-if="!readOnly" class="tg-seg-remove-sm" @click="removeSeg(i)">
						<i class="fa fa-times"></i>
					</button>
				</div>
			</div>
			<div v-if="!readOnly" class="tg-nested-add">
				<button class="tg-add-btn-sm" @click="addSeg('text')">+ {{ __("Text") }}</button>
				<button class="tg-add-btn-sm" @click="addSeg('variable')">+ {{ __("Var") }}</button>
			</div>
			<div v-if="!segments.length" class="tg-nested-empty">{{ __("(empty)") }}</div>
		</div>
	`,
	components: { AutocompleteControl },
});

const props = defineProps({
	df: { type: Object, default: null },
	modelValue: { type: [Object, String], default: null },
	templateValue: { type: String, default: "" },
	read_only: { type: Boolean, default: false },
	variableOptions: { type: Array, default: () => [] },
	docFieldOptions: { type: Array, default: () => [] },
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const readOnly = computed(() => !!props.read_only || !!props.df?.read_only);
const expandedCondIdx = ref(null);

// ─── Internal UI State ───
const ui = ref({ version: 2, segments: [] });
let emitting = false;

// Editor instances for text segments
const editorInstances = new Map();

function genKey() {
	return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

function makeSegment(type) {
	if (type === "text") return { type: "text", content: "", _key: genKey() };
	if (type === "variable") return { type: "variable", path: "", _key: genKey() };
	if (type === "conditional") {
		return {
			type: "conditional",
			condition: { op: "and", conditions: [] },
			then_segments: [],
			elif_branches: [],
			else_segments: [],
			_key: genKey(),
		};
	}
	return { type: "text", content: "", _key: genKey() };
}

function addSegment(type) {
	ui.value.segments.push(makeSegment(type));
}

function removeSegment(idx) {
	const seg = ui.value.segments[idx];
	if (seg && seg._key && editorInstances.has(seg._key)) {
		editorInstances.get(seg._key).destroy();
		editorInstances.delete(seg._key);
	}
	ui.value.segments.splice(idx, 1);
}

function addElif(segment) {
	if (!segment.elif_branches) segment.elif_branches = [];
	segment.elif_branches.push({
		condition: { op: "and", conditions: [] },
		segments: [],
	});
}

function removeElif(segment, eIdx) {
	if (!segment.elif_branches) return;
	segment.elif_branches.splice(eIdx, 1);
}

function toggleConditionEditor(idx) {
	expandedCondIdx.value = expandedCondIdx.value === idx ? null : idx;
}

// ─── Condition Summary ───
function conditionSummary(condition) {
	if (!condition) return "";
	try {
		const expr = compileConditionTree(condition);
		if (!expr || expr === "True") return "";
		// Truncate long expressions
		return expr.length > 80 ? expr.substring(0, 77) + "…" : expr;
	} catch (e) {
		return "";
	}
}

// ─── TipTap Editors for Text Segments ───

const normalizedVariables = computed(() =>
	(props.variableOptions || []).map((opt) => {
		if (typeof opt === "string") return { label: opt, value: opt };
		return { label: opt?.label || opt?.value || "", value: opt?.value || "" };
	})
);

function createMentionSuggestion() {
	return {
		items: ({ query }) => {
			const q = (query || "").toLowerCase();
			return normalizedVariables.value
				.filter(
					(v) =>
						(v.value || "").toLowerCase().includes(q) ||
						(v.label || "").toLowerCase().includes(q)
				)
				.slice(0, 15);
		},
		render: () => {
			let component;
			let popup;
			return {
				onStart: (props) => {
					component = new VueRenderer(MentionList, {
						props,
						editor: props.editor,
					});
					if (!props.clientRect) return;
					popup = tippy("body", {
						getReferenceClientRect: props.clientRect,
						appendTo: () => document.body,
						content: component.element,
						showOnCreate: true,
						interactive: true,
						trigger: "manual",
						placement: "bottom-start",
					});
				},
				onUpdate(props) {
					component?.updateProps(props);
					if (popup && popup[0]) {
						popup[0].setProps({
							getReferenceClientRect: props.clientRect,
						});
					}
				},
				onKeyDown(props) {
					if (props.event.key === "Escape") {
						popup?.[0]?.hide();
						return true;
					}
					return component?.ref?.onKeyDown(props);
				},
				onExit() {
					popup?.[0]?.destroy();
					component?.destroy();
				},
			};
		},
	};
}

function getOrCreateEditor(segment, idx) {
	const key = segment._key || `seg_${idx}`;
	if (editorInstances.has(key)) return editorInstances.get(key);

	const content = mentionContentToHtml(segment.content || segment.text || "");

	const editor = new Editor({
		extensions: [
			StarterKit.configure({
				heading: false,
				bold: false,
				italic: false,
				strike: false,
				code: false,
				codeBlock: false,
				blockquote: false,
				bulletList: false,
				orderedList: false,
				horizontalRule: false,
			}),
			Mention.configure({
				HTMLAttributes: { class: "mention" },
				renderLabel({ node }) {
					return `@${node.attrs.id || ""}`;
				},
				suggestion: createMentionSuggestion(),
			}),
		],
		content,
		editable: !readOnly.value,
		onUpdate: ({ editor: ed }) => {
			// Convert HTML back to text with {{ var }} markers
			segment.content = htmlToTextContent(ed.getHTML());
		},
	});

	editorInstances.set(key, editor);
	return editor;
}

function mentionContentToHtml(text) {
	if (!text) return "<p></p>";
	// Convert {{ var }} to mention spans
	let html = String(text).replace(
		/\{\{\s*([^}]+?)\s*\}\}/g,
		(_, v) =>
			`<span data-type="mention" data-id="${v.trim()}" class="mention">@${v.trim()}</span>`
	);
	if (!html.startsWith("<p>")) html = "<p>" + html + "</p>";
	return html;
}

function htmlToTextContent(html) {
	if (!html) return "";
	const div = document.createElement("div");
	div.innerHTML = html;
	function walk(node) {
		if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
		if (node.nodeType === Node.ELEMENT_NODE) {
			if (node.getAttribute("data-type") === "mention") {
				const id = node.getAttribute("data-id") || "";
				return id ? `{{ ${id} }}` : "";
			}
			const tag = node.tagName.toLowerCase();
			let children = "";
			for (const c of node.childNodes) children += walk(c);
			if (tag === "br") return "\n";
			if (tag === "p" && children) return children;
			return children;
		}
		return "";
	}
	let r = "";
	for (const c of div.childNodes) r += walk(c);
	return r;
}

function focusMiniEditor(refEl) {
	// refEl may be an array from template ref
	const el = Array.isArray(refEl) ? refEl[0] : refEl;
	if (el?.$el) {
		const proseMirror = el.$el.querySelector(".ProseMirror");
		if (proseMirror) proseMirror.focus();
	}
}

// ─── Compiled Jinja ───
const compiledJinja = computed(() => compileSegmentsToJinja(ui.value.segments));

// ─── Model Sync ───

function normalizeModel(val) {
	if (val && typeof val === "object" && val.segments) {
		return {
			version: val.version || 2,
			segments: (val.segments || []).map((s) => ({ ...s, _key: s._key || genKey() })),
		};
	}
	if (typeof val === "string" && val.trim()) {
		try {
			const parsed = JSON.parse(val);
			if (parsed && parsed.segments) return normalizeModel(parsed);
		} catch (e) {
			// Not JSON — could be a raw Jinja string; wrap as text segment
		}
		return { version: 2, segments: [{ type: "text", content: val, _key: genKey() }] };
	}
	return { version: 2, segments: [] };
}

watch(
	() => [props.modelValue, props.templateValue],
	([val, tmpl]) => {
		if (emitting) return;
		ui.value = normalizeModel(val || tmpl);
	},
	{ immediate: true, deep: true }
);

watch(
	ui,
	() => {
		emitting = true;
		const payload = JSON.parse(JSON.stringify(ui.value));
		// Clean internal keys
		const clean = (segs) =>
			(segs || []).map((s) => {
				const c = { ...s };
				delete c._key;
				if (c.then_segments) c.then_segments = clean(c.then_segments);
				if (c.else_segments) c.else_segments = clean(c.else_segments);
				if (c.elif_branches)
					c.elif_branches = c.elif_branches.map((b) => ({
						...b,
						segments: clean(b.segments || []),
					}));
				return c;
			});
		payload.segments = clean(payload.segments);
		emit("update:modelValue", payload);
		setTimeout(() => {
			emitting = false;
		}, 0);
	},
	{ deep: true }
);

// Cleanup editors on unmount
import { onBeforeUnmount } from "vue";
onBeforeUnmount(() => {
	for (const ed of editorInstances.values()) {
		ed.destroy();
	}
	editorInstances.clear();
});
</script>

<style scoped>
.text-generator-control {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

/* ─── Segments ─── */
.tg-segments {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.tg-segment {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	overflow: hidden;
}

.tg-seg-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 4px 8px;
	background: #f8fafc;
	border-bottom: 1px solid var(--border-color);
}

.tg-seg-badge {
	font-size: 10px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	padding: 1px 6px;
	border-radius: 3px;
}

.tg-badge-text {
	background: #e8f5e9;
	color: #2e7d32;
}

.tg-badge-var {
	background: #e3f2fd;
	color: #1565c0;
}

.tg-badge-cond {
	background: #fff3e0;
	color: #e65100;
	display: inline-flex;
	align-items: center;
	gap: 4px;
}

.tg-seg-remove {
	background: transparent;
	border: none;
	color: var(--text-muted);
	cursor: pointer;
	padding: 2px 4px;
	font-size: 11px;
	transition: color 0.1s;
}

.tg-seg-remove:hover {
	color: var(--red-500, #e53e3e);
}

/* ─── Text Segment Editor ─── */
.tg-segment-text {
	background: var(--bg-light, #fff);
}

.tg-editor-mini {
	padding: 6px 10px;
	min-height: 36px;
	cursor: text;
}

.tg-editor-mini :deep(.ProseMirror) {
	outline: none;
	min-height: 24px;
	font-size: 13px;
	line-height: 1.6;
}

.tg-editor-mini :deep(.ProseMirror p) {
	margin: 0;
}

.tg-editor-mini :deep(.mention) {
	display: inline-flex;
	align-items: center;
	padding: 0px 6px;
	border-radius: 4px;
	background: linear-gradient(135deg, #e8f0fe, #d4e4fd);
	color: var(--primary, #2490ef);
	font-size: 12px;
	font-weight: 500;
	font-family: var(--font-monospace, monospace);
	white-space: nowrap;
	border: 1px solid rgba(36, 144, 239, 0.2);
}

/* ─── Variable Segment ─── */
.tg-segment-variable {
	background: var(--bg-light, #fff);
	padding-bottom: 6px;
}

.tg-segment-variable .frappe-control {
	padding: 0 8px;
}

/* ─── Conditional Segment ─── */
.tg-segment-cond {
	background: var(--bg-light, #fff);
	display: flex;
	flex-direction: column;
	gap: 0;
}

.tg-cond-card {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 6px 10px;
	margin: 6px 8px;
	background: #f8f9fa;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	cursor: pointer;
	transition: all 0.15s;
}

.tg-cond-card:hover {
	border-color: var(--primary, #2490ef);
	background: #f0f7ff;
}

.tg-cond-card-active {
	border-color: var(--primary, #2490ef);
	box-shadow: 0 0 0 2px rgba(36, 144, 239, 0.1);
}

.tg-cond-card-sm {
	margin: 4px 8px;
	padding: 4px 8px;
}

.tg-cond-summary {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 12px;
	overflow: hidden;
}

.tg-cond-summary i {
	color: var(--text-muted);
	flex-shrink: 0;
}

.tg-cond-summary code {
	font-size: 11px;
	color: var(--text-color);
	background: transparent;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.tg-cond-editor {
	padding: 8px;
	border-top: 1px dashed var(--border-color);
}

/* ─── Branches ─── */
.tg-branch {
	border-top: 1px dashed var(--border-color);
	padding: 6px 8px;
}

.tg-branch-label {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	margin-bottom: 4px;
	display: flex;
	align-items: center;
	gap: 6px;
}

.tg-branch-then {
	color: #2e7d32;
}

.tg-branch-elif {
	color: #e65100;
}

.tg-branch-else {
	color: #c62828;
}

.tg-branch-content {
	padding-left: 8px;
	border-left: 2px solid var(--border-color);
}

.tg-add-elif {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 3px 10px;
	margin: 4px 8px;
	font-size: 11px;
	color: #e65100;
	border: 1px dashed #ffcc80;
	border-radius: 4px;
	background: #fff8e1;
	cursor: pointer;
	transition: all 0.15s;
}

.tg-add-elif:hover {
	background: #fff3e0;
	border-color: #e65100;
}

/* ─── Add Bar ─── */
.tg-add-bar {
	display: flex;
	gap: 6px;
	flex-wrap: wrap;
}

.tg-add-btn {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 5px 12px;
	font-size: 11px;
	font-weight: 500;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	background: var(--bg-light, #fff);
	color: var(--text-color);
	cursor: pointer;
	transition: all 0.15s;
}

.tg-add-btn:hover {
	background: var(--bg-blue, #e8f0fe);
	border-color: var(--primary, #2490ef);
	color: var(--primary, #2490ef);
}

.tg-add-btn-cond {
	color: #e65100;
}

.tg-add-btn-cond:hover {
	border-color: #e65100;
	background: #fff3e0;
	color: #bf360c;
}

/* ─── Preview ─── */
.tg-preview {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 8px 12px;
	background: #f8fafc;
}

.tg-preview-title {
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted);
	margin-bottom: 4px;
	display: flex;
	align-items: center;
	gap: 4px;
}

.tg-preview-code {
	font-size: 11px;
	white-space: pre-wrap;
	word-break: break-all;
	color: var(--text-color);
	background: transparent;
	padding: 0;
	display: block;
}

/* ─── Nested Segments (inside branches) ─── */
:deep(.tg-nested-segments) {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

:deep(.tg-nested-seg) {
	display: flex;
	gap: 4px;
}

:deep(.tg-nested-text),
:deep(.tg-nested-var) {
	display: flex;
	align-items: center;
	gap: 4px;
	flex: 1;
}

:deep(.tg-seg-remove-sm) {
	background: transparent;
	border: none;
	color: var(--text-muted);
	cursor: pointer;
	font-size: 10px;
	padding: 2px;
}

:deep(.tg-seg-remove-sm:hover) {
	color: var(--red-500, #e53e3e);
}

:deep(.tg-nested-add) {
	display: flex;
	gap: 4px;
}

:deep(.tg-add-btn-sm) {
	font-size: 10px;
	padding: 2px 6px;
	border: 1px dashed var(--border-color);
	border-radius: 4px;
	background: transparent;
	color: var(--text-muted);
	cursor: pointer;
}

:deep(.tg-add-btn-sm:hover) {
	background: var(--bg-blue, #e8f0fe);
	color: var(--primary);
	border-color: var(--primary);
}

:deep(.tg-nested-empty) {
	font-size: 11px;
	color: var(--text-muted);
	padding: 4px;
}
</style>
