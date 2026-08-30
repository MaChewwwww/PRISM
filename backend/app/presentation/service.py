from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Literal, cast
from zoneinfo import ZoneInfo

from app.presentation.models import (
    Activity,
    AgentObservability,
    AgentRecord,
    AgentRun,
    AlternativeBranch,
    AlternativeCollection,
    AlternativeSession,
    Catalyst,
    ChartPoint,
    DataMode,
    DateRange,
    DecisionCollection,
    DecisionNode,
    Evidence,
    ExposureItem,
    Governance,
    GovernanceVersion,
    HackathonWindow,
    HardRule,
    IllustrativeOutcome,
    NewsCollection,
    NewsRecord,
    OutcomeCount,
    Overview,
    Portfolio,
    Position,
    PresentationEnvelope,
    PresentationMeta,
    ProfileParameter,
    ProfileSuggestion,
    ProfileSummary,
    Provenance,
    RuleCheck,
    StoryDetail,
    StorySummary,
    SystemComponent,
    ToolRecord,
    TranscriptStep,
    WeeklySummary,
)
from app.presentation.ports import FixturePresentationRepository, PresentationRepository
from app.rules.registry import AuthorizedRuleset, get_authorized_ruleset

_PRESENTATION_REPOSITORY: PresentationRepository = FixturePresentationRepository()
FIXTURE_VERSION = _PRESENTATION_REPOSITORY.version
FIXTURE_AS_OF = _PRESENTATION_REPOSITORY.as_of


@lru_cache
def _fixture() -> dict[str, Any]:
    return _PRESENTATION_REPOSITORY.snapshot()


def _date(value: str) -> str:
    return value[:10]


def _in_range(value: str, from_date: str, to_date: str) -> bool:
    observed = _date(value)
    return from_date <= observed <= to_date


def _range(from_time: datetime, to_time: datetime) -> DateRange:
    return DateRange(
        preset="custom",
        from_date=from_time.date().isoformat(),
        to_date=to_time.date().isoformat(),
    )


def _meta(date_range: DateRange | None = None) -> PresentationMeta:
    return PresentationMeta(
        generated_at=datetime.now(UTC),
        as_of=FIXTURE_AS_OF,
        data_mode=DataMode.ILLUSTRATIVE_FIXTURE,
        range=date_range,
    )


def _chart_point(raw: dict[str, Any]) -> ChartPoint:
    return ChartPoint(
        date=str(raw["date"]),
        chosen_path=raw.get("chosenPath"),
        alternative=raw.get("alternative"),
        benchmark=raw.get("benchmark"),
        agent_alternative=raw.get("agentAlternative"),
        reduced_size=raw.get("reducedSize"),
        unhedged=raw.get("unhedged"),
        cash_baseline=raw.get("cashBaseline"),
        pnl=raw.get("pnl"),
        drawdown=raw.get("drawdown"),
    )


def _story_summary(raw: dict[str, Any]) -> StorySummary:
    return StorySummary(
        id=raw["id"],
        occurred_at=raw["occurredAt"],
        symbol=raw["symbol"],
        category=raw["category"],
        title=raw["title"],
        summary=raw["summary"],
        outcome=raw["outcome"],
        rule_result=raw["ruleResult"],
        chosen_path_impact=raw["chosenPathImpact"],
        best_alternative_impact=raw["bestAlternativeImpact"],
        lesson=raw["lesson"],
    )


SPECIALISTS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "news-intelligence",
        "News Agent",
        "news-intelligence@1.0",
        "#38BDF8",
        "Catalyst evidence",
    ),
    (
        "quantitative-analysis",
        "Quantitative Agent",
        "quantitative-analysis@1.0",
        "#22D3EE",
        "Market and option statistics",
    ),
    (
        "industry-intelligence",
        "Industry Agent",
        "industry-intelligence@1.0",
        "#60A5FA",
        "Sector and peer context",
    ),
    (
        "fundamental-analysis",
        "Fundamental Agent",
        "fundamental-analysis@1.0",
        "#A78BFA",
        "Company fundamentals",
    ),
    (
        "macroeconomic-analysis",
        "Macroeconomic Agent",
        "macroeconomic-analysis@1.0",
        "#F472B6",
        "Macro regime evidence",
    ),
    (
        "market-reaction-mispricing",
        "Market Reaction/Mispricing Agent",
        "reaction-mispricing@1.0",
        "#10B981",
        "Reaction-gap synthesis",
    ),
    (
        "trading-decision",
        "Trading Decision Agent",
        "trading-decision@1.0",
        "#34D399",
        "Proposal or NO_TRADE",
    ),
)


