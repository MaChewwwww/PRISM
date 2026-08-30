"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Building2,
  CheckCircle2,
  Globe2,
  LineChart,
  Loader2,
  Play,
  Plus,
  X,
} from "lucide-react";

import {
  AGENTS,
  PRESET_TICKERS,
  type AgentAction,
  type PlaygroundResult,
} from "./playground-types";
import { DecisionResult } from "./playground-result-decision";
import { SpecialistResult } from "./playground-result-specialist";

export type { AgentAction } from "./playground-types";

/* ------------------------------------------------------------------ */
/*  Modal                                                             */
/* ------------------------------------------------------------------ */

interface AgentPlaygroundModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialAgentId?: AgentAction;
  initialSymbol?: string;
}

export function AgentPlaygroundModal({
  isOpen,
  onClose,
  initialAgentId = "decision",
  initialSymbol = "NVDA",
}: AgentPlaygroundModalProps) {
  const [selectedAgent, setSelectedAgent] = useState<AgentAction>(initialAgentId);
  const [symbol, setSymbol] = useState(initialSymbol);
  const [catalystSummary, setCatalystSummary] = useState(
    "Strong quarterly earnings beat with upgraded full-year revenue guidance.",
  );
  const [isLoading, setIsLoading] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlaygroundResult | null>(null);

  useEffect(() => {
    if (!isLoading) return;
    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isLoading]);

  if (!isOpen) return null;

  const currentAgent = AGENTS.find((a) => a.id === selectedAgent) ?? AGENTS[0];

  const handleRunAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim()) return;

    setIsLoading(true);
    setElapsedSeconds(0);
    setError(null);
    setResult(null);

    const normSym = symbol.trim().toUpperCase();

    let payload: Record<string, unknown> = { symbol: normSym };
    if (selectedAgent === "reaction") {
      payload = {
        symbol: normSym,
        catalyst_summary: catalystSummary.trim() || `Market movement in ${normSym}`,
        expected_reaction_pct: 3.5,
        bar_limit: 30,
      };
    } else if (selectedAgent === "news") {
      payload = { symbol: normSym, limit: 5 };
    } else if (selectedAgent === "quant" || selectedAgent === "fundamental") {
      payload = { symbol: normSym, bar_limit: 30 };
    }

    try {
      const res = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: selectedAgent, payload }),
      });

      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.error ?? "Failed to execute agent analysis.");
      }
      setResult(json.data as PlaygroundResult);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "An unexpected error occurred while executing the research agent.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/75 p-4 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="playground-title"
    >
      <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-white/10 bg-[#0B0F14] text-slate-100 shadow-2xl shadow-cyan-950/30 overflow-hidden">
        {/* ---- Header ---- */}
        <div className="flex shrink-0 items-center justify-between border-b border-white/10 bg-[#0F151D]/80 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <BrainCircuit className="h-5 w-5" />
            </div>
            <div>
              <h2 id="playground-title" className="text-lg font-semibold tracking-tight text-white">
                Live Agent Playground
              </h2>
              <p className="text-xs text-slate-400">
                Execute and inspect live AI specialist research and master strategy synthesis
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-slate-400 transition hover:bg-white/10 hover:text-white"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ---- Scrollable body ---- */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Agent selector grid */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Select AI Agent to Execute
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {AGENTS.map((agent) => {
                const Icon = agent.icon;
                const isSelected = selectedAgent === agent.id;
                return (
                  <button
                    key={agent.id}
                    type="button"
                    onClick={() => {
                      setSelectedAgent(agent.id);
                      setResult(null);
                      setError(null);
                    }}
                    className={`flex flex-col items-start gap-1.5 rounded-xl border p-3 text-left transition ${
                      isSelected
                        ? "border-cyan-500/60 bg-cyan-500/10 shadow-sm shadow-cyan-500/20"
                        : "border-white/5 bg-[#0F151D] hover:border-white/20 hover:bg-[#16202C]"
                    } ${agent.isAllAgents ? "col-span-2 sm:col-span-2 border-cyan-500/40" : ""}`}
                  >
                    <div className="flex w-full items-center justify-between">
                      <div
                        className="flex h-7 w-7 items-center justify-center rounded-lg"
                        style={{
                          backgroundColor: `${agent.accent}15`,
                          color: agent.accent,
                          border: `1px solid ${agent.accent}30`,
                        }}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white/5 text-slate-300 border border-white/5">
                        {agent.badge}
                      </span>
                    </div>
                    <span className="text-xs font-semibold text-white mt-1">{agent.shortName}</span>
                    <span className="text-[10px] line-clamp-1 text-slate-400">{agent.role}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Form controls */}
          <form
            onSubmit={handleRunAnalysis}
            className="space-y-4 rounded-xl border border-white/5 bg-[#0F151D] p-4"
          >
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
              <div className="flex-1 w-full">
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Target Ticker Symbol
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    placeholder="e.g. NVDA"
                    maxLength={6}
                    required
                    className="w-full rounded-lg border border-white/10 bg-[#0B0F14] px-3.5 py-2 text-sm font-semibold tracking-wider text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  />
                  <button
                    type="submit"
                    disabled={isLoading || !symbol.trim()}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#547D83] hover:bg-[#669299] px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-cyan-950/50 transition disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin text-white" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 fill-white" />
                        Run Agent
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Quick-pick ticker chips */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[11px] text-slate-400 mr-1">Quick Select:</span>
              {PRESET_TICKERS.map((sym) => (
                <button
                  key={sym}
                  type="button"
                  onClick={() => setSymbol(sym)}
                  className={`rounded-md px-2 py-0.5 text-xs font-mono transition border ${
                    symbol === sym
                      ? "border-cyan-500/50 bg-cyan-500/20 text-cyan-300 font-bold"
                      : "border-white/5 bg-white/5 text-slate-300 hover:bg-white/10"
                  }`}
                >
                  {sym}
                </button>
              ))}
            </div>

            {/* Catalyst override for Reaction Agent */}
            {selectedAgent === "reaction" && (
              <div className="pt-2 border-t border-white/5">
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Catalyst / News Summary
                </label>
                <input
                  type="text"
                  value={catalystSummary}
                  onChange={(e) => setCatalystSummary(e.target.value)}
                  placeholder="Describe the catalyst event to test market reaction against"
                  className="w-full rounded-lg border border-white/10 bg-[#0B0F14] px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                />
              </div>
            )}
          </form>

          {/* Loading Pipeline State */}
          {isLoading && (
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-cyan-500/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-500/20 text-cyan-400">
                    <BrainCircuit className="h-5 w-5 animate-spin" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      {currentAgent.isAllAgents
                        ? "Orchestrating 6 Specialist Agents & Master Strategy Synthesis"
                        : `Executing ${currentAgent.name}...`}
                    </h3>
                    <p className="text-xs text-slate-400">
                      Querying Alpaca Market Data & running deep LLM consensus models for {symbol}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 self-start sm:self-center px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs font-mono text-cyan-300">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400" />
                  <span>Elapsed: {elapsedSeconds}s</span>
                </div>
              </div>

              {/* Multi-Agent Stage Pipeline */}
              {currentAgent.isAllAgents ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 pt-1">
                  <div className="rounded-lg border border-white/5 bg-[#0B0F14]/70 p-3 space-y-1">
                    <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold">
                      <LineChart className="h-3.5 w-3.5" />
                      <span>1. Quant & Fund</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      RSI, MACD, Bollinger Bands, Piotroski F & Altman Z
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/5 bg-[#0B0F14]/70 p-3 space-y-1">
                    <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold">
                      <Building2 className="h-3.5 w-3.5" />
                      <span>2. Industry & Peers</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Sector ETF momentum, 20d alpha & peer dispersion
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/5 bg-[#0B0F14]/70 p-3 space-y-1">
                    <div className="flex items-center gap-2 text-pink-400 text-xs font-semibold">
                      <Globe2 className="h-3.5 w-3.5" />
                      <span>3. Macro & News</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      8-benchmark regime registry & news catalysts
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/5 bg-[#0B0F14]/70 p-3 space-y-1">
                    <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold">
                      <Activity className="h-3.5 w-3.5" />
                      <span>4. CIO Synthesis</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Options trade proposal or governed NO_TRADE
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-[#0B0F14]/50 border border-white/5 text-xs text-slate-300">
                  Executing specialized reasoning prompts and deterministic indicators for {symbol}.
                </div>
              )}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-4 text-red-300 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-red-400">
                  Agent Execution Failed
                </h4>
                <p className="text-xs text-red-200">{error}</p>
              </div>
            </div>
          )}

          {/* Results */}
          {result && !isLoading && (
            <div className="space-y-4 animate-in fade-in duration-300">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Live Analysis Results: {symbol}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  Schema v{(!Array.isArray(result) && result.schema_version) || "1.0"}
                </span>
              </div>

              {selectedAgent === "decision" && !Array.isArray(result) ? (
                <DecisionResult data={result} />
              ) : (
                <SpecialistResult agent={selectedAgent} data={result} />
              )}
            </div>
          )}
        </div>

        {/* ---- Footer ---- */}
        <div className="flex shrink-0 items-center justify-between border-t border-white/10 bg-[#0F151D]/80 px-6 py-3 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>FastAPI Research Service Online (:8000)</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/10 px-4 py-1.5 text-xs text-slate-300 hover:bg-white/10 hover:text-white transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

/* ------------------------------------------------------------------ */
/*  Trigger button                                                    */
/* ------------------------------------------------------------------ */

export function TryAgentButton({
  agentId,
  symbol,
  className = "",
  label = "Try Agent",
}: {
  agentId?: AgentAction;
  symbol?: string;
  className?: string;
  label?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className={`inline-flex items-center gap-2 rounded-lg bg-[#547D83] hover:bg-[#669299] px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-cyan-950/40 transition hover:shadow-cyan-500/20 active:scale-95 ${className}`}
        aria-label={label}
      >
        <Plus className="h-4 w-4 stroke-[2.5]" />
        <span>{label}</span>
      </button>

      <AgentPlaygroundModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        initialAgentId={agentId}
        initialSymbol={symbol}
      />
    </>
  );
}
