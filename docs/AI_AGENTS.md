# PRISM — AI Agents

**One signal. Multiple perspectives. Better decisions.**

## The PRISM Multi-Perspective Collective

Just as an optical prism separates a single beam of light into its constituent spectral bands, **PRISM** takes a single market signal and autonomously breaks it down into multiple perspectives:
1. **Catalyst & Reaction Perspective (Market Reaction Research Agent):** Analyzes the catalyst, measures price/volume response, and compares with historical analog patterns to detect overreaction/underreaction gaps.
2. **Strategy Perspective (Trade Proposal Agent):** Converts research findings into defined-risk option strategies while exploring parallel shadow candidates.
3. **Risk & Adversarial Perspective (Risk Agent):** Critiques proposed sizing, challenges assumptions, tests regime vulnerabilities, and proposes risk mitigations.
4. **Counterfactual Learning Perspective (Post-Analysis Agent):** Audits realized outcomes against ShadowFund counterfactuals to recommend continuous profile optimizations.

> **One signal → Autonomous perspectives → Governed decisions → Clearer outcomes**

## Authority model

AI components are untrusted decision-support components. They never own broker credentials, deterministic rule definitions, or execution authority.

| Agent | Inputs | Output | Prohibited behavior |
| --- | --- | --- | --- |
| Market Reaction Research | News/event, bars, volume, volatility, analogs | `ResearchReport` | Proposing or placing an order |
| Trade Proposal | Research, portfolio snapshot, active profile | `TradeProposal` or `NO_TRADE` | Claiming authorization |
| Risk | Proposal, portfolio, regime, contradictory evidence | `RiskAssessment` | Overriding hard rules |
| Post-Analysis | Audit, executions, ShadowFund outcomes | `AIProfileRecommendation` | Activating unvalidated parameters or editing rule logic |

## Output contract

Every output uses a versioned strict schema and includes identity, trace ID, timestamps, model/prompt version, concise rationale, assumptions, evidence references, confidence/uncertainty, and explicit failure/no-action outcomes. Free-form text may accompany a valid structure but cannot replace it.

Invalid JSON, missing required fields, unknown enums, out-of-range values, unsupported instruments, or ungrounded identifiers produce a terminal validation error. The system stores the error and does not advance the workflow.

## Strategy synthesis and volatility regime conditioning

The Proposal and Risk Agents operate under strict quantitative volatility filters:

1. **Deterministic IV Conditioning:**
   - The Proposal Agent receives market volatility metrics (`iv_rank`, `iv_to_hv_ratio`, `atm_iv`).
   - When $\text{IV Rank} > 50\%$ or post-earnings volatility is elevated, the Proposal Agent is restricted to **Defined-Risk Debit Spreads** (`call_debit_spread`, `put_debit_spread`). This offsets post-event implied volatility collapse (IV crush) by selling an out-of-the-money leg.
   - When $\text{IV Rank} \le 50\%$, single-leg long options (`long_call`, `long_put`) are permitted to exploit potential volatility expansion.

2. **Deterministic Contract Selection (Anti-Hallucination):**
   - The Proposal Agent selects the strategic thesis, target delta ($\approx 0.50\text{ Delta}$ long leg / $0.30\text{ Delta}$ short leg), and target DTE window ($21\text{ to }45\text{ days}$).
   - A deterministic Option Chain Resolver queries Alpaca's active option chain to bind exact, tradable OCC contract symbols and strikes, preventing LLM strike hallucination.

3. **Risk AI Critique:**
   - Risk AI evaluates whether the proposed strategy introduces adverse vega exposure or tail risk relative to the active regime and portfolio concentration.

4. **Exit Policy Formulation:**
   - Every candidate `TradeProposal` incorporates a structured `ExitPolicy` specifying take-profit targets (default $50\%$), stop-loss limits (default $50\%$), DTE pin-risk boundaries ($\le 7\text{d}$), and maximum holding duration.