def _decision_tree(raw: dict[str, Any]) -> list[DecisionNode]:
    status = "NO_TRADE" if raw["outcome"] == "no_trade" else "complete"
    nodes: list[DecisionNode] = []
    parent: str | None = None
    for index, (agent_id, name, _prompt, _accent, evidence) in enumerate(SPECIALISTS, start=1):
        node_status = status if agent_id == "trading-decision" else "complete"
        if raw["outcome"] == "degraded" and index >= 2:
            node_status = "not_run"
        nodes.append(
            DecisionNode(
                id=agent_id,
                parent_id=parent,
                label=evidence,
                actor=name,
                component_kind="ai_specialist",
                status=node_status,
                detail=(
                    "Illustrative structured output; no model provider was "
                    "contacted for this fixture."
                ),
            )
        )
        parent = agent_id
    if raw["outcome"] not in {"no_trade", "degraded"}:
        nodes.extend(
            [
                DecisionNode(
                    id="risk-management",
                    parent_id=parent,
                    label="Adversarial risk critique",
                    actor="Risk Management",
                    component_kind="risk_ai",
                    status="complete",
                    detail="AI-assisted critique only; it cannot authorize execution.",
                ),
                DecisionNode(
                    id="rules-engine",
                    parent_id="risk-management",
                    label="Deterministic authorization",
                    actor="Rules Engine",
                    component_kind="deterministic",
                    status=raw["ruleResult"],
                    detail=(
                        "PASS, MODIFY, and FAIL are evaluated against the active versioned ruleset."
                    ),
                ),
                DecisionNode(
                    id="paper-outcome",
                    parent_id="rules-engine",
                    label="Illustrative governed outcome",
                    actor="Paper Execution Layer",
                    component_kind="paper",
                    status="illustrative_only",
                    detail=(
                        "The fixture records a possible governed result; "
                        "no broker order was submitted."
                    ),
                ),
            ]
        )
        parent = "paper-outcome"
    nodes.append(
        DecisionNode(
            id="shadowfund",
            parent_id=parent,
            label="Counterfactual evaluation",
            actor="ShadowFund",
            component_kind="shadow",
            status="simulated",
            detail=(
                "Non-executable branches compare alternative outcomes under "
                "the same fixture timeline."
            ),
        )
    )
    return nodes


def _transcript(raw: dict[str, Any]) -> list[TranscriptStep]:
    occurred_at = raw["occurredAt"]
    steps: list[TranscriptStep] = []
    for index, (agent_id, name, prompt, _accent, evidence) in enumerate(SPECIALISTS, start=1):
        steps.append(
            TranscriptStep(
                id=f"{raw['id']}-{agent_id}",
                occurred_at=occurred_at,
                kind="agent_summary",
                actor=name,
                title=evidence,
                summary=(
                    "Validated illustrative structured output with explicit "
                    "limitations and provenance."
                ),
                model="illustrative-model-record",
                prompt_version=prompt,
                input_tokens=900 + index * 120,
                output_tokens=180 + index * 20,
                latency_ms=900 + index * 170,
                evidence_refs=["prism-demo-v1"],
            )
        )
    if raw["outcome"] not in {"no_trade", "degraded"}:
        steps.extend(
            [
                TranscriptStep(
                    id=f"{raw['id']}-risk-management",
                    occurred_at=occurred_at,
                    kind="agent_summary",
                    actor="Risk Management",
                    title="Adversarial critique",
                    summary=(
                        "Reviewed portfolio, volatility, liquidity, and "
                        "contradictory evidence without authorizing the proposal."
                    ),
                    model="illustrative-model-record",
                    prompt_version="risk-management@1.0",
                    input_tokens=1840,
                    output_tokens=380,
                    latency_ms=2200,
                    evidence_refs=["illustrative portfolio snapshot"],
                ),
                TranscriptStep(
                    id=f"{raw['id']}-rules",
                    occurred_at=occurred_at,
                    kind="rule_gate",
                    actor="Deterministic Rules Engine",
                    title=f"{raw['ruleResult']} result recorded",
                    summary=(
                        "The fixture trace uses the BA-authorized baseline; it "
                        "creates no executable authorization record."
                    ),
                    latency_ms=18,
                    evidence_refs=["prism-authorized-baseline@1.0.0"],
                ),
            ]
        )
    return steps


