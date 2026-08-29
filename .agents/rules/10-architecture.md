# Architecture Rules

## Dependency direction

Domain contracts and deterministic policies must not import frameworks or Alpaca clients. API routes and adapters depend inward on application services and ports. Integration details remain behind adapters.

```text
API / scheduler -> application services -> domain rules + ports -> adapters
```

The backend is a modular monolith. Keep explicit boundaries for research, proposal, risk, rules, profiles, market, portfolio, execution, ShadowFund, audit, and shared contracts. Do not create separately deployed services during the hackathon without an approved architecture change.

## Authority chain

Research produces evidence, Proposal creates a candidate, Risk critiques it, deterministic rules authorize or reject it, and Execution translates only an authorized payload. No earlier layer may import or call the execution adapter.

Authorization must bind the proposal digest, ruleset version, AI profile version, allowed order payload, decision time, expiration, and rule trace. A modification becomes executable only after it is represented in a new accepted proposal and reauthorized.

## AI boundaries

- Keep model providers behind a provider-neutral interface.
- Require strict structured outputs and schema validation.
- Record prompt/model/version metadata without storing hidden reasoning.
- Invalid, incomplete, or unparseable AI output fails closed.
- AI Profiles tune only explicitly configurable parameters within hard deterministic limits.

## Data conventions

Use UUID identifiers, UTC timestamps, trace IDs, schema versions, and decimal-safe strings at API boundaries. Persist append-oriented audit events for decisions and executions. Never use a database row as implicit authorization without an immutable decision record.
