import assert from "node:assert/strict";
import { runConfigSaveLifecycle } from "./config_save_lifecycle.mjs";

// An active fetch blocks before starting validation.
{
	let validationCalls = 0;
	let commitCalls = 0;
	const result = await runConfigSaveLifecycle({
		isLoading: () => true,
		validate: async () => {
			validationCalls += 1;
			return { valid: true };
		},
		commit: () => {
			commitCalls += 1;
		},
	});
	assert.deepEqual(result, { status: "blocked-loading" });
	assert.equal(validationCalls, 0);
	assert.equal(commitCalls, 0);
}

// A fetch that starts while an async panel validator is pending blocks the commit.
// This exercises the async lifecycle boundary instead of only the final decision helper.
{
	let loading = false;
	let releaseValidation;
	let commitCalls = 0;
	const validationPending = new Promise((resolve) => {
		releaseValidation = resolve;
	});
	const saving = runConfigSaveLifecycle({
		isLoading: () => loading,
		validate: () => validationPending,
		commit: () => {
			commitCalls += 1;
		},
	});

	loading = true;
	releaseValidation({ valid: true });
	assert.deepEqual(await saving, { status: "blocked-loading" });
	assert.equal(commitCalls, 0);
}

// Valid saves commit once; invalid saves never commit.
{
	let commitCalls = 0;
	const valid = await runConfigSaveLifecycle({
		isLoading: () => false,
		validate: async () => ({ valid: true }),
		commit: () => {
			commitCalls += 1;
		},
	});
	assert.equal(valid.status, "committed");
	assert.equal(commitCalls, 1);

	const invalid = await runConfigSaveLifecycle({
		isLoading: () => false,
		validate: async () => ({ valid: false, errors: ["Required field"] }),
		commit: () => {
			commitCalls += 1;
		},
	});
	assert.equal(invalid.status, "invalid");
	assert.deepEqual(invalid.validation.errors, ["Required field"]);
	assert.equal(commitCalls, 1);
}

console.log("Rule Config save lifecycle tests passed");
