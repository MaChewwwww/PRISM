# Frontend

This Next.js application is an authenticated, story-first prototype for the governed paper-trading system. It is an information-architecture and interaction baseline, not final designer-owned visual authority.

## Product routes

- `/` summarizes a selected period with portfolio, outcome, agent-usage, and improvement views.
- `/stories` and `/stories/[storyId]` keep catalyst, agent interpretation, deterministic governance, outcome, counterfactual, and lesson in one chronology.
- `/portfolio` compares an illustrative paper-shaped account with the strongest simulated ShadowFund path.
- `/alternatives` and `/alternatives/[sessionId]` explain non-executable counterfactual branches.
- `/news` reserves an Alpaca News-shaped read model without making a provider request.
- `/agents` and `/agents/[agentId]` show fictional run cadence, model/prompt metadata, token usage, tools, and planned MCP capabilities without hidden reasoning.
- `/rules` explains immutable hard controls and provides a browser-local, non-authoritative draft preview. Activation remains disabled.

Legacy research, proposal, execution, audit, profile, and ShadowFund URLs redirect into the story-first routes. There is no user-facing System route; the backend status endpoint remains operational but is not consumed by the product UI.

## Data and component boundaries

- Authentication is live. All other frontend data is fixed and fictional.
- Typed view models and loaders live under `src/features/story`; future backend loaders should replace that boundary without changing page inputs.
- Generated API types remain under `src/types` and must not be hand-edited.
- Generated UI primitives live in `src/components/ui`; product composition lives in `src/components/product` and feature directories.
- Recharts receives numbers only inside chart presentation adapters. Exact financial fixture values remain decimal strings and are available in accessible tables.
- Every fixture surface identifies illustrative paper results, simulated alternatives, or planned integrations.

From the repository root, use `pnpm dev`, `pnpm test`, and `pnpm verify`.
