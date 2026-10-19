# ChatGPT-to-Jules handoff

The `Start Jules Task` workflow creates a Jules API session for the FlexiRule repository and asks Jules to create a pull request automatically when it has a code patch. It does not merge that PR.

## Trigger from a ChatGPT conversation

1. Use an existing FlexiRule GitHub issue or pull request as the task's context.
2. Ask ChatGPT to prepare the final implementation prompt and post it as a comment with this format:

   ```text
   /jules
   Implement the task described below. Follow AGENTS.md, inspect the actual call paths,
   add regression tests, and run the relevant checks before opening a pull request.
   [Paste the complete task prompt here.]
   ```

3. The workflow starts when an authorized repository owner, member, or collaborator posts the comment. The task is always started from `develop`, and Jules is configured with `AUTO_CREATE_PR`.
4. Follow the Actions run log to the Jules session URL. Review the resulting PR and its CI checks before merging.

The connected GitHub integration used by ChatGPT must have permission to create issue/PR comments. If it is read-only, post the formatted comment manually or grant the integration only the required repository permissions.

## Manual fallback

Open **Actions → Start Jules Task → Run workflow** and provide the prompt. The only allowed starting branch is `develop`.

## Guardrails

- The workflow only accepts `/jules` commands from users whose GitHub comment association is `OWNER`, `MEMBER`, or `COLLABORATOR`.
- It targets only `sources/github/Sendipad/flexirule` and the `develop` branch.
- Prompts are limited to 20,000 characters; session titles are limited to 120 characters.
- `JULES_API_KEY` is read from GitHub Actions secrets and is never written into the request payload or printed in logs.
- Jules may create a PR, but this workflow does not approve or merge it.
- Creating the workflow file does not verify that the secret is valid or that Jules has been granted repository access. The first authorized run verifies those runtime prerequisites.
