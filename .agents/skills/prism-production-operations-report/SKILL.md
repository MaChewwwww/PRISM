---
name: prism-production-operations-report
description: Produce a bounded, provenance-aware production report of PRISM autonomous events, agent decisions, paper receipts, portfolio risk, ShadowFund outcomes, and available P&L. Use for analysis and reporting only; it never changes execution state.
---

# PRISM production operations report

Create an operator-readable production report from PRISM's authenticated,
read-only APIs. Separate actual paper-trading records from non-executable
ShadowFund and illustrative presentation data.

## Safety and provenance boundary

- Read `AGENTS.md`, `.agents/rules/30-trading-safety.md`,
  `docs/DATA_API_CONTRACTS.md`, and `docs/SECURITY.md` first.
- Authenticate through the normal operator flow. Never expose passwords,
  bearer tokens, account IDs, broker/client order IDs, raw provider payloads,
  raw error bodies, or hidden reasoning in a report.
- Use only `GET` requests. Never invoke a research endpoint to manufacture new
  events, and never call execution, kill-switch, profile, or configuration
  control endpoints.
- Require a timezone-aware UTC range for historical collections. If the user
  does not provide one, use the current UTC calendar day and state that choice.
  Bound all autonomous collections to 200 records or fewer.

## Sources and meaning

| Need | Read-only source | Report as |
| --- | --- | --- |
| Worker events | `/api/v1/autonomous/cycles` | Recorded production cycle outcomes and reasons |
| Agent proposals and rule outcomes | `/api/v1/autonomous/decisions` | Deterministic authorization evidence, never hidden reasoning |
| Paper order state | `/api/v1/autonomous/executions` | Sanitized receipt state, quantities, timestamps, stable error codes |
| Current account/risk state | `/api/v1/autonomous/portfolio/latest` | Latest persisted normalized snapshot, not a live refresh |
| Shadow portfolio outcomes | `/api/v1/presentation/alternatives` | Recorded non-executable ShadowFund branches; retain `data_mode` and limitations |
| Provider use | `/api/v1/llm-usage/summary` | Aggregated provider tokens/latency metadata only |
| Presentation agents/news | `/api/v1/presentation/agents` and `/news` | Include only when their `data_mode` proves they are recorded; label illustrative fixtures as illustrative |

## Analysis rules

- Preserve decimal strings through all calculations; do not convert money,
  quantities, percentages, or P&L to binary floats.
- Distinguish `APPROVE`, `REJECT`, and `MODIFIED_PENDING_ACCEPTANCE`; only the
  first can progress toward paper execution, and an approval is not a fill.
- Group cycles by `NO_TRADE`, `SUBMITTED`, and `FAILED`; include the most common
  recorded reasons and flag failures separately from normal safety refusals.
- Group decisions by authorization outcome, symbol, ruleset/profile version,
  expiry, and failed/modified rule codes. Do not claim an agent decision was an
  autonomous order unless a linked sanitized execution receipt exists.
- Report paper execution counts by receipt status. Treat `pending` and
  `reconciling` as operational attention items; report stable error codes only.
- For earnings/losses, report only evidence that exists: persisted portfolio
  value/start-of-day equity and per-position unrealized P&L, plus ShadowFund
  branch gross/net P&L separately. Do not invent realized P&L, account returns,
  or a combined actual-plus-ShadowFund total.
- Empty states are valid before the first cycle. Say `no recorded data in the
  requested range`, not `zero performance`.

## Report format

Lead with the UTC range and data provenance, then provide concise sections:

1. **Autonomous activity** — cycles, safety refusals, failures, and cadence.
2. **Decisions and governance** — proposals, authorization outcomes, rule
   themes, expiries, and linked receipts where available.
3. **Paper portfolio and receipts** — latest snapshot time, risk completeness,
   position-level unrealized P&L, and receipt statuses.
4. **ShadowFund comparison** — separate non-executable outcomes, coverage, and
   limitations.
5. **Costs and follow-up** — LLM usage summary if available, open attention
   items, and evidence-backed next questions. Never recommend a trade or change
   execution authority.
