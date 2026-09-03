"""Run PRISM's evidence-qualified PostAnalysisAgent for the trading week on demand.

Gathers weekly proposals, authorizations, receipts, and ShadowFund counterfactuals,
runs the PostAnalysisAgent through LLMGateway, produces bounded AI Profile recommendations
and structured key findings, persists the batch to the database, and optionally applies
automatic profile governance if enabled.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.autonomous.worker import (
    POST_ANALYSIS_AGENT_VERSION,
    WORKER_VERSION,
)
from app.core.config import get_settings
from app.core.database import create_database
from app.llm.gateway import LLMGateway
from app.profiles.service import ProfileGovernanceService
from app.research.post_analysis import PostAnalysisAgent
from app.rules.registry import get_authorized_ruleset
from app.shadowfund.service import ShadowFundService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("weekly_post_analysis")


async def run_post_analysis(
    *,
    source_mode: str = "production",
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> str:
    settings = get_settings()
    engine, sessionmaker = create_database(settings.database_url)

    try:
        async with sessionmaker() as session:
            ruleset = get_authorized_ruleset()
            window = ruleset.parameters.hackathon_window
            now = datetime.now(UTC)

            start = window_start or window.trading_start_at
            end = window_end or min(now, window.official_scoring_at)

            logger.info("=" * 60)
            logger.info("PRISM ON-DEMAND WEEKLY POST-ANALYSIS")
            logger.info("Trading Window: %s to %s", start.isoformat(), end.isoformat())
            logger.info("Source Mode: %s", source_mode)
            logger.info("=" * 60)

            agent = PostAnalysisAgent(LLMGateway(settings))
            active_profile = await ProfileGovernanceService().get_active(session)
            profile_name = active_profile.name if active_profile else "baseline"
            logger.info("Active AI Profile: %s", profile_name)

            summary, recommendations = await agent.analyze_week(
                session,
                window_start=start,
                window_end=end,
                source_mode=source_mode,
                active_profile=active_profile,
            )

            logger.info("Analysis Summary:\n%s", json.dumps(summary, indent=2))
            logger.info(
                "Recommendations (%d generated):\n%s",
                len(recommendations),
                json.dumps(recommendations, indent=2),
            )

            shadow_service = ShadowFundService()
            batch = await shadow_service.persist_post_analysis_batch(
                session,
                source_mode=source_mode,
                window_start=start,
                window_end=end,
                model_metadata={
                    "trigger": "on_demand_weekly_post_analysis",
                    "agent": POST_ANALYSIS_AGENT_VERSION,
                    "worker": WORKER_VERSION,
                    "timestamp": now.isoformat(),
                },
                summary=summary,
                recommendations=recommendations,
            )
            await session.commit()
            logger.info(
                "Successfully persisted batch: id=%s state=%s", batch.id, batch.state
            )

            await ProfileGovernanceService().apply_automatic_if_enabled(
                session,
                batch_id=batch.id,
                operator_id=settings.auth_email,
            )
            await session.commit()
            logger.info("Post-analysis pipeline completed successfully!")
            return batch.id
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run PRISM on-demand weekly post-analysis."
    )
    parser.add_argument(
        "--source-mode",
        choices=["production", "staging"],
        default="production",
        help="Source mode filter (default: production).",
    )
    parser.add_argument(
        "--window-start",
        type=str,
        default=None,
        help="Optional window start ISO timestamp.",
    )
    parser.add_argument(
        "--window-end",
        type=str,
        default=None,
        help="Optional window end ISO timestamp.",
    )
    args = parser.parse_args()

    start = (
        datetime.fromisoformat(args.window_start).astimezone(UTC)
        if args.window_start
        else None
    )
    end = (
        datetime.fromisoformat(args.window_end).astimezone(UTC)
        if args.window_end
        else None
    )

    asyncio.run(
        run_post_analysis(
            source_mode=args.source_mode,
            window_start=start,
            window_end=end,
        )
    )


if __name__ == "__main__":
    main()
