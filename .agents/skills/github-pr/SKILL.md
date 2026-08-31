---
name: github-pr
description: Commit completed repository work, create or reuse a governed Git branch, push it, and open the correctly based GitHub pull request. Use when the user asks to commit changes, prepare/open a PR, or promote staging to main; do not use to merge or bypass checks.
---

# GitHub Pull Request

Prepare a reviewable PR without bypassing repository governance. Root `AGENTS.md` and `.agents/rules/70-commits-pull-requests.md` remain authoritative.

## Inspect before mutating

1. Read the repository rules, then inspect `git status --short`, the current branch, `git diff`, `git diff --cached`, remotes, and recent commits.
2. Confirm `gh auth status` and that `origin` points to the intended GitHub repository. Never create a repository, fork, or remote unless the user explicitly requests it.
3. Detect an empty repository. Do not improvise the bootstrap exception: report that `main` needs its one-time initial commit and `staging` branch, and obtain explicit authorization for those remote mutations.

## Choose the branch and base

- Normal work: branch from current `staging` as `feature/<slug>`; use `fix/`, `chore/`, `docs/`, `refactor/`, `test/`, or `ci/` when that type is more accurate. Target `staging`.
- Urgent production work: branch from current `main` using the same typed prefixes and target `main` directly. Preserve the required checks and pull-request review; direct pushes remain prohibited.
- If working changes are already present on `main` or `staging`, create the work branch before committing so the protected branch stays unchanged.
- If already on an allowed work branch, reuse it unless it is unrelated to the change.
- Promotion: a clean `staging` branch targets `main`; do not add a promotion-only commit. An allowed typed branch based on current `main` may also target `main` for an urgent direct release.
- Refuse a PR from `main`, an untyped branch into `main`, detached HEAD, or a branch with unrelated history.

Fetch before branching and ensure the chosen base exists on `origin`. Use explicit base/head flags throughout; never infer `main` from GitHub's default branch.

## Commit if needed

If the branch has uncommitted intended work:

1. Run applicable tests and `pnpm verify` for repository-wide changes. Run `pnpm docker:config` for infrastructure changes.
2. Review for credentials and sensitive output. Inspect generated files and lockfile changes.
3. Stage only intended paths. Preserve unrelated changes and never use destructive cleanup.
4. Review `git diff --cached --check` and `git diff --cached`.
5. Commit with `type(scope): imperative summary`. Always wrap commit messages in single quotes `'...'` or use `git commit -F <file>` to prevent PowerShell/Bash variable expansion of `$` (e.g. `$100,000`) or stripping of backticks. Do not amend or rewrite existing commits unless explicitly authorized.

If there is no uncommitted work, require at least one commit ahead of the base. Stop rather than create an empty commit.

## Safe PR body & title formatting

To prevent shells (especially Windows PowerShell) from stripping variables (`$100` -> empty), mangling markdown backticks, or truncating content:
- **Mandatory `--body-file`**: NEVER pass inline multi-line markdown using `--body "..."`. Always write the formatted markdown body into a temporary scratch file and pass `--body-file <path-to-file>`.
- **Single-quoted titles**: Wrap titles in single quotes (e.g., `--title 'feat(core): support $100,000 baseline'`) so dollar signs and special characters are preserved verbatim.

## Push and open the PR

Pushing and opening a PR are external writes. The user's explicit request to create/open a PR authorizes both; otherwise pause for authorization immediately before pushing.

1. Push without force: `git push --set-upstream origin <head>`.
2. Check for an existing open PR with `gh pr list --head <head> --state open --json url,baseRefName`. Reuse and report it instead of creating a duplicate; do not silently retarget an existing PR.
3. Create with explicit branches: `gh pr create --base <base> --head <head> --title '<title>' --body-file <temp-body-file>`.
4. The body follows `.github/pull_request_template.md` and records summary, safety impact, verification, generated artifacts/docs, and TBDs.
5. Clean up any temporary scratch files.
6. Return the PR URL, head/base, commit SHA, and checks performed. Do not merge, enable auto-merge, delete branches, or bypass checks.

Official command behavior: https://cli.github.com/manual/gh_pr_create