def _rule_checks(raw: dict[str, Any]) -> list[RuleCheck]:
    if raw["outcome"] == "degraded":
        freshness_result: Literal["PASS", "MODIFY", "FAIL", "NOT_EVALUATED"] = "FAIL"
        freshness_code = "STALE_DATA"
        freshness_explanation = "Required comparison evidence exceeded 30 seconds."
    else:
        freshness_result = "PASS"
        freshness_code = "WITHIN_FRESHNESS_WINDOW"
        freshness_explanation = "Required evidence is within 30 seconds."
    authorization: str = raw["ruleResult"]
    economics_result: Literal["PASS", "MODIFY", "FAIL", "NOT_EVALUATED"]
    economics_result = cast(
        Literal["PASS", "MODIFY", "FAIL", "NOT_EVALUATED"],
        authorization if authorization in {"PASS", "MODIFY", "FAIL"} else "NOT_EVALUATED",
    )
    return [
        RuleCheck(
            rule_id="P0-PAPER-ONLY",
            priority="P0",
            name="Paper environment only",
            result="PASS",
            reason_code="PAPER_MODE_CONFIRMED",
            explanation=(
                "The fixture has no broker execution path and represents paper-only behavior."
            ),
        ),
        RuleCheck(
            rule_id="P0-DATA-FRESHNESS",
            priority="P0",
            name="Evidence freshness",
            result=freshness_result,
            reason_code=freshness_code,
            explanation=freshness_explanation,
        ),
        RuleCheck(
            rule_id="P1-TICKER-CONCENTRATION",
            priority="P1",
            name="Ticker concentration",
            result="PASS" if authorization != "MODIFY" else "MODIFY",
            reason_code=(
                "WITHIN_TICKER_CONCENTRATION"
                if authorization != "MODIFY"
                else "TICKER_CONCENTRATION_BREACH"
            ),
            explanation=(
                "Existing plus proposed allocation is evaluated against the authorized 5.0% cap."
            ),
        ),
        RuleCheck(
            rule_id="P4-TRADE-ECONOMICS",
            priority="P4",
            name="Opportunity, EV, and reward/risk gates",
            result=economics_result,
            reason_code=(
                "AUTHORIZED_BASELINE_RESULT" if authorization != "NOT_EVALUATED" else "NO_PROPOSAL"
            ),
            explanation="Score, net EV, and realistic reward/risk are separate mandatory gates.",
        ),
    ]


def _branch(raw: dict[str, Any]) -> AlternativeBranch:
    branch_id = raw["id"]
    label = raw["label"]
    variation = raw["variation"]
    return AlternativeBranch(
        id=branch_id,
        label=label,
        variation=variation.replace("active allocation", "chosen-path allocation"),
        pnl=raw["pnl"],
        delta_vs_chosen=raw["deltaVsChosen"],
        drawdown=raw["drawdown"],
        coverage=raw["coverage"],
        status=raw["status"],
    )


def _story_detail(raw: dict[str, Any]) -> StoryDetail:
    summary = _story_summary(raw)
    evidence = [
        Evidence(
            label=item["label"],
            source="PRISM versioned demonstration fixture",
            observed_at=item["observedAt"],
            provenance=(
                Provenance.SIMULATED
                if "ShadowFund" in item["label"]
                else Provenance.ILLUSTRATIVE_FIXTURE
            ),
        )
        for item in raw["evidence"]
    ]
    outcome = raw["illustrativeOutcome"]
    return StoryDetail(
        **summary.model_dump(),
        catalyst=Catalyst(**raw["catalyst"]),
        market_path=[_chart_point(item) for item in raw["marketPath"]],
        decision_tree=_decision_tree(raw),
        transcript=_transcript(raw),
        rule_checks=_rule_checks(raw),
        illustrative_outcome=IllustrativeOutcome(
            action=outcome["action"],
            status=outcome["status"],
            rationale=outcome["rationale"],
            observed_at=outcome["observedAt"],
        ),
        alternatives=[_branch(item) for item in raw["alternatives"]],
        lessons=raw["lessons"],
        evidence=evidence,
    )


