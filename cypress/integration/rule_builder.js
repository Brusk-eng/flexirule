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

	it("6. Rule Configuration Modal - Full-Modal Raw Configuration Transition", () => {
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
	it("7. Whole-Rule save keeps shared return-schema policy available", () => {
		const ruleName = `Rule_Contract_Save_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			cy.window().then((win) => {
				const contracts = win.flexirule?.contracts;
				expect(contracts, "shared contracts API").to.exist;
				expect(contracts.requiresReturnVariable, "canonical requirement helper").to.be.a(
					"function"
				);
				for (const type of ["boolean", "array", "string", "number", "integer"]) {
					expect(contracts.hasResolvedOutputSchema({ type }), type).to.equal(true);
				}
				expect(contracts.hasResolvedOutputSchema({ type: "unknown" })).to.equal(false);
			});

			// Save through the whole-Rule path (not only the action config modal),
			// then reload to ensure the shared contract module remains initialized.
			ruleBuilderPage.addNodeFromEdge("Assignment", "Contract Save Regression");
			ruleBuilderPage.saveRule();
			cy.reload();
			cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
			cy.window()
				.its("flexirule.contracts.requiresReturnVariable")
				.should("be.a", "function");
		});
	});

	it("8. Empty mutation allowlists reject configured mutation modes", () => {
		cy.create_test_rule_backend({ rule_name: `Rule_Empty_Mutation_Allowlist_${Date.now()}` }).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			cy.window().then((win) => {
				const contracts = win.flexirule?.contracts;
				expect(contracts, "shared contracts API").to.exist;
				expect(contracts.isMutationModeAllowed, "shared mutation policy helper").to.be.a(
					"function"
				);
				expect(
					contracts.isMutationModeAllowed("Set Context Variable", []),
					"an explicitly empty allowlist permits no mutation modes"
				).to.equal(false);
				expect(
					contracts.isMutationModeAllowed("Set Context Variable", ["Set Context Variable"])
				).to.equal(true);
				expect(contracts.isMutationModeAllowed(null, [])).to.equal(true);
			});
		});
	});

	it("9. Whole-Rule save rejects a Process operation missing its required return variable", () => {
		const ruleName = `Rule_Process_Return_Required_${Date.now()}`;
		const processName = "Validation";
		const operationName = "on_field_change";
		const processConfig = {
			watched_fields: ["email_id", "phone", "mobile_no"],
			match_mode: "Any",
			store_result: "changed_fields",
		};

		cy.create_test_rule_backend({ rule_name: ruleName }).then((ruleDoc) => {
			ruleBuilderPage.visitRule(ruleDoc.name);
			ruleBuilderPage.openVisualBuilder();
			ruleBuilderPage.addNodeFromEdge("Process", "Missing Return Variable Process");

			cy.window().then(async (win) => {
				const builder = win.fxrRuleBuilder;
				const store = builder?.ruleStore;
				const contracts = win.flexirule?.contracts;
				expect(store, "whole-Rule builder store").to.exist;
				expect(contracts, "shared contracts API").to.exist;

				const process = store.processes.find((item) => item.name === processName);
				expect(process, "installed Process used by this regression").to.exist;
				expect(
					(process.operations || []).some((item) => item.func_name === operationName),
					"the selected operation exists on the Process"
				).to.equal(true);

				const node = store.nodes.find(
					(item) => item.data?.action_label === "Missing Return Variable Process"
				);
				expect(node, "Process node on the Rule graph").to.exist;
				Object.assign(node.data, {
					action_type: "Process",
					process_name: processName,
					operation: operationName,
					config: processConfig,
					return_type: "Yes / No",
					return_variable: null,
					mutation_mode: null,
					is_enabled: 1,
				});

				const frontendContractResult = contracts.validateAgainstContract(node.data);
				expect(contracts.requiresReturnVariable(node.data, {
					processName,
					operation: operationName,
				})).to.equal(true);
				expect(frontendContractResult.valid).to.equal(false);
				expect(frontendContractResult.errors.join("\\n")).to.match(/Return Variable Name/i);

				// Run the same Process action through the backend validator used by
				// Rule save, then assert its structured error before attempting UI save.
				const processActionId = node.data.action_id || node.id;
				const processAction = {
					action_id: processActionId,
					action_type: "Process",
					action_label: "Missing Return Variable Process",
					process_name: processName,
					operation: operationName,
					config: JSON.stringify(processConfig),
					return_type: "Yes / No",
					return_variable: null,
					mutation_mode: null,
					is_enabled: 1,
				};
				const backendValidation = await win.frappe.call({
					method: "flexirule.ruleflow.api.validate_rule_document",
					args: {
						mode: "draft",
						doc: {
							doctype: "Rule",
							name: ruleDoc.name,
							is_active: 0,
							trigger_type: "DocType Event",
						document_type: "Contact",
							trigger_event: "After Save",
							actions: [
								{
									action_id: "root",
									action_type: "Entry Action",
									action_label: "Start",
									is_enabled: 1,
									next_step_if_true: processActionId,
								},
								processAction,
							],
						},
					},
				});
				expect(backendValidation.message?.valid).to.equal(false);
				expect((backendValidation.message?.errors || []).join("\\n")).to.match(
					/ Missing Return Variable Process .*Return Variable Name/i
				);
			});

			cy.window().then((win) => {
				cy.stub(win.frappe, "msgprint").as("saveValidationMessage");
			});
			cy.get('button:contains("Save Rule")').click();
			cy.get("@saveValidationMessage").should("have.been.called");
			cy.get("@saveValidationMessage").should((stub) => {
				const messages = stub.getCalls().map((call) => JSON.stringify(call.args[0])).join("\\n");
				expect(messages).to.match(/Validation Error/i);
				expect(messages).to.match(/Return Variable Name/i);
			});
		});
	});
});
