# Salesforce Flow to FlexiRule Reference: Flow Types and Execution

This document maps Salesforce Flow types and execution models to FlexiRule, aiming to provide architectural guidance.

## Salesforce Flow Types

### 1. Record-Triggered Flow
**Description:** Executes when a Salesforce record is created, updated, or deleted. Can be configured to run before save (fast field updates) or after save (actions and related records).
**Example:** Send an email alert when an Opportunity's stage changes to 'Closed Won'.

**Mapping to FlexiRule:**
- Maps to FlexiRule's `Rule` where the primary construct is a Document Event Trigger.
- **Before Save** maps to `before_save`, `validate`, `before_insert` Frappe hooks.
- **After Save** maps to `on_update`, `after_insert`, `on_submit` Frappe hooks.
- FlexiRule needs a `Trigger Node` capturing the `DocType`, `Event`, and initial Document Context.

### 2. Scheduled-Triggered Flow
**Description:** Runs in the background at a specific time and frequency (Daily, Weekly) for a batch of records.
**Example:** Every Friday, find all Case records older than 30 days and close them.

**Mapping to FlexiRule:**
- Maps to Frappe Scheduled actions (Daily, Weekly, Monthly hooks).
- FlexiRule requires a `Schedule Trigger Node` where frequency is selected, and it returns a list/collection of records that enter the Flow Loop.

### 3. Screen Flow
**Description:** A UI-based flow that guides users through a wizard or form to collect data, query records, and create updates.
**Example:** A script for Customer Support agents taking call details.

**Mapping to FlexiRule:**
- Not directly analogous unless FlexiRule builds Frappe Page wizards or Dialogs intercepting user interactions. Partially maps to custom server actions triggered by buttons (`doc._action`), opening Dialogs on the Frappe frontend.

### 4. Autolaunched Flow (No Trigger)
**Description:** Runs in the background when invoked by Apex, Process Builder, REST API, or another Flow (Subflow).
**Example:** A utility flow to calculate tax that is called from multiple other flows.

**Mapping to FlexiRule:**
- Directly maps to FlexiRule `Sub-Rule` or a server callable method (`frappe.call`).
- FlexiRule uses the `Process Node` or `Sub-Rule Node` to invoke another rule, passing variables down and returning variables.

## Execution Model
Salesforce operates with transaction governance limits. Variables and collections are passed linearly.
- **FlexiRule Counterpart:** Python Server Scripts and execution engine passing `doc` and generic `context` dictionaries between nodes in a Directed Acyclic Graph (DAG) pattern.
