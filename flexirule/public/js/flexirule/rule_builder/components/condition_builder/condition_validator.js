/**
 * Validates a condition tree recursively.
 * Returns an object with { valid: boolean, message?: string }
 */
export function validateConditions(node, isRoot = false) {
    // 1. Check for Groups (including Root)
    // A group is identified by the presence of a 'conditions' array
    if (node.conditions !== undefined) {
        if (!node.conditions || node.conditions.length === 0) {
            return {
                valid: false,
                message: isRoot
                    ? __("Please add at least one condition.")
                    : __("Empty condition groups are not allowed."),
            };
        }

        for (const child of node.conditions) {
            const result = validateConditions(child);
            if (!result.valid) return result;
        }
    }
    // 2. Check for Collections
    // A collection is identified by the presence of a 'collection' field
    else if (node.collection !== undefined) {
        if (!node.collection) {
            return {
                valid: false,
                message: __("Please select a table for the collection condition."),
            };
        }

        if (!node.where || !node.where.conditions || node.where.conditions.length === 0) {
            return {
                valid: false,
                message: __("Collection '{0}' must have at least one condition.").replace(
                    "{0}",
                    node.collection
                ),
            };
        }

        const result = validateConditions(node.where);
        if (!result.valid) return result;
    }

    // Simple conditions (with field/op/value) are considered valid for now as they default to valid state on creation
    return { valid: true };
}