5. **Single-Prompt Multi-Perspective Extraction:**
   - In the same inference pass that creates the primary candidate action, the Proposal Agent extracts structured `shadow_candidates` (e.g. contrarian reversal thesis, conservative sizing multiplier, or alternate delta candidate). This provides rich multiverse inputs for ShadowFund with zero extra API latency or token overhead.

## Post-Analysis AI and adaptive profile tuning


Post-Analysis AI acts as an asynchronous, self-auditing intelligence loop:

1. **ShadowFund Counterfactual Audit:**
   - The agent continuously evaluates completed executions against ShadowFund virtual branches (*Do Nothing*, *Reduced Sizing*, *Hedged*).
   - Measures decision regret, drawdown impact, and exit timing efficacy across market volatility regimes.

2. **Exit Policy & Risk Calibration:**
   - Evaluates whether alternate exit parameters (e.g., locking profit at $40\%$ vs $60\%$, or cutting losses at $35\%$ vs $50\%$) would have historically improved portfolio Sharpe ratio and win rate.
   - Synthesizes empirical evidence into structured `AIProfileRecommendation` proposals containing recommended parameter adjustments.

3. **Dual Activation Modes:**
   - **Manual Prescriptive Mode (Default):** Surfaces the recommendation, rationale, and counterfactual comparison to the operator on the UI for manual **Apply / Modify / Reject** review.
   - **Autonomous Guardrailed Mode (Optional):** Automatically switches to the updated profile *only if* all proposed values pass the **Deterministic Profile Validator** within the approved $[20\%, 90\%]$ safety envelope.

## Prompt and model lifecycle




- Store prompt templates by stable name and semantic version.
- Record provider, model identifier, prompt version, contract version, and relevant input digest.
- Do not store hidden chain-of-thought. Store concise user-facing rationale and evidence.
- Evaluate prompt/model changes against fixed replay fixtures before activation.
- Keep provider calls behind an interface so the provider can be changed without changing domain contracts.

## Supported providers and configuration

The system supports pluggable LLM backends configured via environment variables:
- **Featherless AI** (`featherless`): High-throughput, serverless open-weights models (e.g. `DeepSeek-V4-Flash-0731`, `Qwen3.8-Flash-Next`, `Qwen3.8-27B`) via `FEATHERLESS_API_KEY` and `FEATHERLESS_BASE_URL` (`https://api.featherless.ai/v1`).
- **Anthropic** (`anthropic`): Claude models via `ANTHROPIC_API_KEY`.
- **Google Gemini** (`gemini`): Gemini models via `GEMINI_API_KEY`.
- **Ollama** (`ollama`): Local open-weights models via `OLLAMA_BASE_URL`.
- **DeepSeek** (`deepseek`): DeepSeek models via `DEEPSEEK_API_KEY`.
- **OpenAI** (`openai`): OpenAI models via `OPENAI_API_KEY`.

Environment selection is driven by `LLM_PROVIDER` and optional `LLM_MODEL`. When using `featherless`, recommended warm-pool models include `DeepSeek-V4-Flash-0731` for full research/strategy reasoning and `Qwen3.8-Flash-Next` for low-latency JSON extraction.

## Safety and observability

- Agents receive the minimum required context and no Alpaca secret.
- Treat news and external text as untrusted data, not instructions.
- Bound tool access by agent responsibility; research tools are read-only.
- Apply timeouts, retry only safe calls, and record latency/token/error metadata without sensitive content.
- User-visible decision stories may show concise rationale, evidence references, structured outputs, model/prompt versions, latency, token counts, and sanitized tool/MCP invocation summaries. They must never show hidden chain-of-thought or sensitive tool arguments/results.
- Distinguish recorded invocations from configured or planned capabilities. A provider, model, tool, or MCP server is counted only when a run record says it was used.
- NO_CLEAR_EDGE and NO_TRADE are successful outcomes.

## Deferred decisions

The active production model set, evaluation thresholds, and automatic AI Profile switching remain TBD. Infrastructure supports runtime configuration across all supported providers without altering core contracts.