def _portfolio(from_date: str, to_date: str) -> Portfolio:
    raw = _fixture()
    points = [
        _chart_point(item)
        for item in raw["portfolioPoints"]
        if from_date <= item["date"] <= to_date
    ]
    positions = [
        Position(
            symbol="ACME spread",
            allocation="3.2%",
            value="$3,306.88",
            pnl="+$184.00",
            provenance=Provenance.ILLUSTRATIVE_FIXTURE,
        ),
        Position(
            symbol="VELA spread",
            allocation="2.1%",
            value="$2,180.64",
            pnl="+$126.00",
            provenance=Provenance.ILLUSTRATIVE_FIXTURE,
        ),
        Position(
            symbol="Cash reserve",
            allocation="94.7%",
            value="$98,352.48",
            pnl="$0.00",
            provenance=Provenance.ILLUSTRATIVE_FIXTURE,
        ),
    ]
    raw_activities = (
        (
            "2026-08-25T19:45:00Z",
            "ACME position mark updated",
            "Mark-to-market valuation",
            "+$184.00",
        ),
        ("2026-08-21T16:14:00Z", "NOVA no-trade recorded", "No account mutation", "$0.00"),
        (
            "2026-07-29T19:50:00Z",
            "VELA position closed",
            "Take-profit target reached",
            "+$126.00",
        ),
    )
    activities = [
        Activity(
            occurred_at=datetime.fromisoformat(occurred_at.replace("Z", "+00:00")),
            label=label,
            detail=detail,
            amount=amount,
        )
        for occurred_at, label, detail, amount in raw_activities
        if _in_range(occurred_at, from_date, to_date)
    ]
    return Portfolio(
        points=points,
        positions=positions,
        activities=activities,
        exposure=[
            ExposureItem(label="Cash reserve", value="94.7"),
            ExposureItem(label="Defined-risk spreads", value="5.3"),
            ExposureItem(label="Single-leg options", value="0.0"),
        ],
    )


def get_overview(from_time: datetime, to_time: datetime) -> PresentationEnvelope[Overview]:
    date_range = _range(from_time, to_time)
    stories = [
        _story_summary(raw)
        for raw in _fixture()["stories"]
        if _in_range(raw["occurredAt"], date_range.from_date, date_range.to_date)
    ]
    counts = [
        OutcomeCount(
            label=outcome, value=str(sum(story.outcome.value == outcome for story in stories))
        )
        for outcome in ("pass", "modify", "fail", "no_trade", "degraded")
    ]
    return PresentationEnvelope(
        meta=_meta(date_range),
        data=Overview(
            stories=stories,
            portfolio=_portfolio(date_range.from_date, date_range.to_date),
            outcomes=counts,
            recommendations=[
                "Show freshness gaps before research artifacts are accepted.",
                "Prefer bounded spreads when the deterministic regime is VOLATILE.",
                "Treat NO_TRADE as a complete governed decision.",
            ],
        ),
    )


def get_decisions(
    from_time: datetime,
    to_time: datetime,
    *,
    outcome: str | None = None,
    symbol: str | None = None,
) -> PresentationEnvelope[DecisionCollection]:
    date_range = _range(from_time, to_time)
    all_stories = [_story_summary(raw) for raw in _fixture()["stories"]]
    stories = [
        story
        for story in all_stories
        if date_range.from_date <= story.occurred_at.date().isoformat() <= date_range.to_date
        and (not outcome or outcome == "all" or story.outcome.value == outcome)
        and (not symbol or symbol == "all" or story.symbol == symbol)
    ]
    return PresentationEnvelope(
        meta=_meta(date_range),
        data=DecisionCollection(
            stories=stories, symbols=sorted({item.symbol for item in all_stories})
        ),
    )


def get_decision(decision_id: str) -> PresentationEnvelope[StoryDetail] | None:
    raw = next((item for item in _fixture()["stories"] if item["id"] == decision_id), None)
    return None if raw is None else PresentationEnvelope(meta=_meta(), data=_story_detail(raw))


def get_portfolio(from_time: datetime, to_time: datetime) -> PresentationEnvelope[Portfolio]:
    date_range = _range(from_time, to_time)
    return PresentationEnvelope(
        meta=_meta(date_range), data=_portfolio(date_range.from_date, date_range.to_date)
    )


def _alternative(raw: dict[str, Any]) -> AlternativeSession:
    return AlternativeSession(
        id=raw["id"],
        story_id=raw["storyId"],
        occurred_at=raw["occurredAt"],
        symbol=raw["symbol"],
        title=raw["title"],
        summary=raw["summary"],
        chosen_path_pnl=raw["chosenPathPnl"],
        best_branch=raw["bestBranch"],
        alternative_label=raw.get("alternativeLabel"),
        best_delta=raw["bestDelta"],
        coverage=raw["coverage"],
        branches=[_branch(item) for item in raw["branches"]],
        path=[_chart_point(item) for item in raw["path"]],
        limitations=raw["limitations"],
    )


