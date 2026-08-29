# Security

## Trust boundaries

Browsers, provider data, AI output, external APIs, and command output are untrusted. Deterministic validation and authorization sit between every proposal and future paper execution. AI output can inform research, proposals, risk critiques, and bounded recommendations; it cannot grant authority.

## Authentication and credentials

The current skeleton uses seeded operator credentials and an HTTP-only `prism_session` cookie signed by the backend. The login response does not expose the session token. The browser never receives Alpaca or LLM credentials, and the removed demo-credentials endpoint is not replaced with a password-bearing hint. In staging and production, the Login as a Judge route reads the protected server environment and establishes the same session without sending credentials through browser JavaScript. The login form does not auto-fill credentials.

Development may use non-secret local labels. Staging and production reject example/default passwords and session secrets; authentication secrets must be supplied through protected environment configuration. `/api/v1/system/status`, the news-analysis endpoint, and all presentation endpoints require authentication. Liveness and readiness remain unauthenticated for orchestration.

Provider errors are classified and redacted. Logs and API responses may expose credential-presence booleans, never values, account numbers, positions, orders, raw response bodies, or hidden reasoning.

## Execution controls

Live trading is rejected by configuration. Paper execution defaults off and additionally requires a verified paper endpoint, active ruleset/profile compatibility, unexpired `APPROVE`, matching proposal and payload digests, fresh snapshots, supported permissions/contracts, sufficient buying-power inputs, kill-switch clearance, and a client order ID. When autonomous trading is enabled, a configured UTC start/end interval is an additional gate. Production intervals must remain inside the BA-authorized hackathon window; staging may use a separate bounded paper-account rehearsal interval. `REJECT` and `MODIFIED_PENDING_ACCEPTANCE` cannot reach execution.

The current pass does not implement or activate autonomous orchestration or broker submission. Staging and production use separately protected paper credentials; environment selection does not bypass deterministic authorization, paper mode, or the production BA window. Illustrative presentation data never claims a paper account, order, or fill.

## Network and supply chain

Production publishes Nginx only. Databases and caches remain on private networks. CI performs governance checks, lint/type/test/build checks, deterministic contract drift checks, dependency audits, secret scanning, and image scans. Staging and production use distinct protected environments and secrets.

On suspected compromise, disable execution, engage the kill switch, rotate credentials, preserve audit evidence, reconcile any genuine paper orders, and record the incident timeline.
