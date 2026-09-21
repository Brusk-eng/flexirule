import "@testing-library/cypress/add-commands";
import "@4tw/cypress-drag-drop";
import "cypress-real-events/support";

Cypress.Commands.add("login", (email, password) => {
	if (!email) {
		email = Cypress.config("testUser") || "Administrator";
	}
	if (!password) {
		password = Cypress.env("adminPassword");
	}
	return cy.session(
		[email, password] || "",
		() => {
			return cy.request({
				url: "/api/method/login",
				method: "POST",
				body: {
					usr: email,
					pwd: password,
				},
			});
		},
		{
			cacheAcrossSpecs: true,
		}
	);
});

Cypress.Commands.add("call", (method, args) => {
	return cy
		.window()
		.its("frappe.csrf_token")
		.then((csrf_token) => {
			return cy
				.request({
					url: `/api/method/${method}`,
					method: "POST",
					body: args,
					headers: {
						Accept: "application/json",
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token": csrf_token,
					},
				})
				.then((res) => {
					expect(res.status).eq(200);
					if (method === "logout") {
						Cypress.session.clearAllSavedSessions();
					}
					return res.body;
				});
		});
});

Cypress.Commands.add("fill_field", (fieldname, value, fieldtype = "Data") => {
	cy.get_field(fieldname, fieldtype).as("input");

	if (fieldtype === "Select") {
		cy.get("@input").select(value);
	} else {
		cy.get("@input").type(value, {
			waitForAnimations: false,
			parseSpecialCharSequences: false,
			force: true,
			delay: 50,
		});
	}
	return cy.get("@input");
});

Cypress.Commands.add("get_field", (fieldname, fieldtype = "Data") => {
	let field_element = fieldtype === "Select" ? "select" : "input";
	let selector = `[data-fieldname="${fieldname}"] ${field_element}:visible`;

	return cy.get(selector).first();
});

Cypress.Commands.add("new_form", (doctype) => {
	let dt_in_route = doctype.toLowerCase().replace(/ /g, "-");
	cy.visit(`/app/${dt_in_route}/new`);
	cy.get(".page-head", { timeout: 30000 }).should("exist");
});

Cypress.Commands.add("save", () => {
	cy.intercept("/api/method/frappe.desk.form.save.savedocs").as("save_call");
	cy.get(`.page-container:visible button[data-label="Save"]`).click({ force: true });
	cy.wait("@save_call");
});

Cypress.Commands.add("insert_doc", (doctype, args, ignore_duplicate) => {
	if (!args.doctype) {
		args.doctype = doctype;
	}
	return cy
		.window()
		.its("frappe.csrf_token")
		.then((csrf_token) => {
			return cy
				.request({
					method: "POST",
					url: `/api/resource/${doctype}`,
					body: args,
					headers: {
						Accept: "application/json",
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token": csrf_token,
					},
					failOnStatusCode: !ignore_duplicate,
				})
				.then((res) => {
					let status_codes = [200];
					if (ignore_duplicate) {
						status_codes.push(409);
					}
					expect(res.status).to.be.oneOf(status_codes);
					return res.body.data;
				});
		});
});
