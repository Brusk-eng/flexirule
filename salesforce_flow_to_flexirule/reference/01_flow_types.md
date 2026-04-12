# 1. Flow Types

Salesforce Flow offers several types of flows to handle different automation scenarios. Each flow type defines HOW and WHEN the flow is invoked.

---

## 1.1 Screen Flow
**Description:**
A Screen Flow is a user interface-driven flow that can accept user input, display information, and guide users through a multi-step process.

**Example:**
A wizard that guides a customer service agent through a script to log a new ticket and captures relevant customer information step-by-step.

**How this maps to Flexirule:**
Currently, Flexirule primarily acts as an invisible backend event-driven engine. A true "Screen Flow" equivalent would require Flexirule to present modal forms or distinct web steps to Frappe users.
**What needs to be implemented or improved:**
- We need to introduce a "Screen / Form Step" node type.
- The rule engine needs to support pausing execution to wait for user input.
- Frontend: The Vue UI should render form steps dynamically based on the rule configuration.

---

## 1.2 Record-Triggered Flow
**Description:**
A Flow that executes automatically in the background when a record is created, updated, or deleted.

**Example:**
When a "Lead" is updated to "Qualified", automatically send an email alert to the sales team and create a "Opportunity" record.

**How this maps to Flexirule:**
Flexirule supports Document Events (e.g., `before_save`, `after_insert`) through its Trigger root node connected to Frappe Document hooks. This is directly analogous to Record-Triggered Flows.
**What needs to be implemented or improved:**
- We need to ensure the Vue Visual Builder properly maps Frappe server-side events (`validate`, `before_save`, `on_submit`) into the Trigger node configuration form without hardcoded logic.
- We need to fetch DocType metadata via API to show available DocTypes and Events dynamically.

---

## 1.3 Scheduled Flow
**Description:**
A Flow that runs at a specific time and frequency (once, daily, weekly) for a batch of records.

**Example:**
Every day at midnight, find all "Subscriptions" that are expiring in 7 days and send them a renewal reminder email.

**How this maps to Flexirule:**
Flexirule maps to scheduled run functionality conceptually similar to Frappe's `Scheduled Job Type`. A rule could be triggered by cron expressions.
**What needs to be implemented or improved:**
- Add a Cron/Scheduled Trigger node option.
- Hook into Frappe's `frappe.enqueue` or standard scheduler to run the rule engine.
- UI must present schedule configuration (daily, weekly, custom cron) pulled dynamically from backend capabilities.

---

## 1.4 Autolaunched Flow
**Description:**
A background Flow that is invoked by another Flow, REST API, Process Builder, Apex, or a Custom Button. It requires no user interaction.

**Example:**
A reusable "Calculate Discount" flow that takes an Item ID as input, performs logic, and returns a calculated price. It is called by other Record-Triggered flows.

**How this maps to Flexirule:**
This directly maps to SubRules or Rules triggered by API / Webhooks. Flexirule's Action nodes or external API calls can hit a specific rule's execution endpoint.
**What needs to be implemented or improved:**
- Standardize the Rule execution API to accept arbitrary JSON payloads mapped to Rule inputs.
- Ensure the SubRule node can elegantly pass data context down to an Autolaunched rule and receive its outputs clearly.
