/**
 * Compile a ConditionBuilder tree into a Python/Jinja boolean expression string.
 *
 * Input: { op: "and", conditions: [ { left: { ref: "doc.status" }, op: "==", right: { value: "Open" } }, ... ] }
 * Output: "doc.status == 'Open' and doc.total > 100"
 */

const SIMPLE_PATH_RE = /^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$/;
const ALLOWED_ROOTS = new Set([
	"doc",
	"old_doc",
	"vars",
	"item",
	"loop",
	"caller",
	"rule",
	"doctype",
]);

export function normalizeTemplatePath(path, knownVarRoots = []) {
	const raw = String(path || "").trim();
	if (!raw || !SIMPLE_PATH_RE.test(raw)) return raw;

	const roots = new Set(knownVarRoots || []);
	const root = raw.split(".", 1)[0];
	if (ALLOWED_ROOTS.has(root)) return raw;
	if (roots.has(root)) return `vars.${raw}`;
	return `doc.${raw}`;
}

function normalizeInlineJinja(content, knownVarRoots = []) {
	if (!content || typeof content !== "string") return content || "";
	return content.replace(/\{\{\s*([^}]+?)\s*\}\}/g, (_m, expr) => {
		const normalized = normalizeTemplatePath(expr, knownVarRoots);
		if (!normalized) return "";
		return `{{ ${normalized} }}`;
	});
}

export function compileConditionTree(node, knownVarRoots = []) {
	if (!node) return "";

	// Group node (and/or)
	if (Array.isArray(node.conditions)) {
		if (!node.conditions.length) return "True";

		const parts = node.conditions
			.map((child) => compileConditionTree(child, knownVarRoots))
			.filter(Boolean);

		if (!parts.length) return "True";
		if (parts.length === 1) return parts[0];

		const joiner = node.op === "or" ? " or " : " and ";
		return "(" + parts.join(joiner) + ")";
	}

	// Collection node (any/all)
	if (node.collection !== undefined) {
		const alias = node.alias || "item";
		const collection = normalizeTemplatePath(node.collection || "[]", knownVarRoots) || "[]";
		const whereExpr = node.where ? compileConditionTree(node.where, knownVarRoots) : "True";
		const quantifier = node.op === "all" ? "all" : "any";
		return `${quantifier}(${whereExpr} for ${alias} in ${collection})`;
	}

	// Simple condition (left op right)
	if (node.left !== undefined) {
		const left = normalizeTemplatePath(node.left.ref || "", knownVarRoots);
		if (!left) return "";

		const op = node.op || "==";

		// Unary operators
		if (op === "is_set") return left;
		if (op === "is_not_set") return `not ${left}`;

		// Get right value
		let right;
		if (node.right?.ref) {
			right = normalizeTemplatePath(node.right.ref, knownVarRoots);
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
export function compileSegmentsToJinja(segments, options = {}) {
	const knownVarRoots = options.knownVarRoots || [];
	if (!Array.isArray(segments)) return "";
	return segments
		.map((seg) => {
			if (!seg) return "";
			const t = (seg.type || "text").toLowerCase();

			if (t === "text")
				return normalizeInlineJinja(seg.content || seg.text || "", knownVarRoots);

			if (t === "variable") {
				const p = normalizeTemplatePath(seg.path || "", knownVarRoots);
				return p ? `{{ ${p} }}` : "";
			}

			if (t === "conditional") {
				const condExpr = seg.condition
					? compileConditionTree(seg.condition, knownVarRoots)
					: "True";
				let out = `{% if ${condExpr} %}`;
				out += compileSegmentsToJinja(seg.then_segments || [], { knownVarRoots });

				// elif branches
				if (Array.isArray(seg.elif_branches)) {
					for (const elif of seg.elif_branches) {
						const elifExpr = elif.condition
							? compileConditionTree(elif.condition, knownVarRoots)
							: "True";
						out += `{% elif ${elifExpr} %}`;
						out += compileSegmentsToJinja(elif.segments || [], { knownVarRoots });
					}
				}

				// else
				const elseContent = compileSegmentsToJinja(seg.else_segments || [], {
					knownVarRoots,
				});
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
