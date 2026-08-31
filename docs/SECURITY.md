# Security

## Trust boundaries

Browsers, provider data, AI output, external APIs, and command output are untrusted. Deterministic validation and authorization sit between every proposal and future paper execution. AI output can inform research, proposals, risk critiques, and bounded recommendations; it cannot grant authority.

## Authentication and credentials

The current skeleton uses seeded operator credentials and an HTTP-only `prism_session` cookie signed by the backend. The login response does not expose the session token. The browser never receives Alpaca or LLM credentials, and the removed demo-credentials endpoint is not replaced with a password-bearing hint. In staging and production, the Login as a Judge route reads the protected server environment and establishes the same session without sending credentials through browser JavaScript. The login form does not auto-fill credentials.

Development may use non-secret local labels. Staging and production reject example/default passwords and session secrets; authentication secrets must be supplied through protected environment configuration. `/api/v1/system/status`, the news-analysis endpoint, and all presentation endpoints require authentication. Liveness and readiness remain unauthenticated for orchestration.

Provider errors are classified and redacted. Logs and redacted system-status responses may expose credential-presence booleans, never values, account numbers, raw provider position/order records, raw response bodies, or hidden reasoning. Authenticated autonomous portfolio read models may expose only their documented normalized position projection.

Authenticated autonomous operational read models expose only normalized cycle,
authorization, receipt, and persisted-portfolio fields. They never invoke the
worker or providers on behalf of the browser and omit account identifiers,
client/broker order identifiers, raw broker messages, raw provider payloads,
credentials, and hidden reasoning.

## Execution controls

Live trading is rejected by configuration. Paper execution defaults off and additionally requires a verified paper endpoint, active ruleset/profile compatibility, unexpired `APPROVE`, matching proposal and payload digests, fresh snapshots, supported permissions/contracts, sufficient buying-power inputs, kill-switch clearance, and a client order ID. Production autonomous trading additionally requires a configured UTC start/end interval within the BA-authorized hackathon window. Staging rejects autonomous trading configuration and uses a separate non-executing historical backtest boundary. `REJECT` and `MODIFIED_PENDING_ACCEPTANCE` cannot reach execution.

AI Profile changes are an authenticated backend-only control plane. A profile recommendation is immutable evidence; activation creates a new, audited successor and supersedes the prior profile without rewriting historic authorizations. Automatic calibration is controlled by the authenticated operator's persisted database preference and fails closed on invalid or incomplete recommendations. Profile changes are bounded by the registry and never instantiate or call an execution adapter.

LLM observability stores provider-reported token counts, model/provider identity, latency, trace ID, and an output digest only. It never stores prompts, credentials, raw model output, or hidden reasoning. Estimated cost is absent unless an operator configures an explicit current rate card; it is not a provider billing ledger.

`SHADOWFUND_ENABLED` is server-only and false by default. In staging it additionally requires the explicit backtest flag and cannot coexist with autonomous trading. ShadowFund has no import or invocation path to the paper CLI, autonomous worker, active-account reads, or execution persistence; its failure is isolated from decision, paper-exit, and portfolio paths. Presentation responses expose redacted provenance/digests only and never credentials or raw provider payloads.

The production autonomous worker remains fail-closed until readiness and deterministic authorization are green. Staging and production use separately protected paper credentials when configured; staging credentials cannot enable the autonomous worker. Environment selection does not bypass deterministic authorization, paper mode, or the production BA window. Illustrative presentation data never claims a paper account, order, or fill.

## Network and supply chain

Production publishes Nginx only. Databases and caches remain on private networks. CI performs governance checks, lint/type/test/build checks, deterministic contract drift checks, dependency audits, secret scanning, and image scans. Staging and production use distinct protected environments and secrets.

On suspected compromise, disable execution, engage the kill switch, rotate credentials, preserve audit evidence, reconcile any genuine paper orders, and record the incident timeline.
