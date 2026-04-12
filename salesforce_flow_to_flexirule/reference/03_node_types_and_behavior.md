# 3. Node Types & Behavior

Salesforce Flow groups nodes into Data, Logic, and Action categories.

---

## 3.1 Assignment
**Description:**
Sets or updates values in variables, collection variables, or record variables.

**Example:**
Add 1 to a counter variable inside a Loop.

**How this maps to Flexirule:**
Flexirule should have a specific "Assignment" Action subtype to modify the execution context.
**What needs to be implemented or improved:**
- Standardize Assignment as a Node Type under the "Logic & Flow Control" category. Require backend schema for assignment syntax.

---

## 3.2 Decision
**Description:**
Evaluates a set of conditions and routes users down one of several paths based on the outcome.

**Example:**
Check if Lead Rating is "Hot" (Path 1) or "Cold" (Path 2).

**How this maps to Flexirule:**
Maps to the "Condition" node.
**What needs to be implemented or improved:**
- Ensure Condition nodes cleanly support multiple outbound edges for different paths in the Vue Canvas.

---

## 3.3 Loop
**Description:**
Iterates over a collection (array) of records or values, executing a set of nodes for each item.

**Example:**
Loop through a list of Opportunity Line Items to calculate total tax.

**How this maps to Flexirule:**
Currently under-developed in Flexirule. 
**What needs to be implemented or improved:**
- Implement an explicit Loop/Iterator node. The canvas needs to visually indicate the "For Each" and "After Loop" paths.

---

## 3.4 Data Operations (Get/Create/Update/Delete Records)
**Description:**
Interacts directly with the database to read, insert, modify, or erase records.

**Example:**
Get all Accounts where State = "NY".

**How this maps to Flexirule:**
Maps to specific Frappe ORM actions (e.g., `frappe.get_doc`, `frappe.db.insert`).
**What needs to be implemented or improved:**
- Represent these as explicit "Data & Record Operations" nodes.
- Make the configuration UI perfectly aligned with Frappe DocType schema via API.

---

## 3.5 Subflow
**Description:**
Calls another Flow. Useful for common, repeatable logic.

**Example:**
Calling a generic "Send Error Email" Flow from multiple different parent Flows.

**How this maps to Flexirule:**
Maps to the "SubRule" logic in Flexirule.
**What needs to be implemented or improved:**
- Improve the Vue Canvas to show SubRules transparently without buggy rendering.
- Maintain consistent parameter passing into the SubRule context from the parent rule.
