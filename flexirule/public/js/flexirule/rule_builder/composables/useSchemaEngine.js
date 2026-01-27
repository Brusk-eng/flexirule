import { ref, reactive, watch, nextTick } from "vue";
import CoreUtils from "../core/CoreUtils";

/**
 * useSchemaEngine
 * 
 * Composable to manage dynamic schema logic:
 * - Normalization of fields (fieldtypes, labels, etc.)
 * - Dependency evaluation (hidden, required, read-only)
 * - Dynamic options resolution
 * 
 * @param {Object} options 
 * @param {Array} options.fields - Raw field definitions
 * @param {Object} options.config - Reactive configuration object
 * @param {Object} options.context - Additional context (vars, doc_meta, etc.)
 */
export function useSchemaEngine(options = {}) {
    const rawFields = ref(options.fields || []);
    const config = options.config || reactive({});
    const context = options.context || {};

    const normalizedFields = ref([]);
    const dependencyStates = reactive({}); // contextId -> { fieldname: { hidden, reqd, read_only, options } }

    const fieldMap = {};

    /**
     * Build a flat map of fields for quick lookup, including child table fields.
     */
    function buildFieldMap(fields) {
        const traverse = (fs) => {
            fs.forEach(f => {
                fieldMap[f.fieldname] = f;
                if (f.fieldtype === "Table" && f.fields) {
                    traverse(f.fields);
                }
            });
        };
        traverse(fields);
    }

    /**
     * Normalize a single field definition.
     */
    async function normalizeField(field) {
        const f = { ...field };
        f.reqd = f.reqd || 0;
        f.read_only = f.read_only || 0;
        f.hidden = f.hidden || 0;

        if (f.in_list_view === undefined) f.in_list_view = 1;
        if (f.width) f.columns = f.width;

        f.fieldtype = CoreUtils.map_fieldtype(f.fieldtype);

        // Resolve initial options
        f.options = await resolveOptions(f, config, getEvalContext());

        if (f.fieldtype === "Table") {
            const children = f.fields || f.table_fields || [];
            if (!f._is_normalized) {
                f.fields = await Promise.all(children.map(cf => normalizeField(cf)));
                f._is_normalized = true;
            }
        }

        return f;
    }

    /**
     * Resolve dynamic options for a field.
     */
    async function resolveOptions(field, doc, evalContext = {}) {
        const getter = field.get_options || (typeof field.options === "function" ? field.options : null);
        if (getter) {
            try {
                return await getter(doc, evalContext, context.doc_meta);
            } catch (e) {
                console.warn(`useSchemaEngine: Failed to resolve options for ${field.fieldname}`, e);
                return [];
            }
        }

        if (typeof field.options === "string") {
            if (field.options.startsWith("doc.")) {
                return doc[field.options.replace("doc.", "")] || "";
            }
            if (field.options.startsWith("vars.")) {
                return (evalContext.vars || {})[field.options.replace("vars.", "")] || "";
            }
        }

        return field.options || "";
    }

    // Evaluate dependencies for a specific context (root or table row).
    async function evaluateDependencies(targetDoc, row = null, tableFieldname = null) {
        const contextId = row ? (row.name || row.__uuid || "row") : "root";
        if (!dependencyStates[contextId]) {
            dependencyStates[contextId] = {};
        }

        let targetFields = [];
        if (row && tableFieldname) {
            const tableDef = fieldMap[tableFieldname];
            targetFields = tableDef ? tableDef.fields || [] : [];
        } else {
            targetFields = normalizedFields.value.filter(f => f.fieldtype !== "Table");
        }

        const evalContext = getEvalContext(row);

        for (const field of targetFields) {
            const state = {
                reqd: field.reqd || 0,
                read_only: field.read_only || 0,
                hidden: field.hidden || 0,
                options: null,
            };

            if (field.depends_on) {
                state.hidden = CoreUtils.eval_condition(field.depends_on, evalContext) ? 0 : 1;
            }
            if (field.mandatory_depends_on) {
                state.reqd = CoreUtils.eval_condition(field.mandatory_depends_on, evalContext) ? 1 : 0;
            }
            if (field.read_only_depends_on) {
                state.read_only = CoreUtils.eval_condition(field.read_only_depends_on, evalContext) ? 1 : 0;
            }

            // Always re-resolve if it looks dynamic
            const isDynamic = field.get_options || typeof field.options === "function" ||
                (typeof field.options === "string" && (field.options.startsWith("doc.") || field.options.startsWith("vars.")));

            if (isDynamic) {
                state.options = await resolveOptions(field, targetDoc, evalContext);
            }

            dependencyStates[contextId][field.fieldname] = state;
        }
    }

    function getEvalContext(row = null) {
        return {
            doc: row || config,
            row: row,
            parent: config,
            config: config,
            vars: context.available_variables || {},
            ...context
        };
    }

    async function init() {
        normalizedFields.value = await Promise.all(rawFields.value.map(f => normalizeField(f)));
        buildFieldMap(normalizedFields.value);
        await evaluateDependencies(config);
    }

    return {
        normalizedFields,
        dependencyStates,
        init,
        evaluateDependencies,
        getEvalContext
    };
}
