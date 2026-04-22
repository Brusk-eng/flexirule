# Salesforce Flow to FlexiRule Reference: UI Interaction Patterns

This document maps how visual elements and user input are managed in Salesforce Screen Flows and proposes how FlexiRule can accomplish similar requirements.

## 1. Declarative Screen Building

**Description:**
Salesforce Screen Flows allow administrators to drag and drop UI components (Text, Picklist, Display Text, custom Aura/LWC) onto a Screen node. The flow pauses, displays the screen to the end user, collects input, and resumes execution.

**Example:**
A "Return Merchandise" flow asks the user for the Order Number, displays Order Details, and asks for the Return Reason via a picklist.

**Mapping to FlexiRule:**
- **Challenges:** FlexiRule primarily acts as a backend Rules Engine (Record-Triggered). Pausing execution to wait for user input breaks the synchronous nature of standard Frappe hooks.
- **Solution 1 (Dialogs):** FlexiRule could offer `Client Script Generation`. A rule bounded to `Client Script` level (instead of Server hook) that triggers a Frappe Dialog. 
- **Solution 2 (Web Form/Page):** A specific `Screen Rule` type that maps nodes to Frappe Web Forms or Custom Pages. Each node represents a distinct Form Step.
- **Current State:** FlexiRule v1 does not deeply support interactive, multi-step Screen flows like Salesforce yet.

## 2. Dynamic Component Visibility

**Description:**
Salesforce Screens support conditional visibility on fields. A "Specify Reason" text area only appears if "Other" is selected in the Dropdown above it.

**Mapping to FlexiRule:**
- **Counterpart:** Frappe `depends_on` logic in DocTypes or Dialog fields.
- **Implementation:** If FlexiRule generates Client Scripts or dynamic Dialogs, it must compile condition logic into JavaScript `depends_on` strings.

## 3. Data Table and Record Selection

**Description:**
Salesforce Screen Flows provide advanced Data Table components out-of-the-box, allowing users to view, sort, and select multiple records querying from a collection variable.

**Mapping to FlexiRule:**
- **Counterpart:** Frappe `Link` fields, `Table` (Child Table) fields, or custom HTML blocks in Dialogs.

## 4. Contextual Launching (Action Buttons)

**Description:**
Flows are launched from Quick Actions on Record Detail pages in Salesforce. The Action passes the current record's ID into a pre-defined `recordId` variable.

**Mapping to FlexiRule:**
- **Counterpart:** Frappe Custom Actions (buttons via `Custom Script` or `Workflow`).
- **Implementation:** Allow users to define a Rule with Trigger = `Action Button`. The FlexiRule framework dynamically injects a Custom Script into the target DocType that adds a button to the Frappe UI (`frm.add_custom_button()`), which triggers an API call (`frappe.call`) to invoke the autolaunched Rule on the backend, passing `doc.name`.
