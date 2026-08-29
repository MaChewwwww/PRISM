# Alpaca Documentation Rule

Alpaca APIs, SDKs, CLI commands, MCP tools, account capabilities, and option rules can change. Verify rather than recall.

## Required research order

1. Fetch `https://docs.alpaca.markets/us/llms.txt` to discover current pages.
2. Read the relevant official page by appending `.md` to its documentation URL.
3. Inspect the current OpenAPI specification or endpoint reference for wire shapes.
4. Inspect the locked SDK/CLI release and its changelog or migration guide.
5. For CLI work, run installed `alpaca version`, command `--help`, and `--schema` before changing parsing or invocation.
6. For MCP work, discover the active tool schemas; never infer MCP arguments from REST examples.

Record source URLs and retrieval dates in integration documentation when behavior affects safety, contracts, or compatibility. Prefer official Alpaca sources over tutorials. Treat examples as illustrative when they disagree with executable schemas, and document the discrepancy.

The application uses `alpaca-py` for typed reads and a pinned CLI adapter for gated paper execution. Do not introduce the JavaScript SDK into the frontend or expose Alpaca credentials to browser code.
