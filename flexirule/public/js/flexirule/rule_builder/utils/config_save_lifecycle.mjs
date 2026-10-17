/**
 * Run the Rule Config save lifecycle with loading and source-context guards.
 *
 * A graph fetch can start and finish while validation is awaiting, leaving a
 * modal's node reference detached even though isLoading() is false again.
 */
export async function runConfigSaveLifecycle({
	isLoading,
	isContextCurrent = () => true,
	validate,
	commit,
}) {
	if (isLoading() || !isContextCurrent()) {
		return { status: "blocked-stale-context" };
	}

	const validation = await validate();

	// Validation can await panel-level validators. Recheck both loading and
	// identity/generation before mutating the graph or closing the modal.
	if (isLoading() || !isContextCurrent()) {
		return { status: "blocked-stale-context" };
	}

	if (!validation?.valid) {
		return { status: "invalid", validation };
	}

	commit();
	return { status: "committed", validation };
}
