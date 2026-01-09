// Copyright (c) 2025, Abdo Ruzaqi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Rule Execution Log", {
	refresh(frm) {
		frm.trigger("render_execution_path");
		frm.trigger("render_context_snapshot");
	},

	render_execution_path(frm) {
		if (!frm.doc.execution_path) return;

		let wrapper = frm.fields_dict.executions_path_html.$wrapper;
		let path = [];
		try {
			path = JSON.parse(frm.doc.execution_path);
		} catch (e) {
			wrapper.html(`<div class="alert alert-warning">Invalid JSON in Execution Path</div>`);
			return;
		}

		if (!path || !path.length) {
			wrapper.html(`<p class="text-muted">${__("No execution path recorded.")}</p>`);
			return;
		}

		// Calculate Durations
		let rows = path
			.map((step, idx) => {
				let next_step = path[idx + 1];
				let duration_ms = 0;

				// If we have a next step, simpler diff
				if (next_step) {
					duration_ms = (next_step.timestamp - step.timestamp) * 1000;
				} else {
					duration_ms = 0;
				}

				// Format Text
				let duration_text = duration_ms > 0 ? `${duration_ms.toFixed(2)} ms` : "-";

				// Helper to Format JSON or Strings
				const format_v = (v) => {
					if (v === undefined || v === null) return "";
					if (typeof v === "string") {
						// Try to parse if it looks like JSON
						try {
							let parsed = JSON.parse(v);
							return `<pre>${JSON.stringify(parsed, null, 2)}</pre>`;
						} catch (e) {
							return frappe.utils.escape_html(v);
						}
					}
					return `<pre>${JSON.stringify(v, null, 2)}</pre>`;
				};

				let details = "";
				if (step.input && Object.keys(step.input).length) {
					details += `<div><span class="text-muted">Input:</span> ${format_v(
						step.input
					)}</div>`;
				}
				if (step.output) {
					// If output is string representation of list like "[{'name': ...}]"
					details += `<div><span class="text-muted">Output:</span> ${format_v(
						step.output
					)}</div>`;
				}
				if (step.error) {
					details += `<div class="text-danger"><strong>Error:</strong> ${format_v(
						step.error
					)}</div>`;
				}

				return `<tr>
                <td style="vertical-align: top;">
                    <div class="font-weight-bold">${step.node}</div>
                    <div class="small text-muted">${step.type}</div>
                </td>
                <td class="text-right" style="vertical-align: top;">${duration_text}</td>
                <td style="vertical-align: top;">${details}</td>
            </tr>`;
			})
			.join("");

		let html = `
            <div class="table-responsive">
                <table class="table table-bordered table-striped" style="margin-bottom: 0;">
                    <thead>
                        <tr>
                            <th style="width: 20%">${__("Node")}</th>
                            <th style="width: 15%">${__("Duration")}</th>
                            <th style="width: 65%">${__("Details")}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;

		wrapper.html(html);
	},

	render_context_snapshot(frm) {
		if (!frm.doc.context_snapshot) return;

		let wrapper = frm.fields_dict.contexts_html.$wrapper;
		let context = null;
		try {
			context = JSON.parse(frm.doc.context_snapshot);
		} catch (e) {
			/* ignore */
		}

		if (!context) return;

		// Render Context nicely
		// Limit height if too long?

		let sections = Object.keys(context)
			.map((key) => {
				let val = context[key];
				let json_html = `<pre style="max-height: 300px; overflow: auto;">${JSON.stringify(
					val,
					null,
					2
				)}</pre>`;
				return `
                <div class="form-group">
                    <div class="label-area">
                        <label>${frappe.model.unscrub(key)}</label>
                    </div>
                    ${json_html}
                </div>
            `;
			})
			.join("");

		wrapper.html(`
            <div class="context-snapshot-wrapper">
                ${sections}
            </div>
        `);
	},
});
