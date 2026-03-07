import {
	ref,
	computed,
	watch,
	reactive,
	onMounted,
	onUnmounted,
	onBeforeUnmount,
	watchEffect,
	nextTick,
	provide,
	inject,
	useSlots,
} from "vue";
import LinkControl from "./controls/LinkControl.vue";
import DataControl from "./controls/DataControl.vue";
import SelectControl from "./controls/SelectControl.vue";
import CheckControl from "./controls/CheckControl.vue";
import TextControl from "./controls/TextControl.vue";
import CodeControl from "./controls/CodeControl.vue";
import MultiCheckControl from "./controls/MultiCheckControl.vue";
import AutocompleteControl from "./controls/AutocompleteControl.vue";
import FieldPickerControl from "./controls/FieldPickerControl.vue";
import InlineTableControl from "./controls/InlineTableControl.vue";
import MultiFieldPickerControl from "./controls/MultiFieldPickerControl.vue";
import MultiSelectControl from "./controls/MultiSelectControl.vue";
import PercentSliderControl from "./controls/PercentSliderControl.vue";

export function registerGlobalComponents(app) {
	app.component("LinkControl", LinkControl)
		.component("DataControl", DataControl)
		.component("SelectControl", SelectControl)
		.component("CheckControl", CheckControl)
		.component("TextControl", TextControl)
		.component("CodeControl", CodeControl)
		.component("MultiCheckControl", MultiCheckControl)
		.component("AutocompleteControl", AutocompleteControl)
		.component("FieldPickerControl", FieldPickerControl)
		.component("InlineTableControl", InlineTableControl)
		.component("MultiFieldPickerControl", MultiFieldPickerControl)
		.component("MultiSelectControl", MultiSelectControl)
		.component("PercentSliderControl", PercentSliderControl);
}

export function registerVueGlobals(app) {
	const globals = {
		ref,
		computed,
		watch,
		reactive,
		onMounted,
		onUnmounted,
		onBeforeUnmount,
		watchEffect,
		nextTick,
		provide,
		inject,
		useSlots,
		__: window.__ || ((s) => s),
	};

	// Expose to window for script setup availability without imports
	Object.keys(globals).forEach((key) => {
		window[key] = globals[key];
	});

	// Expose to app for templates
	Object.keys(globals).forEach((key) => {
		app.config.globalProperties[key] = globals[key];
	});
}
