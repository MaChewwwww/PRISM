# Trading Safety Rules

## Hard platform controls

- Paper trading is the only supported environment. Any live flag, live host, or inability to prove paper mode stops startup or execution.
- Execution defaults off and requires an active ruleset version.
- The kill switch blocks new orders while leaving monitoring and audit available.
- No frontend route, AI agent, prompt, MCP trading tool, or maintenance script may bypass deterministic authorization.
- Never print, persist in logs, commit, or send Alpaca secrets to a model.

## Execution gate

Before order submission, verify authorization status and expiration, proposal/payload digest, active ruleset, portfolio/account freshness, contract activity, options level, buying power inputs, data freshness, and client order ID. Reconcile an ambiguous result by client order ID; never blindly retry a submission.

Build subprocess calls as argument arrays with JSON on stdin. Do not use a shell. Use explicit timeouts, redact output, and preserve broker errors for audit.

## Initial option envelope

Allow only long calls, long puts, and two-leg long call/put debit spreads. Options use whole-contract quantities, `day` time in force, no extended hours, and active OCC contracts. Spreads require Level 3, one underlying, one expiration, a 1:1 simplified ratio, a net debit limit, and covering long/short legs in the same order. Reject naked short options, credit spreads, equity legs, rolls, more than two legs, and exercises.

BA-owned concentration, drawdown, sizing, liquidity, and freshness thresholds remain TBD. Missing required business configuration returns a deterministic rejection; never substitute example values.