def get_alternatives(
    from_time: datetime, to_time: datetime
) -> PresentationEnvelope[AlternativeCollection]:
    date_range = _range(from_time, to_time)
    sessions = [
        _alternative(raw)
        for raw in _fixture()["alternatives"]
        if _in_range(raw["occurredAt"], date_range.from_date, date_range.to_date)
    ]
    return PresentationEnvelope(
        meta=_meta(date_range), data=AlternativeCollection(sessions=sessions)
    )


def get_alternative(session_id: str) -> PresentationEnvelope[AlternativeSession] | None:
    raw = next((item for item in _fixture()["alternatives"] if item["id"] == session_id), None)
    return None if raw is None else PresentationEnvelope(meta=_meta(), data=_alternative(raw))


def _agent_runs(agent_id: str, index: int) -> list[AgentRun]:
    runs: list[AgentRun] = []
    for run_index, raw in enumerate(_fixture()["stories"], start=1):
        runs.append(
            AgentRun(
                id=f"{agent_id}-run-{run_index}",
                occurred_at=raw["occurredAt"],
                status="degraded" if raw["outcome"] == "degraded" and index > 1 else "complete",
                trigger="normalized illustrative event",
                duration_ms=900 + index * 170 + run_index * 40,
                input_tokens=800 + index * 110 + run_index * 30,
                output_tokens=170 + index * 20,
                cached_tokens=320 if run_index % 2 else 0,
                summary=(
                    "Recorded illustrative structured output; no provider invocation is claimed."
                ),
            )
        )
    return runs


def _agents() -> list[AgentRecord]:
    roles = {
        "news-intelligence": "Classifies catalysts and preserves source provenance.",
        "quantitative-analysis": (
            "Measures price, volume, volatility, option, and analog behavior."
        ),
        "industry-intelligence": "Adds sector, peer, supply-chain, and competitive context.",
        "fundamental-analysis": "Assesses company economics, guidance, valuation, and quality.",
        "macroeconomic-analysis": (
            "Evaluates macro regime, policy, rates, and cross-asset context."
        ),
        "market-reaction-mispricing": (
            "Synthesizes expected versus observed reaction and uncertainty."
        ),
        "trading-decision": "Produces a typed TradeProposal or successful NO_TRADE result.",
    }
    records = [
        AgentRecord(
            id=agent_id,
            name=name,
            role=roles[agent_id],
            cadence="After prior validated specialist artifact"
            if index > 1
            else "On normalized event",
            model="provider-neutral structured model",
            prompt_version=prompt,
            description=f"{name} has research/proposal authority only and cannot call execution.",
            dependencies=[evidence, "Versioned illustrative fixture"],
            stage=index,
            authority="proposal" if agent_id == "trading-decision" else "research",
            accent=accent,
            runs=_agent_runs(agent_id, index),
        )
        for index, (agent_id, name, prompt, accent, evidence) in enumerate(SPECIALISTS, start=1)
    ]
    records.extend(
        [
            AgentRecord(
                id="risk-management",
                name="Risk Management",
                role=(
                    "Challenges proposals with portfolio, regime, liquidity, "
                    "and tail-risk evidence."
                ),
                cadence="After a TradeProposal",
                model="provider-neutral structured model",
                prompt_version="risk-management@1.0",
                description=(
                    "AI-assisted adversarial critique; deterministic rules retain authority."
                ),
                dependencies=["TradeProposal", "Portfolio risk snapshot", "Market regime snapshot"],
                stage=8,
                authority="risk",
                accent="#F59E0B",
                runs=_agent_runs("risk-management", 8),
            ),
            AgentRecord(
                id="post-analysis",
                name="Post-Analysis",
                role=(
                    "Reviews completed chosen and ShadowFund paths and "
                    "recommends bounded profile changes."
                ),
                cadence="Asynchronously after completed evaluation windows",
                model="provider-neutral structured model",
                prompt_version="post-analysis@1.0",
                description=(
                    "Recommendations require deterministic validation and manual operator review."
                ),
                dependencies=["ShadowFund results", "Audit records", "Authorized profile bounds"],
                stage=12,
                authority="recommendation",
                accent="#818CF8",
                runs=_agent_runs("post-analysis", 9),
            ),
        ]
    )
    return records


