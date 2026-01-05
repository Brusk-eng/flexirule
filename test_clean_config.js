// Mock frappe utils
global.frappe = {
    utils: {
        get_random: (len) => 'x'.repeat(len) // Return exact length string
    }
};

// Paste the relevant parts of ConfigurableAction for testing
class ConfigurableAction {
    constructor(opts) {
        this.node_data = opts.node_data;
        this.config = this._load_config();
    }

    _load_config() {
        // Reduced logic for test
        let config = this.node_data.config || {};
        this._hydrate_for_ui(config);
        return config;
    }

    _sync_to_node() {
        if (this.node_data) {
            const clean_config = this._clean_for_storage(this.config);
            this.node_data.config = clean_config;
        }
    }

    _hydrate_for_ui(data) {
        if (!data || typeof data !== 'object') return;
        for (const key in data) {
            if (Array.isArray(data[key])) {
                data[key].forEach((row, idx) => {
                    if (typeof row === 'object' && row !== null) {
                        if (!row.name) {
                            row.name = frappe.utils.get_random(10);
                            row.__islocal = 1;
                        }
                        if (row.idx === undefined) {
                            row.idx = idx + 1;
                        }
                        this._hydrate_for_ui(row);
                    }
                });
            } else if (typeof data[key] === 'object') {
                this._hydrate_for_ui(data[key]);
            }
        }
    }

    _clean_for_storage(data) {
        if (!data) return data;
        const clean = JSON.parse(JSON.stringify(data));

        const traverse_and_clean = (obj) => {
            if (Array.isArray(obj)) {
                obj.forEach(item => traverse_and_clean(item));
            } else if (typeof obj === 'object' && obj !== null) {
                const is_local = !!obj.__islocal;

                const keys_to_remove = [
                    '__islocal', '__checked', '__unsaved', 'docstatus',
                    'parent', 'parenttype', 'parentfield', 'owner', 'creation', 'modified'
                ];
                keys_to_remove.forEach(k => delete obj[k]);

                if (is_local || (obj.name && obj.name.length === 10) || (obj.name && obj.name.startsWith('row '))) {
                    delete obj.name;
                }
                delete obj.idx;
                for (const key in obj) {
                    traverse_and_clean(obj[key]);
                }
            }
        };

        traverse_and_clean(clean);
        return clean;
    }
}

// TEST
const node_data = {
    config: {
        some_field: "value",
        child_table: [
            { field_a: 1 }, // Needs hydration
            { field_b: 2, name: "stable_id", __islocal: 0 } // Should preserve stable_id? But logic says remove if len=10. Stable ID usually short? Or hash? 
            // Frappe usually assigns 10 char random for new docs too.
            // But if it's retrieved from backend, name exists.
            // If we are strictly "Concept Configuration", we might not care about name persistence unless it's ref'd.
        ]
    }
};

const action = new ConfigurableAction({ node_data });
console.log("Hydrated Config:", JSON.stringify(action.config, null, 2));

// Simulate UI adding fields
action.config.child_table[0].__checked = 1;
action.config.child_table[0].__islocal = 1;

// Save
action._sync_to_node();
console.log("Cleaned Config:", JSON.stringify(action.node_data.config, null, 2));

if (action.node_data.config.child_table[0].__checked) {
    console.error("FAIL: __checked not removed");
} else {
    console.log("PASS: __checked removed");
}

if (action.node_data.config.child_table[0].name) {
    console.error("FAIL: name not removed");
    console.log(action.node_data.config.child_table[0].name);
} else {
    console.log("PASS: name removed");
}
