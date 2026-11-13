"use client";

import React, { useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  SearchIcon,
  SparklesIcon,
  CopyIcon,
  CheckIcon,
} from "../../../components/icons";
import { MemoryCategoryBadge, LifecycleStatusBadge } from "../../../components/Badge";
import { useToast } from "../../../components/Toast";
import {
  ReconstructResponse,
  RetrievalStrategy,
  SearchResponse,
} from "../../../lib/types";

export default function RetrievalPlaygroundPage() {
  const { client, workspace } = useAuth();
  const toast = useToast();

  const [query, setQuery] = useState(
    "What is the recommended database architecture and connection configuration?"
  );
  const [strategy, setStrategy] = useState<RetrievalStrategy>("hybrid");
  const [topK, setTopK] = useState(5);
  const [budgetTokens, setBudgetTokens] = useState(2048);
  const [includeHistorical, setIncludeHistorical] = useState(false);

  const [mode, setMode] = useState<"search" | "reconstruct">("search");
  const [isLoading, setIsLoading] = useState(false);

  // Results
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [reconstructResults, setReconstructResults] = useState<ReconstructResponse | null>(null);
  const [copiedContext, setCopiedContext] = useState(false);

  const sampleQueries = [
    "What is the recommended database architecture and connection configuration?",
    "Deployment checklist for Alembic migrations and pgvector",
    "Staging cluster endpoint and port parameters",
    "Previous single-AZ deployment history",
  ];

  const handleRunRetrieval = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      if (mode === "search") {
        const res = await client.searchMemories({
          query: query.trim(),
          strategy,
          top_k: topK,
          namespace: workspace,
          include_historical: includeHistorical,
        });
        setSearchResults(res);
        setReconstructResults(null);
        toast.success(`Retrieved ${res.results.length} candidate(s) in ${res.latency_ms.toFixed(1)}ms`);
      } else {
        const res = await client.reconstructContext({
          query: query.trim(),
          budget_tokens: budgetTokens,
          strategy,
          namespace: workspace,
        });
        setReconstructResults(res);
        setSearchResults(null);
        toast.success(`Context reconstructed (${res.total_tokens_used} tokens used)`);
      }
    } catch {
      toast.error("Retrieval query failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyFormattedContext = () => {
    if (reconstructResults?.formatted_context) {
      navigator.clipboard.writeText(reconstructResults.formatted_context);
      setCopiedContext(true);
      setTimeout(() => setCopiedContext(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
          Retrieval & Reconstruction Playground
        </h1>
        <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
          Interactive query laboratory for multi-channel hybrid recall and token-bounded context prompt synthesis
        </p>
      </div>

      {/* Main Testing Panel */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
        {/* Sample queries chips */}
        <div className="space-y-1.5">
          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
            Sample Prompt Queries:
          </div>
          <div className="flex flex-wrap gap-2">
            {sampleQueries.map((sq, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setQuery(sq)}
                className="px-2.5 py-1 rounded text-xs font-mono border border-slate-200 dark:border-slate-700 hover:border-indigo-500/50 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors text-left"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={handleRunRetrieval} className="space-y-4 pt-2">
          <div>
            <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
              Natural Language Query / Prompt
            </label>
            <div className="relative">
              <input
                type="text"
                required
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask or query reasoning propositions..."
                className="w-full pl-9 pr-4 py-2.5 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <SearchIcon className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            </div>
          </div>

          {/* Strategy & Options Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <div>
              <label className="block text-slate-500 mb-1">Retrieval Strategy</label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value as RetrievalStrategy)}
                className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200"
              >
                <option value="hybrid">Hybrid (Dense + Lexical + Graph)</option>
                <option value="dense_vector">Dense Vector (pgvector HNSW)</option>
                <option value="lexical_sparse">Lexical Sparse (BM25)</option>
                <option value="temporal_recency">Temporal Recency & Decay</option>
                <option value="relational_graph">Relational Graph Traversal</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-500 mb-1">Execution Mode</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as "search" | "reconstruct")}
                className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200"
              >
                <option value="search">Multi-Channel Candidate Recall</option>
                <option value="reconstruct">Token-Bounded Context Reconstruction</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-500 mb-1">
                {mode === "search" ? `Top K Candidates: ${topK}` : `Token Budget: ${budgetTokens}`}
              </label>
              {mode === "search" ? (
                <input
                  type="range"
                  min="1"
                  max="20"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  className="w-full mt-2 accent-indigo-600"
                />
              ) : (
                <select
                  value={budgetTokens}
                  onChange={(e) => setBudgetTokens(parseInt(e.target.value))}
                  className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200"
                >
                  <option value={512}>512 tokens</option>
                  <option value={1024}>1024 tokens</option>
                  <option value={2048}>2048 tokens</option>
                  <option value={4096}>4096 tokens</option>
                </select>
              )}
            </div>

            <div className="flex items-center gap-2 pt-5">
              <input
                type="checkbox"
                id="incHist"
                checked={includeHistorical}
                onChange={(e) => setIncludeHistorical(e.target.checked)}
                className="rounded border-slate-700 text-indigo-600"
              />
              <label htmlFor="incHist" className="text-slate-600 dark:text-slate-300 text-[11px]">
                Include superseded records
              </label>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-medium transition-colors shadow-lg shadow-indigo-600/20 disabled:opacity-50"
            >
              <SparklesIcon className="w-4 h-4" />
              {isLoading
                ? "Processing..."
                : mode === "search"
                ? "Execute Hybrid Recall"
                : "Reconstruct Context Prompt"}
            </button>
          </div>
        </form>
      </div>

      {/* Results Section */}
      {searchResults && (
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                Recall Matches ({searchResults.results.length})
              </span>
              <span className="text-slate-400">
                Latency: {searchResults.latency_ms.toFixed(1)}ms
              </span>
            </div>
            <div className="text-xs font-mono text-indigo-500">
              Strategy: {strategy}
            </div>
          </div>

          <div className="space-y-3">
            {searchResults.results.map((rec, i) => (
              <div
                key={rec.item.id}
                className="p-4 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-xs font-mono space-y-2 hover:border-indigo-500/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-indigo-500">#{i + 1}</span>
                    <MemoryCategoryBadge category={rec.item.memory_type} />
                    <LifecycleStatusBadge status={rec.item.status} />
                  </div>

                  <div className="flex items-center gap-3 text-[11px]">
                    <span className="text-emerald-500 font-semibold">
                      Relevance: {(rec.relevance_score * 100).toFixed(0)}%
                    </span>
                    <span className="text-slate-400">
                      Conf: {(rec.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <p className="text-slate-800 dark:text-slate-200 text-xs font-mono leading-relaxed">
                  {rec.item.content}
                </p>

                {rec.match_explanation && (
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 p-2 rounded border border-slate-100 dark:border-slate-800/80">
                    <span className="font-semibold text-indigo-400 mr-1">Match Reason:</span>
                    {rec.match_explanation}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reconstruct Result */}
      {reconstructResults && (
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                Grounded Context Synthesis
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                {reconstructResults.total_tokens_used} / {budgetTokens} Tokens Used
              </span>
            </div>

            <button
              onClick={handleCopyFormattedContext}
              className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-indigo-500"
            >
              {copiedContext ? <CheckIcon className="w-3.5 h-3.5 text-emerald-400" /> : <CopyIcon className="w-3.5 h-3.5" />}
              <span>{copiedContext ? "Copied" : "Copy Formatted Context"}</span>
            </button>
          </div>

          <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-950 p-4 font-mono text-xs text-indigo-300 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-96">
            {reconstructResults.formatted_context}
          </div>

          {/* Citations Breakdown */}
          <div className="space-y-2 pt-2">
            <h4 className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold">
              Grounding Citations ({reconstructResults.citations.length})
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {reconstructResults.citations.map((c) => (
                <div
                  key={c.citation_tag}
                  className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-xs font-mono space-y-1"
                >
                  <div className="flex items-center justify-between text-indigo-400 font-bold">
                    <span>{c.citation_tag}</span>
                    <span className="text-[10px] text-slate-400">
                      Anchor: {c.temporal_anchor}
                    </span>
                  </div>
                  <p className="text-slate-700 dark:text-slate-300 text-[11px] line-clamp-2">
                    {c.snippet}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
