/**
 * Compile a ConditionBuilder tree into a Python/Jinja boolean expression string.
 *
 * Input: { op: "and", conditions: [ { left: { ref: "doc.status" }, op: "==", right: { value: "Open" } }, ... ] }
 * Output: "doc.status == 'Open' and doc.total > 100"
 */

export function compileConditionTree(node) {
	if (!node) return "";

	// Group node (and/or)
	if (Array.isArray(node.conditions)) {
		if (!node.conditions.length) return "True";

		const parts = node.conditions.map((child) => compileConditionTree(child)).filter(Boolean);

		if (!parts.length) return "True";
		if (parts.length === 1) return parts[0];

		const joiner = node.op === "or" ? " or " : " and ";
		return "(" + parts.join(joiner) + ")";
	}

	// Collection node (any/all)
	if (node.collection !== undefined) {
		const alias = node.alias || "row";
		const collection = node.collection || "[]";
		const whereExpr = node.where ? compileConditionTree(node.where) : "True";
		const quantifier = node.op === "all" ? "all" : "any";
		return `${quantifier}(${whereExpr} for ${alias} in ${collection})`;
	}

	// Simple condition (left op right)
	if (node.left !== undefined) {
		const left = node.left.ref || "";
		if (!left) return "";

		const op = node.op || "==";

		// Unary operators
		if (op === "is_set") return left;
		if (op === "is_not_set") return `not ${left}`;

		// Get right value
		let right;
		if (node.right?.ref) {
			right = node.right.ref;
		} else {
			right = formatValue(node.right?.value);
		}

		// Map operators
		const opMap = {
			"==": "==",
			"!=": "!=",
			">": ">",
			"<": "<",
			">=": ">=",
			"<=": "<=",
			in: "in",
			"not in": "not in",
			like: "like",
			"not like": "not like",
			contains: "in",
			not_contains: "not in",
		};

		const pyOp = opMap[op] || op;

		if (op === "contains" || op === "not_contains") {
			// Reverse: right in left
			return `${right} ${pyOp} ${left}`;
		}

		return `${left} ${pyOp} ${right}`;
	}

	return "";
}

function formatValue(val) {
	if (val === null || val === undefined) return "None";
	if (typeof val === "boolean") return val ? "True" : "False";
	if (typeof val === "number") return String(val);
	if (Array.isArray(val)) {
		// Could be a [DocType, value] tuple for links
		if (val.length === 2 && typeof val[0] === "string") {
			return formatValue(val[1]);
		}
		return "[" + val.map(formatValue).join(", ") + "]";
	}
	// String - quote it
	const escaped = String(val).replace(/'/g, "\\'");
	return `'${escaped}'`;
}

/**
 * Compile segments array to a Jinja template string.
 */
export function compileSegmentsToJinja(segments) {
	if (!Array.isArray(segments)) return "";
	return segments
		.map((seg) => {
			if (!seg) return "";
			const t = (seg.type || "text").toLowerCase();

			if (t === "text") return seg.content || seg.text || "";

			if (t === "variable") {
				const p = (seg.path || "").trim();
				return p ? `{{ ${p} }}` : "";
			}

			if (t === "conditional") {
				const condExpr = seg.condition ? compileConditionTree(seg.condition) : "True";
				let out = `{% if ${condExpr} %}`;
				out += compileSegmentsToJinja(seg.then_segments || []);

				// elif branches
				if (Array.isArray(seg.elif_branches)) {
					for (const elif of seg.elif_branches) {
						const elifExpr = elif.condition
							? compileConditionTree(elif.condition)
							: "True";
						out += `{% elif ${elifExpr} %}`;
						out += compileSegmentsToJinja(elif.segments || []);
					}
				}

				// else
				const elseContent = compileSegmentsToJinja(seg.else_segments || []);
				if (elseContent) {
					out += `{% else %}${elseContent}`;
				}

				out += "{% endif %}";
				return out;
			}

			return "";
		})
		.join("");
}
