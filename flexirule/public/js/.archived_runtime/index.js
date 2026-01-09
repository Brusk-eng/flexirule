/**
 * FlexiRule Frontend Runtime
 *
 * This file serves as the main entry point for the FlexiRule runtime.
 * It imports all necessary modules and ensures they are attached to
 * the global `flexirule` namespace.
 */

// Define namespaces
frappe.provide("flexirule");
frappe.provide("flexirule.utils");
frappe.provide("flexirule.adapters");
frappe.provide("flexirule.integration");

// 1. Utils
import "./utils/eval.js";
import "./utils/dom.js";
import "./utils/meta.js";

// 2. Controls
import "./controls/control_factory.js";
import "./controls/field_selector.js";
import "./controls/docfield_widget.js";

// 3. Core
import "./core/dependency_engine.js";
import "./core/configurable_action.js";
import "./core/ui_runtime.js";

// 4. Table
import "./table/flexi_table_schema.js";
import "./table/flexi_table_row.js";
import "./table/flexi_table.js";

// 6. Integration
import "./integration/rule_builder_bridge.js";

// 7. Legacy Rule Builder Components (as fallback)
import "../rule_builder/configurable_action.js";

/**
 * Note: Individual files attach themselves to the flexirule namespace
 * using side-effects. This file just ensures correct loading order.
 */

console.log("[FlexiRule] Runtime Entry Initialized");
