# Commits, Branches, and Pull Requests

## Branch flow

The governed integration path is:

```text
feature/* (or fix/*, chore/*, docs/*, refactor/*, test/*, ci/*)
copilot/feature-* (or copilot/fix-*, copilot/chore-*, copilot/docs-*, copilot/refactor-*, copilot/test-*, copilot/ci-*)
  -> staging or main
staging -> main
```

- `main` and `staging` are protected integration branches. After the one-time repository bootstrap, do not commit or push directly to either branch.
- Normal work targets `staging` by pull request. Urgent, reviewed work may target `main` directly from an allowed typed branch based on current `main`.
- A production promotion may be either a pull request whose head is exactly `staging` and base is `main`, or a direct typed work branch into `main`.
- Never merge a pull request, bypass required checks, force-push a shared branch, or use administrator overrides unless the user explicitly authorizes that exact action.

## Commit discipline

- Inspect `git status`, the diff, and staged diff before every commit. Preserve unrelated user changes.
- If changes are present on `main` or `staging`, create the intended work branch before committing them. A direct-main branch must begin from current `main`; a staging branch must begin from current `staging`.
- Stage explicit intended paths; do not use a blanket stage when unrelated changes exist.
- Never commit secrets, `.env`, credentials, private keys, local databases, caches, generated environments, or credential-bearing MCP configuration.
- Use focused Conventional Commit subjects: `type(scope): imperative summary`. Supported types are `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`, and `perf`.
- Include generated contracts, migrations, tests, documentation, and lockfiles in the same commit when they are part of the change.
- Run the applicable checks before committing. Repository-wide changes require `pnpm verify`; infrastructure changes also require `pnpm docker:config`.
- Do not amend, rewrite, squash, or rebase commits belonging to others without explicit authorization.

## Pull requests

- Use the repository-local `$github-pr` skill for a request to commit, push, or open a GitHub pull request.
- PR titles use the same Conventional Commit shape as commit subjects.
- PR bodies state the outcome, safety impact, verification performed, generated artifacts, documentation changes, and unresolved TBDs.
- Confirm the remote branch and base explicitly. Do not rely on the repository default branch for PR targeting.
- Pushing and creating a PR are external mutations. A request that explicitly says to create/open the PR authorizes those actions; otherwise request authorization immediately before the first push.

## Bootstrap exception

An empty repository needs one reviewed initial commit on `main` before GitHub can host the branch flow. With explicit owner authorization, create and push that bootstrap commit, create `staging` at the same commit, then enable the documented branch protections. This exception ends as soon as both remote branches exist.
