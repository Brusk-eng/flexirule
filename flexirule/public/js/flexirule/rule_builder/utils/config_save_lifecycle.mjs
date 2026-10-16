/**
 * Run the Rule Config save lifecycle with live loading checks around async validation.
 *
 * The commit callback runs synchronously immediately after the post-validation check,
 * so a graph fetch cannot slip between the final guard and applying the draft.
 */
export async function runConfigSaveLifecycle({ isLoading, validate, commit }) {
	if (isLoading()) {
		return { status: "blocked-loading" };
	}

	const validation = await validate();

	// Validation can await panel-level validators. Read the live store state again
	// before either applying changes or treating a now-stale draft as saved.
	if (isLoading()) {
		return { status: "blocked-loading" };
	}

	if (!validation?.valid) {
		return { status: "invalid", validation };
	}

	commit();
	return { status: "committed", validation };
}
