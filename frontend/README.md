# Frontend

This Next.js application is an authenticated, story-first prototype for the governed paper-trading system. It is an information-architecture and interaction baseline, not final designer-owned visual authority.

## Product routes

- `/` summarizes the Active Portfolio for a selected period with outcome, agent-usage, and improvement views.
- `/stories` and `/stories/[storyId]` keep catalyst, agent interpretation, deterministic governance, outcome, counterfactual, and lesson in one chronology.
- `/portfolio` compares the Active Portfolio view with the strongest simulated ShadowFund path.
- `/alternatives` and `/alternatives/[sessionId]` explain non-executable counterfactual branches.
- `/news` reserves an Alpaca News-shaped read model without making a provider request.
- `/agents` and `/agents/[agentId]` show fictional run cadence, model/prompt metadata, token usage, tools, and planned MCP capabilities without hidden reasoning.
- `/rules` explains immutable hard controls and provides a browser-local, non-authoritative draft preview. Activation remains disabled.

Legacy research, proposal, execution, audit, profile, and ShadowFund URLs redirect into the story-first routes. There is no user-facing System route; the backend status endpoint remains operational but is not consumed by the product UI.

## Data and component boundaries

- Authentication is live. Workspace data is loaded by the server-side presentation adapter and typed from generated OpenAPI contracts.
- The Active Portfolio label describes the current chosen portfolio view; provenance metadata remains explicit when the backend serves an illustrative fixture.
- Generated API types remain under `src/types` and must not be hand-edited.
- Generated UI primitives live in `src/components/ui`; product composition lives in `src/components/product` and feature directories.
- Recharts receives numbers only inside chart presentation adapters. Exact financial fixture values remain decimal strings and are available in accessible tables.
- Every surface identifies its actual source. The current backend fixture remains labeled in provenance metadata; it never implies a broker account, fill, or order.

The staging and production login forms do not auto-fill credentials. When configured, they offer a Login as a Judge action that uses protected server environment values to establish the HTTP-only session; the password is never sent to browser JavaScript or exposed by a hint endpoint.

From the repository root, use `pnpm dev`, `pnpm test`, and `pnpm verify`.
