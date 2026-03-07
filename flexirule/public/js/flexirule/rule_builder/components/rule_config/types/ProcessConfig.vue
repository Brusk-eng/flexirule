<template>
	<div class="process-config-wrapper">
		<div v-if="error" class="alert alert-danger m-3">
			<i class="fa fa-exclamation-triangle"></i> {{ error }}
		</div>
		<div v-if="!engine && !error" class="d-flex justify-content-center p-5">
			<div class="spinner-border text-primary"></div>
		</div>
		<template v-else-if="engine">
			<SchemaRenderer :fields="engine.normalized_fields" :engine="engine" />
			<div v-if="engine.normalized_fields.length === 0" class="p-5 text-center text-muted">
				<p>{{ __("No configuration fields found for this operation.") }}</p>
				<div class="small mt-2 p-2 border rounded bg-light text-left">
					<code>Process: {{ node.data?.process_name }}</code
					><br />
					<code>Operation: {{ node.data?.operation }}</code>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { onMounted, ref, reactive, watch } from "vue";
import ProcessEngine from "../engines/ProcessEngine.js";
import SchemaRenderer from "../SchemaRenderer.vue";
import { useStore } from "../../../store";

const props = defineProps({
	node: Object,
});

const store = useStore();
const engine = ref(null);
const error = ref(null);

let initCounter = 0;

async function initEngine() {
	if (!props.node?.data?.process_name || !props.node?.data?.operation) {
		console.warn("ProcessConfig: Process name or operation missing", props.node?.data);
		return;
	}

	error.value = null;
	const currentInitId = ++initCounter;

	if (engine.value && typeof engine.value.dispose === "function") {
		engine.value.dispose();
	}
	engine.value = null;

	try {
		let configValue = props.node.data.config || {};
		if (typeof configValue === "string") {
			try {
				configValue = JSON.parse(configValue);
			} catch (e) {
				configValue = {};
			}
		}

		const config = reactive(configValue);

		const newEngine = new ProcessEngine({
			process_name: props.node.data.process_name,
			operation_name: props.node.data.operation,
			config: config,
			document_type: store.rule_doc?.document_type,
			doc_meta: store.raw_meta,
			available_variables: await store.getAvailableVariables(props.node.id),
		});

		await newEngine.init();

		if (currentInitId !== initCounter) return;

		engine.value = newEngine;
		props.node.data.config = config;
	} catch (err) {
		if (currentInitId === initCounter) {
			console.error("ProcessConfig: Engine initialization failed", err);
			error.value = err.message || "Unknown error during initialization";
		}
	}
}

onMounted(() => {
	initEngine();
});

watch(
	() => [props.node.data?.process_name, props.node.data?.operation],
	() => {
		initEngine();
	}
);

async function validate() {
	if (!engine.value) return { valid: true };
	return await engine.value.validate();
}

defineExpose({
	validate,
});
</script>

<style scoped>
.process-config-wrapper {
	min-height: 200px;
}
</style>
