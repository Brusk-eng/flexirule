/**
 * FlexiRule Runtime Bundle
 *
 * This bundle file imports all FlexiRule runtime modules in the correct order.
 * Include this in your app to make the runtime available.
 *
 * Usage: Add to hooks.py in app_include_js or build as a separate bundle.
 */

// Namespace
frappe.provide("flexirule");
frappe.provide("flexirule.utils");
frappe.provide("flexirule.adapters");

// 1. Utils (no dependencies)
import "./flexirule/utils/eval.js";
import "./flexirule/utils/dom.js";

// 2. Controls (depends on utils)
import "./flexirule/controls/control_factory.js";
import "./flexirule/controls/field_selector.js";
import "./flexirule/controls/docfield_widget.js";

// 3. Core (depends on utils, controls)
import "./flexirule/core/dependency_engine.js";
import "./flexirule/core/configurable_action.js";
import "./flexirule/core/ui_runtime.js";

// 4. Table (depends on core, controls)
import "./flexirule/table/flexi_table_schema.js";
import "./flexirule/table/flexi_table_row.js";
import "./flexirule/table/flexi_table.js";

// 5. Adapters (depends on everything above)
import "./flexirule/adapters/adapter_bridge.js";

// 6. Integration
import "./flexirule/integration/rule_builder_bridge.js";

console.log("[FlexiRule] Runtime loaded");
