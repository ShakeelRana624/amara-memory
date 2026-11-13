"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  RefreshIcon,
  ActivityIcon,
  ShieldIcon,
  BrainIcon,
  DatabaseIcon,
} from "../../../components/icons";
import { useToast } from "../../../components/Toast";
import { UsageResponse } from "../../../lib/types";

export default function UsageAnalyticsPage() {
  const { client, workspace, tenantId, isSandbox } = useAuth();
  const toast = useToast();

  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [scopeNamespace, setScopeNamespace] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUsage = async () => {
    setIsLoading(true);
    try {
      const data = await client.getUsage(scopeNamespace ? workspace : undefined);
      setUsage(data);
    } catch {
      toast.error("Failed to load usage statistics");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsage();
  }, [workspace, scopeNamespace, client]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Usage & Cognitive Analytics
            {isSandbox && (
              <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 font-normal">
                Sandbox Mode
              </span>
            )}
          </h1>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
            Epistemic state machine distribution and memory telemetry for tenant: <strong className="text-indigo-500">{tenantId}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs font-mono text-slate-600 dark:text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={scopeNamespace}
              onChange={(e) => setScopeNamespace(e.target.checked)}
              className="rounded border-slate-700 text-indigo-600"
            />
            <span>Filter by workspace ({workspace})</span>
          </label>

          <button
            onClick={fetchUsage}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
            title="Refresh analytics"
          >
            <RefreshIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Top Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono">
            <span>Total Memories</span>
            <BrainIcon className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {isLoading ? "..." : usage?.total_memories ?? 0}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            Across all lifecycle states
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono">
            <span>Epistemic Certainty</span>
            <ShieldIcon className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {isLoading ? "..." : `${((usage?.average_confidence ?? 0.95) * 100).toFixed(1)}%`}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            Average confidence score
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono">
            <span>Cognitive Salience</span>
            <ActivityIcon className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {isLoading ? "..." : `${((usage?.average_importance ?? 0.75) * 100).toFixed(1)}%`}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            Average importance weight
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono">
            <span>Partition Scope</span>
            <DatabaseIcon className="w-4 h-4 text-cyan-500" />
          </div>
          <div className="mt-2 text-base font-bold font-mono text-slate-900 dark:text-slate-100 truncate">
            {scopeNamespace ? workspace : "All Namespaces"}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            Tenant: {tenantId}
          </div>
        </div>
      </div>

      {/* Deep Distribution Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Memory Types */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Memory Category Distribution
          </h3>

          <div className="space-y-4 pt-2">
            {[
              { key: "semantic", label: "Semantic Memories", color: "bg-indigo-500" },
              { key: "episodic", label: "Episodic Observations", color: "bg-cyan-500" },
              { key: "procedural", label: "Procedural Skills", color: "bg-emerald-500" },
              { key: "working", label: "Working Context Buffers", color: "bg-amber-500" },
              { key: "associative", label: "Associative Links", color: "bg-purple-500" },
            ].map((cat) => {
              const count = usage?.by_category?.[cat.key] || 0;
              const total = usage?.total_memories || 1;
              const pct = Math.round((count / total) * 100);

              return (
                <div key={cat.key} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-700 dark:text-slate-300 font-medium">
                      {cat.label}
                    </span>
                    <span className="text-slate-500">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${cat.color} transition-all duration-300`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* State Machine Statuses */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Epistemic Lifecycle State Breakdown
          </h3>

          <div className="space-y-2 pt-2">
            {[
              {
                key: "active",
                label: "Active",
                desc: "Full weight in recall and context synthesis",
                badge: "text-emerald-500 bg-emerald-500/10",
              },
              {
                key: "decaying",
                label: "Decaying",
                desc: "Fading relevance under exponential half-life",
                badge: "text-amber-500 bg-amber-500/10",
              },
              {
                key: "consolidated",
                label: "Consolidated",
                desc: "Synthesized into generalized semantic propositions",
                badge: "text-indigo-500 bg-indigo-500/10",
              },
              {
                key: "superseded",
                label: "Superseded",
                desc: "Overruled by newer verified contradictions",
                badge: "text-slate-400 bg-slate-500/10",
              },
              {
                key: "archived",
                label: "Archived",
                desc: "Preserved in cold store for compliance/audit",
                badge: "text-slate-400 bg-slate-500/10",
              },
            ].map((st) => {
              const count = usage?.by_status?.[st.key] || 0;

              return (
                <div
                  key={st.key}
                  className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-xs font-mono"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${st.badge}`}>
                        {st.label}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{st.desc}</div>
                  </div>
                  <div className="text-sm font-bold text-slate-700 dark:text-slate-300">
                    {count}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
