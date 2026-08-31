---
name: prism-production-trader-watch
description: Monitor PRISM's deployed production autonomous paper trader for readiness, cycle failures, kill-switch state, and safe error evidence. Use for production health checks and diagnosis; it never changes trading authority or submits orders.
---

# PRISM production trader watch

Assess whether the deployed autonomous paper trader is healthy and behaving as
configured. This is a read-only diagnostic workflow. It is not a release,
provider-probe, execution, or kill-switch-control skill.

## Safety boundary

- Read `AGENTS.md`, `.agents/rules/30-trading-safety.md`, and the production
  sections of `docs/deployment/staging-server-maintenance-cheatsheet.md` before
  connecting.
- Use the production root `/opt/bgh/prism-production`; parse SSH connection
  settings from `.env.devops` without sourcing it. Never print `.env`, tokens,
  account identifiers, provider payloads, or raw broker errors.
- Do not call any `POST`, `PUT`, or `DELETE` endpoint; do not recreate
  containers, alter configuration, run a worker cycle manually, invoke the
  paper CLI, or contact Alpaca/Featherless. Request explicit approval before
  any of those actions.
- Do not use `GET /api/v1/autonomous/status` as a generic read probe: on an
  uninitialized database it creates the durable control row. Read the existing
  `autonomous_controls` row with a read-only database query instead.

## Evidence to collect

Use bounded, redacted checks in this order:

1. Confirm the deployed revision, Compose service state/health, and direct
   readiness on the configured `PRISM_HTTP_PORT` (production currently uses
   port 3002). Treat a host-port redirect as an edge-routing issue, not backend
   readiness.
2. Read only non-secret operational flags: paper mode, execution/autonomous
   enabled state, static kill switch, ruleset, authorized UTC window, and scan
   interval.
3. Query the durable control row read-only and report only `active`, update
   time, actor label, and reason. If it is absent, say so; do not initialize it.
4. Through the normal authenticated operator flow, query bounded UTC ranges
   from `/api/v1/autonomous/cycles`, `/decisions`, and `/executions`. Use a
   maximum of 200 records and state the range. The endpoints already redact
   account/order identifiers and raw errors.
5. Inspect a bounded recent backend log window only when health, a cycle, or a
   receipt indicates a problem. Summarize error class, UTC time, component, and
   count. Do not reproduce raw log lines or provider output.

## Interpretation

- Before the authorized start time, no worker cycle is expected. State that
  explicitly rather than treating an empty history as a failure.
- During the window, a `NO_TRADE` result is normal when its recorded reason is
  a safety gate (for example `Kill switch active`, market closed, or missing
  entitled evidence). A `FAILED` cycle, readiness failure, stale in-window
  cadence relative to the configured scan interval, or unresolved/reconciling
  receipt requires attention.
- A durable kill switch set to active should yield an auditable `NO_TRADE` and
  no new execution receipt. It is independent of the schedule gate.
- Never infer a fill, P&L, or a live-trading capability from a proposal or an
  illustrative presentation response.

## Report format

Lead with `healthy`, `degraded`, or `attention required`, then provide:

- deployment and readiness evidence;
- effective paper/execution/schedule/kill-switch state;
- cycle, decision, and receipt counts for the exact UTC range;
- any relevant redacted failure categories and their impact;
- the smallest safe next action. If a state change is needed, request explicit
  operator approval instead of making it.