def _tools() -> list[ToolRecord]:
    return [
        ToolRecord(
            id="presentation-fixture",
            name="Versioned presentation fixture",
            kind="Internal",
            state="used",
            calls=9,
            success_rate="100%",
            median_latency="< 10 ms",
            purpose="Backend-owned illustrative read model; no provider request.",
        ),
        ToolRecord(
            id="alpaca-read-adapter",
            name="Alpaca read adapter",
            kind="SDK",
            state="planned",
            calls=0,
            success_rate="Not used",
            median_latency="Not recorded",
            purpose="Future authenticated paper-account and market-data reads.",
        ),
        ToolRecord(
            id="provider-neutral-llm",
            name="Provider-neutral LLM adapter",
            kind="LLM",
            state="planned",
            calls=0,
            success_rate="Not used for fixture",
            median_latency="Not recorded",
            purpose="Future structured specialist outputs; no fixture invocation is claimed.",
        ),
    ]


def _components() -> list[SystemComponent]:
    return [
        SystemComponent(
            id="risk-management",
            name="Risk Management",
            kind="risk_ai",
            authority="Non-authoritative critique",
            description="Adversarial AI-assisted assessment.",
            stage=8,
        ),
        SystemComponent(
            id="rules-engine",
            name="Deterministic Rules Engine",
            kind="deterministic",
            authority="Sole execution authorization",
            description="Evaluates the exact proposal and snapshot bindings.",
            stage=9,
        ),
        SystemComponent(
            id="paper-execution",
            name="Paper Execution",
            kind="paper_execution",
            authority="Authorized payload translation only",
            description="Disabled by default and unable to trade live.",
            stage=10,
        ),
        SystemComponent(
            id="shadowfund",
            name="ShadowFund",
            kind="shadowfund",
            authority="Non-executable evaluation",
            description="Runs counterfactual branches without an order path.",
            stage=11,
        ),
        SystemComponent(
            id="post-analysis",
            name="Post-Analysis",
            kind="post_analysis",
            authority="Recommendation only",
            description="Suggests bounded AI Profile changes for manual review.",
            stage=12,
        ),
    ]


def get_agents(from_time: datetime, to_time: datetime) -> PresentationEnvelope[AgentObservability]:
    date_range = _range(from_time, to_time)
    agents = deepcopy(_agents())
    for agent in agents:
        agent.runs = [
            run
            for run in agent.runs
            if date_range.from_date <= run.occurred_at.date().isoformat() <= date_range.to_date
        ]
    return PresentationEnvelope(
        meta=_meta(date_range),
        data=AgentObservability(agents=agents, tools=_tools(), components=_components()),
    )


def get_agent(agent_id: str) -> PresentationEnvelope[AgentRecord] | None:
    agent = next((item for item in _agents() if item.id == agent_id), None)
    return None if agent is None else PresentationEnvelope(meta=_meta(), data=agent)


def get_news(
    from_time: datetime,
    to_time: datetime,
    *,
    symbol: str | None = None,
    significance: str | None = None,
) -> PresentationEnvelope[NewsCollection]:
    date_range = _range(from_time, to_time)
    all_items = [
        NewsRecord(
            id=raw["id"],
            published_at=raw["publishedAt"],
            source="PRISM versioned demonstration fixture",
            symbols=raw["symbols"],
            headline=raw["headline"],
            summary=raw["summary"],
            category=raw["category"],
            story_id=raw["storyId"],
            significance=raw["significance"],
        )
        for raw in _fixture()["news"]
    ]
    items = [
        item
        for item in all_items
        if date_range.from_date <= item.published_at.date().isoformat() <= date_range.to_date
        and (not symbol or symbol == "all" or symbol in item.symbols)
        and (not significance or significance == "all" or item.significance == significance)
    ]
    return PresentationEnvelope(
        meta=_meta(date_range),
        data=NewsCollection(
            items=items, symbols=sorted({symbol for item in all_items for symbol in item.symbols})
        ),
    )


