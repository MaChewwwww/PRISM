# CI/CD and Branch Promotion

## Governed flow

```text
feature/*, fix/*, chore/*, docs/*, refactor/*, test/*, ci/*
                              │
                              ▼ pull request
                           staging
                              │
                              ▼ promotion pull request
                             main
                              │
                              ▼ protected manual deployment
                          production
```

Direct commits and pushes to `staging` and `main` are prohibited after the one-time repository bootstrap. `.github/workflows/branch-policy.yml` rejects a PR into `staging` unless its head uses an allowed typed branch, and rejects a PR into `main` unless its head is exactly `staging`.

## Continuous integration

Pull requests and pushes targeting `staging` or `main` run:

- repository governance and vendored-skill provenance checks;
- ESLint, Prettier, Ruff, mypy, TypeScript, Vitest, and pytest;
- deterministic contract regeneration and application builds;
- JavaScript/Python dependency audits and secret scanning;
- frontend/backend image builds and Trivy scans.

Configure GitHub branch protection or rulesets for both integration branches. Require pull requests, at least one approving review, dismissal of stale approvals, conversation resolution, linear history, and these checks: `branch-policy`, `verify`, `secrets`, and both container matrix jobs. Disable force pushes and branch deletion. For `main`, require the head branch to be up to date if that policy fits the team's merge queue.

## Staging delivery

A successful CI run caused by a push to `staging` can trigger `.github/workflows/deploy-staging.yml`. Deployment is disabled until repository variable `STAGING_DEPLOY_ENABLED` equals `true`. The job uses the protected `staging` environment and its `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, and `VPS_APP_PATH` secrets.

Staging checks out the exact CI commit in its own VPS path and Compose project, listens on `${STAGING_HTTP_PORT:-8080}`, and verifies readiness. Use a staging-specific DNS/TLS proxy before exposing it beyond trusted operators.

## Production delivery

Production deploys automatically on port `80` whenever a reviewed promotion PR merges into `main` and passes CI. The workflow verifies the commit ancestry on `main`, enters the protected `production` environment, builds immutable images, deploys through SSH, and checks readiness. Manual dispatch with an explicit revision remains available as an operational fallback.

The staging and production environments must use different `VPS_APP_PATH` values, Compose project names, secrets, credentials, and databases. Specifically, **staging uses a personal dummy Alpaca paper account** (`.env.staging.example`) to protect competition funds during simulations, and **production uses the official Hackathon-provided Alpaca paper account** (`.env.production.example`) with the $100,000 capital baseline. Only Alpaca paper credentials are permitted in either environment, and execution remains disabled unless separately authorized.

## Pull-request automation

Use the repository-local `$github-pr` skill to prepare a commit and PR. It selects `staging` for normal work and `main` only for a clean promotion from `staging`; it never merges. `gh pr create` receives explicit `--base` and `--head` values so repository-default-branch changes cannot redirect a PR.

## Bootstrap

Because GitHub cannot protect an unborn branch, the repository owner must explicitly authorize the one-time initial commit and push to `main`. Create `staging` at that same commit, push it, configure both rulesets and environments, then begin the governed PR flow. The bootstrap exception must not be reused.

## Rollback

Rollback redeploys a previously verified SHA through the appropriate protected environment. Do not rewrite integration-branch history or delete audit data. Database changes must remain forward compatible or include an independently tested recovery procedure.
