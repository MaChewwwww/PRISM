# Day 1-2 Performance Calibration Review Addendum

Revision: 2026-09-02. This addendum preserves the original Day 1 and Day 2 reports and records corrections and limits discovered during the calibration review. It is not evidence of profitability.

## Observed evidence corrections

- The Day 1 report's window API evidence supports 30 completed cycles, not 74.
- The Day 2 cycle ledger records 144 total cycles: 111 outside regular-market time and 33 in-market. It records 13 approvals, concentrated in NVDA (11) with two GOOGL approvals.
- Repeated approved cycles added exposure to the same thesis. This is a duplicate-thesis control failure, not independent diversification.
- The former reaction calculation compared a long daily-bar window rather than the catalyst timestamp to a fresh market price. Its 100 scores are therefore not usable as catalyst-reaction evidence.
- ShadowFund records are incomplete for the relevant branches. They do not support claims comparing AI alternatives, contrarian branches, or exit policies until identical, complete entry/path/exit quote observations exist.
- The available exit receipts lack filled-average-price evidence for realized exit P&L. Reported position P&L must not be represented as realized strategy exit performance.

## Implemented hypothesis and measurement standard

PRISM now treats a fill as one strategy with a durable entry debit and legs. Marks use the executable close: long-leg bid minus short-leg ask for debit spreads, and the closing bid for long options. The adaptive exit hypothesis is: arm at +20%, trail by 10 percentage points of strategy MFE, and hard-exit at +40%; the fixed -50% hard stop, DTE, force-flatten, thesis invalidation, and stagnation exits remain in force.

The next valid comparison must replay the same timestamped quotes under three policies: legacy +75%/-50%, simple +30%/-50%, and adaptive 20/10/40. Any missing quote makes that comparison unavailable rather than estimated.

## Team decision boundary

Two trading days do not establish a profitable strategy. The ruleset change is a paper-trading, auditable calibration hypothesis. New entries remain enabled through the authorized 2026-09-02 20:00 UTC cutoff; it is not a defensive-only or entry-pause change.