def _hard_rules(ruleset: AuthorizedRuleset) -> list[HardRule]:
    p = ruleset.parameters
    window = p.hackathon_window
    eastern = ZoneInfo("America/New_York")

    def _et(value: datetime) -> str:
        local = value.astimezone(eastern)
        return f"{local:%a %b} {local.day} {local:%H:%M} ET"

    return [
        HardRule(
            rule_id="P0-PAPER-ONLY",
            priority="P0",
            name="Paper environment only",
            active_value="paper only",
            explanation="Any live configuration stops startup or execution.",
        ),
        HardRule(
            rule_id="P0-DATA-FRESHNESS",
            priority="P0",
            name="Evidence freshness",
            active_value=f"<= {p.data_freshness_seconds} seconds",
            explanation="Stale pricing, research, or account inputs fail closed.",
        ),
        HardRule(
            rule_id="P0-DRAWDOWN",
            priority="P0",
            name="Drawdown states",
            active_value=(
                f"{p.drawdown_caution_pct}% / {p.drawdown_defensive_pct}% / {p.drawdown_halt_pct}%"
            ),
            explanation="CAUTION, DEFENSIVE, and HALT reduce or block new risk.",
        ),
        HardRule(
            rule_id="P0-CASH-BUFFER",
            priority="P0",
            name="Cash buffer",
            active_value=f">= {p.cash_buffer_pct}%",
            explanation="The reserve is non-bypassable.",
        ),
        HardRule(
            rule_id="P0-HACKATHON-SCORING",
            priority="P0",
            name="Hackathon scoring point",
            active_value=f"EOD {_et(window.official_scoring_at)}; total account equity",
            explanation=(
                "The official score is total account equity at the Thursday close, "
                "not a cash balance."
            ),
        ),
        HardRule(
            rule_id="P1-HACKATHON-ENTRY-CUTOFF",
            priority="P1",
            name="Hackathon new-entry cutoff",
            active_value=_et(window.new_entry_cutoff_at),
            explanation=(
                "No new positions may open after the Wednesday market close; "
                "existing positions may only be managed."
            ),
        ),
        HardRule(
            rule_id="P1-HACKATHON-FORCE-FLATTEN",
            priority="P1",
            name="Hackathon force-flatten",
            active_value=f"by {_et(window.force_flatten_by)}",
            explanation=(
                "All positions must be closed by the scoring point to avoid settlement "
                "assignment or exercise."
            ),
        ),
        HardRule(
            rule_id="P1-TICKER-CAP",
            priority="P1",
            name="Ticker concentration",
            active_value=f"<= {p.ticker_concentration_pct}%",
            explanation="Existing plus proposed allocation is evaluated together.",
        ),
        HardRule(
            rule_id="P1-INSTRUMENT",
            priority="P1",
            name="Options envelope",
            active_value="long options or 1:1 debit spreads",
            explanation="VOLATILE blocks single-leg options; all unsupported structures fail.",
        ),
        HardRule(
            rule_id="P2-RISK-PER-TRADE",
            priority="P2",
            name="Risk per trade",
            active_value=(
                f"{p.max_risk_per_trade_pct}% normal / {p.volatile_risk_per_trade_pct}% volatile"
            ),
            explanation="The hard-stop loss must remain inside the active risk budget.",
        ),
        HardRule(
            rule_id="P2-PORTFOLIO-RISK",
            priority="P2",
            name="Aggregate hard-stop risk",
            active_value=f"<= {p.aggregate_hard_stop_risk_pct}%",
            explanation="Portfolio risk is assessed before authorizing new risk.",
        ),
        HardRule(
            rule_id="P3-LIQUIDITY",
            priority="P3",
            name="Maximum bid/ask spread",
            active_value=f"<= {p.max_bid_ask_spread_pct}% of premium",
            explanation="Poor execution economics reject or modify the proposal.",
        ),
        HardRule(
            rule_id="P3-EXIT",
            priority="P3",
            name="Exit integrity",
            active_value=(
                f"TP {p.take_profit_default_pct}% / SL {p.stop_loss_pct}% / "
                f"DTE <= {p.dte_threshold_default_days}"
            ),
            explanation=(
                "Every position requires deterministic profit, loss, DTE, time, and thesis exits."
            ),
        ),
        HardRule(
            rule_id="P4-EV",
            priority="P4",
            name="Net expected value",
            active_value=f">= +{p.minimum_net_ev_r}R",
            explanation="Execution costs are included before authorization.",
        ),
        HardRule(
            rule_id="P4-REWARD-RISK",
            priority="P4",
            name="Realistic reward/risk",
            active_value=f">= {p.minimum_reward_risk_ratio}:1",
            explanation="Maximum theoretical payoff is not used as expected profit.",
        ),
        HardRule(
            rule_id="P5-OPPORTUNITY",
            priority="P5",
            name="Opportunity competition",
            active_value=(
                f"score >= {p.opportunity_score_floor}; Balanced >= {p.balanced_opportunity_score}"
            ),
            explanation="Only eligible candidates compete for finite risk budget.",
        ),
    ]


