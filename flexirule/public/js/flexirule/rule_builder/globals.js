import LinkControl from "./controls/LinkControl.vue";
import DataControl from "./controls/DataControl.vue";
import SelectControl from "./controls/SelectControl.vue";
import CheckControl from "./controls/CheckControl.vue";
import TextControl from "./controls/TextControl.vue";
import CodeControl from "./controls/CodeControl.vue";
import MultiCheckControl from "./controls/MultiCheckControl.vue";

export function registerGlobalComponents(app) {
	app.component("LinkControl", LinkControl)
		.component("DataControl", DataControl)
		.component("SelectControl", SelectControl)
		.component("CheckControl", CheckControl)
		.component("TextControl", TextControl)
		.component("CodeControl", CodeControl)
		.component("MultiCheckControl", MultiCheckControl);
}
