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

		// Opening this route loads a separate bundle that also imports contracts.js.
		// The contracts namespace must remain readable, and the builder constructor
		// must be registered after module initialization completes.
		ruleBuilderPage.openVisualBuilder();
		cy.window().its("frappe.ui.RuleBuilder").should("be.a", "function");
		cy.window().its("flexirule.contracts.hasResolvedOutputSchema").should("be.a", "function");
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

	it("5. First Action node configuration save in modal", () => {
		const ruleName = `Rule_ModalSave_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			// Add Assignment Action
			ruleBuilderPage.addNodeFromEdge("Assignment", "Modal Action");

			// Open Rule Configuration Modal
			cy.get(".vue-flow__node .assignment").last().dblclick({ force: true });
			cy.get(".config-modal-container", { timeout: 10000 }).should("be.visible");

			// Change a real field so the modal Save action becomes available.
			cy.get(".config-modal-header h3.editable").should("be.visible").click();
			cy.get(".config-modal-header .title-input")
				.should("be.visible")
				.clear()
				.type("Modal Action Updated")
				.blur();
			cy.get(".config-modal-header h3")
				.should("be.visible")
				.and("contain", "Modal Action Updated");

			// Verify the modal closes on the first Save click.
			cy.get(".config-modal-container .save-action").should("be.visible").click();
			cy.get(".config-modal-container").should("not.exist");

			// Verify canvas reflects the edited label and dirty / save rule state.
			cy.contains(".vue-flow__node", "Modal Action Updated").should("be.visible");
			cy.get('button:contains("Save Rule")').should("be.visible");
		});
	});

	it("6. Canvas save state updates when editing second action after Rule save", () => {
		const ruleName = `Rule_SecondActionEdit_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			// Add first Action node and configure
			ruleBuilderPage.addNodeFromEdge("Assignment", "Action 1");

			// Save Rule canvas and verify baseline established
			ruleBuilderPage.saveRule();
			cy.get('button:contains("Activate Rule")').should("be.visible");

			// Add a second Assignment node using the tested label-prompt flow.
			ruleBuilderPage.addNodeFromEdge("Assignment", "Action 2");

			// Save Rule canvas again
			ruleBuilderPage.saveRule();
			cy.get('button:contains("Activate Rule")').should("be.visible");

			// Open second Action node in modal and edit its label to mark it dirty.
			cy.get(".vue-flow__node .assignment").last().dblclick({ force: true });
			cy.get(".config-modal-container", { timeout: 10000 }).should("be.visible");
			cy.get(".config-modal-header h3.editable").should("be.visible").click();
			cy.get(".config-modal-header .title-input")
				.should("be.visible")
				.clear()
				.type("Action 2 Modified")
				.blur();
			cy.get(".config-modal-header h3")
				.should("be.visible")
				.and("contain", "Action 2 Modified");

			// Save the edited action using the actual modal Save control.
			cy.get(".config-modal-container .save-action").should("be.visible").click();
			cy.get(".config-modal-container").should("not.exist");
			cy.contains(".vue-flow__node", "Action 2 Modified").should("be.visible");

			// Verify primary action changes back to Save Rule
			cy.get('button:contains("Save Rule")')
				.should("be.visible")
				.and("have.class", "btn-primary");

			// Click Save Rule and verify baseline is reset to clean state
			ruleBuilderPage.saveRule();
			cy.get('button:contains("Activate Rule")').should("be.visible");
		});
	});

	it("7. Rule Activation & Validation Flow", () => {
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

	it("8. Rule Configuration Modal - Full-Modal Raw Configuration Transition", () => {
		const ruleName = `Rule_RawConfig_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			// Add Assignment Action
			ruleBuilderPage.addNodeFromEdge("Assignment", "Raw Config Test Action");

			// Open Rule Configuration Modal (double click or node toolbar configure)
			cy.get(".vue-flow__node .assignment").last().dblclick({ force: true });
			cy.get(".config-modal-container", { timeout: 10000 }).should("be.visible");

			// Workspace view initially visible (three panels / workspace container)
			cy.get(".workspace-view-container").should("be.visible");
			cy.get(".full-raw-config-container").should("not.exist");

			// Click Cog button to enter Full-Modal Raw Configuration view
			cy.get('.header-toolbar button[title*="Raw Configuration"]').click();

			// Verify Full-Modal Raw Configuration view is active and workspace is hidden
			cy.get(".full-raw-config-container").should("be.visible");
			cy.get(".workspace-view-container").should("not.exist");
			cy.get(".config-modal-header .header-titles h3").should("contain", "Raw Configuration");

			// Verify Back button exists in header
			cy.get(".btn-back-nav").should("be.visible");

			// Click Back button to return to 3-panel workspace
			cy.get(".btn-back-nav").click();

			// Verify workspace view restored and full raw config container removed
			cy.get(".workspace-view-container").should("be.visible");
			cy.get(".full-raw-config-container").should("not.exist");

			// Close modal
			cy.get(".config-modal-header button.close-action").click();
			cy.get(".config-modal-container").should("not.exist");
		});
	});
});