def get_governance() -> PresentationEnvelope[Governance]:
    ruleset = get_authorized_ruleset()
    names = {
        "target_position_size_pct": (
            "Target position size",
            "% equity",
            "Target only; deterministic risk caps still apply.",
        ),
        "opportunity_score_threshold": (
            "Opportunity score threshold",
            "score",
            "Minimum score before proposal generation.",
        ),
        "take_profit_pct": (
            "Take-profit target",
            "% initial debit",
            "Must also satisfy realistic reward/risk.",
        ),
        "stop_loss_pct": ("Stop-loss limit", "% initial debit", "Fixed hard stop; not tunable."),
    }
    balanced = ruleset.profiles["balanced"]
    profile_parameters = [
        ProfileParameter(
            id=key,
            name=names[key][0],
            active_value=str(getattr(balanced, key)),
            minimum=str(bound.minimum),
            maximum=str(bound.maximum),
            unit=names[key][1],
            description=names[key][2],
        )
        for key, bound in ruleset.profile_bounds.items()
    ]
    profiles = [
        ProfileSummary(
            key=key,
            status="active" if key == ruleset.default_profile else "available",
            parameters={name: str(value) for name, value in params.model_dump().items()},
        )
        for key, params in ruleset.profiles.items()
    ]
    return PresentationEnvelope(
        meta=_meta(),
        data=Governance(
            ruleset_id=ruleset.ruleset_id,
            ruleset_version=ruleset.version,
            ruleset_status="active",
            active_profile="balanced",
            decision_semantics={
                "PASS": "The individual rule passed unchanged.",
                "MODIFY": "Create a revised proposal and evaluate it again.",
                "FAIL": "Stop the proposal safely.",
                "APPROVE": "The exact payload may progress while authorization remains valid.",
                "REJECT": "The proposal cannot progress.",
                "MODIFIED_PENDING_ACCEPTANCE": (
                    "No execution authority exists; revise and reauthorize."
                ),
            },
            hard_rules=_hard_rules(ruleset),
            profile_parameters=profile_parameters,
            profiles=profiles,
            versions=[
                GovernanceVersion(
                    version=ruleset.version,
                    state="active",
                    summary="BA-authorized operating baseline.",
                ),
            ],
            hackathon_window=HackathonWindow(
                trading_start_at=ruleset.parameters.hackathon_window.trading_start_at,
                official_scoring_at=ruleset.parameters.hackathon_window.official_scoring_at,
                window_outer_boundary_at=ruleset.parameters.hackathon_window.window_outer_boundary_at,
                force_flatten_by=ruleset.parameters.hackathon_window.force_flatten_by,
                new_entry_cutoff_at=ruleset.parameters.hackathon_window.new_entry_cutoff_at,
                effective_max_hold_trading_days=ruleset.parameters.hackathon_max_hold_trading_days,
                scoring_basis=ruleset.parameters.hackathon_window.scoring_basis,
            ),
        ),
    )


def get_weekly_summary() -> PresentationEnvelope[WeeklySummary]:
    return PresentationEnvelope(
        meta=_meta(),
        data=WeeklySummary(
            week_of="2026-08-25",
            stories_analyzed=6,
            illustrative_net_pnl="+$310.00",
            shadow_beat_chosen=2,
            key_findings=[
                "Two ShadowFund branches outperformed the chosen illustrative "
                "path; both used bounded structures.",
                "One story stopped because evidence exceeded the authorized "
                "30-second freshness window.",
                "The fixed 50% stop and defined-risk structure reduced adverse "
                "excursion in the fixture.",
                "NO_TRADE preserved illustrative capital when the reaction gap was not durable.",
            ],
            suggestions=[
                ProfileSuggestion(
                    id="profile-suggestion-score",
                    parameter_id="opportunity_score_threshold",
                    parameter_name="Opportunity score threshold",
                    current_value="84",
                    suggested_value="88",
                    allowed_minimum="75",
                    allowed_maximum="95",
                    confidence="medium",
                    rationale=(
                        "A more selective Balanced draft would have filtered "
                        "marginal fixture candidates. This remains a "
                        "recommendation, not an activation."
                    ),
                    week_of="2026-08-25",
                    validation_state="within_authorized_bounds",
                ),
                ProfileSuggestion(
                    id="profile-suggestion-take-profit",
                    parameter_id="take_profit_pct",
                    parameter_name="Take-profit target",
                    current_value="75.00",
                    suggested_value="85.00",
                    allowed_minimum="75.00",
                    allowed_maximum="100.00",
                    confidence="low",
                    rationale=(
                        "Some bounded fixture branches benefited from a wider "
                        "profit target; evidence remains limited and requires "
                        "manual review."
                    ),
                    week_of="2026-08-25",
                    validation_state="within_authorized_bounds",
                ),
            ],
        ),
    )
