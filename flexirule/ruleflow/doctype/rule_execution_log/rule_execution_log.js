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

				// If we have a next step, diff between steps
				if (next_step) {
					duration_ms = (next_step.timestamp - step.timestamp) * 1000;
				} else if (frm.doc.duration) {
					// Last step: total duration - time elapsed until last step started
					let elapsed_until_last = (step.timestamp - path[0].timestamp) * 1000;
					duration_ms = frm.doc.duration * 1000 - elapsed_until_last;
				}

				// Format Text
				let duration_text = duration_ms > 0 ? `${duration_ms.toFixed(2)} ms` : "-";

				// Helper to Format JSON or Strings
				const format_v = (v) => {
					if (v === undefined || v === null) return "";
					if (typeof v === "string") {
						// Try to parse if it looks like JSON
						// Special handling for Python-style string representations (single quotes)
						let clean_v = v;
						if (v.startsWith("[") || v.startsWith("{")) {
							clean_v = v.replace(/'/g, '"');
						}

						try {
							let parsed = JSON.parse(clean_v);
							return `<pre class="small">${JSON.stringify(parsed, null, 2)}</pre>`;
						} catch (e) {
							// Return as-is if it fails to parse
							return `<div class="text-monospace small" style="white-space: pre-wrap;">${frappe.utils.escape_html(
								v
							)}</div>`;
						}
					}
					return `<pre class="small">${JSON.stringify(v, null, 2)}</pre>`;
				};

				let details = "";
				if (step.input && Object.keys(step.input).length) {
					details += `<div><span class="text-muted small">Input:</span> ${format_v(
						step.input
					)}</div>`;
				}
				if (step.output) {
					details += `<div><span class="text-muted small">Output:</span> ${format_v(
						step.output
					)}</div>`;
				}
				if (step.error) {
					details += `<div class="text-danger small"><strong>Error:</strong> ${format_v(
						step.error
					)}</div>`;
				}

				let node_label = step.action || step.node || "Unknown";
				let node_id = step.action_id ? `(${step.action_id})` : "";

				return `<tr>
                <td style="vertical-align: top;">
                    <div class="font-weight-bold">${node_label}</div>
                    <div class="small text-muted">${node_id}</div>
                    <div class="small text-muted italic">${step.type}</div>
                </td>
                <td class="text-right" style="vertical-align: top;">
                    <span class="badge ${duration_ms > 0 ? "badge-info" : "badge-light"}">
                        ${duration_text}
                    </span>
                </td>
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
