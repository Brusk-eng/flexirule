import { ruleBuilderPage } from "../support/pages/RuleBuilderPage";

describe("FlexiRule UI Test Suite", () => {
	beforeEach(() => {
		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	it("1. Rule Creation & Visual Builder Launch", () => {
		const ruleName = `Rule_Create_${Date.now()}`;

		cy.new_form("Rule");
		cy.fill_field("rule_name", ruleName);
		cy.fill_field("document_type", "Contact", "Link");
		cy.get('select[data-fieldname="trigger_event"]').select("After Save");
		cy.save();

		// Open visual builder
		ruleBuilderPage.openVisualBuilder();
		cy.get(".vue-flow__node").should("exist");
	});

	it("2. Canvas Node Addition, Configuration & Persistence", () => {
		const ruleName = `Rule_Persist_${Date.now()}`;

		// Fast backend creation of rule document
		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			// Add Assignment Action
			ruleBuilderPage.addNodeFromEdge("Assignment", "Set Initial State");
			cy.get(".vue-flow__node .assignment").should("be.visible");

			// Configure Node
			ruleBuilderPage.selectNode("assignment");
			ruleBuilderPage.configureNodeLabel("Updated State Label");
			ruleBuilderPage.closeSettingsPanel();

			// Add Notify Action
			ruleBuilderPage.addNodeFromEdge("Notify", "Notify Manager");
			cy.get(".vue-flow__node .notify").should("be.visible");

			// Save
			ruleBuilderPage.saveRule();

			// Reload & Verify Persistence
			cy.reload();
			cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
			cy.get(".vue-flow__node .assignment .node-title").should(
				"contain",
				"Updated State Label"
			);
			cy.get(".vue-flow__node .notify .node-title").should("contain", "Notify Manager");
		});
	});

	it("3. Branching & Condition Node Configuration", () => {
		const ruleName = `Rule_Branch_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			// Add Condition
			ruleBuilderPage.addNodeFromEdge("Condition", "Check Credit Limit");
			cy.get(".vue-flow__node .condition").should("be.visible");

			// True Branch
			ruleBuilderPage.addNodeFromEdge("Assignment", "Approve Branch", "true");
			cy.get(".vue-flow__node .assignment .node-title").should("contain", "Approve Branch");

			// False Branch
			ruleBuilderPage.addNodeFromEdge("Notify", "Reject Branch", "false");
			cy.get(".vue-flow__node .notify .node-title").should("contain", "Reject Branch");

			// Save and verify
			ruleBuilderPage.saveRule();
			cy.reload();
			cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
			cy.get(".vue-flow__node .assignment .node-title").should("contain", "Approve Branch");
			cy.get(".vue-flow__node .notify .node-title").should("contain", "Reject Branch");
		});
	});

	it("4. Action Node Deletion and UI State Update", () => {
		const ruleName = `Rule_Delete_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			ruleBuilderPage.addNodeFromEdge("Stop", "Stop Execution");
			cy.get(".vue-flow__node .stop").should("be.visible");

			// Delete Stop node
			ruleBuilderPage.selectNode("stop");
			ruleBuilderPage.deleteSelectedNode();
			cy.get(".vue-flow__node .stop").should("not.exist");

			ruleBuilderPage.saveRule();
		});
	});

	it("5. Rule Activation & Validation Flow", () => {
		const ruleName = `Rule_Activation_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);

			// Activate rule in form view
			cy.get('input[data-fieldname="is_active"]').check({ force: true });
			cy.save();

			// Reload and verify active check remains
			cy.reload();
			cy.get('input[data-fieldname="is_active"]').should("be.checked");
		});
	});
});
