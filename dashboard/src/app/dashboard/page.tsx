"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import {
  BrainIcon,
  ActivityIcon,
  LayersIcon,
  PlusIcon,
  RefreshIcon,
  SparklesIcon,
  ArrowRightIcon,
  ShieldIcon,
  ClockIcon,
} from "../../components/icons";
import { LifecycleStatusBadge, MemoryCategoryBadge } from "../../components/Badge";
import { Modal } from "../../components/Modal";
import { useToast } from "../../components/Toast";
import { MemoryCategory, MemoryItem, UsageResponse } from "../../lib/types";

export default function OverviewPage() {
  const { client, workspace, tenantId, isSandbox, health, refreshHealth } = useAuth();
  const toast = useToast();

  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [recentMemories, setRecentMemories] = useState<MemoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Ingestion Modal State
  const [isIngestOpen, setIsIngestOpen] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState<MemoryCategory>("episodic");
  const [newConfidence, setNewConfidence] = useState(1.0);
  const [newImportance, setNewImportance] = useState(0.7);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Consolidation Trigger State
  const [isConsolidating, setIsConsolidating] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [usageData, memoriesData] = await Promise.all([
        client.getUsage(workspace),
        client.getMemories("all", workspace, "temporal_recency", 10),
      ]);
      setUsage(usageData);
      setRecentMemories(memoriesData.slice(0, 5));
    } catch {
      toast.error("Error loading workspace telemetry");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    refreshHealth();
  }, [workspace, client]);

  const handleIngestMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    setIsSubmitting(true);
    try {
      await client.createMemory({
        content: newContent.trim(),
        memory_type: newCategory,
        confidence: Number(newConfidence),
        importance: Number(newImportance),
        namespace: workspace,
      });
      toast.success("Cognitive proposition ingested and encoded");
      setNewContent("");
      setIsIngestOpen(false);
      await loadData();
    } catch {
      toast.error("Failed to ingest memory");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConsolidate = async () => {
    setIsConsolidating(true);
    try {
      const res = await client.consolidate(workspace);
      toast.success(`Consolidated ${res.consolidated_count} memory cluster(s)`);
      await loadData();
    } catch {
      toast.error("Consolidation run failed");
    } finally {
      setIsConsolidating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Workspace Overview
            {isSandbox && (
              <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 font-normal">
                Sandbox Mode
              </span>
            )}
          </h1>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
            Real-time telemetry for namespace: <strong className="text-indigo-500">{workspace}</strong> (Tenant: {tenantId})
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            title="Refresh metrics"
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
          >
            <RefreshIcon className="w-4 h-4" />
          </button>

          <button
            onClick={handleConsolidate}
            disabled={isConsolidating}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/20 text-xs font-mono font-medium transition-colors disabled:opacity-50"
          >
            <SparklesIcon className="w-3.5 h-3.5" />
            {isConsolidating ? "Consolidating..." : "Consolidate Clusters"}
          </button>

          <button
            onClick={() => setIsIngestOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-medium transition-colors shadow-md shadow-indigo-600/20"
          >
            <PlusIcon className="w-3.5 h-3.5" />
            Ingest Memory
          </button>
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs font-mono">
            <span>Total Memories</span>
            <BrainIcon className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {isLoading ? "..." : usage?.total_memories ?? 0}
          </div>
          <div className="mt-1 text-[11px] font-mono text-emerald-500 flex items-center gap-1">
            <span>Active records across lifecycle</span>
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs font-mono">
            <span>Avg Confidence</span>
            <ShieldIcon className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {isLoading
              ? "..."
              : `${((usage?.average_confidence ?? 0.95) * 100).toFixed(1)}%`}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            Epistemic certainty score
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs font-mono">
            <span>Avg Importance</span>
            <ActivityIcon className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {isLoading
              ? "..."
              : `${((usage?.average_importance ?? 0.75) * 100).toFixed(1)}%`}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            Cognitive salience weight
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs font-mono">
            <span>Engine Backend</span>
            <LayersIcon className="w-4 h-4 text-cyan-500" />
          </div>
          <div className="mt-2 text-base font-bold font-mono text-slate-900 dark:text-slate-100 truncate">
            {health?.storage_backend || "postgresql+pgvector"}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>DB Online • v{health?.version || "0.1.0"}</span>
          </div>
        </div>
      </div>

      {/* Middle Row: Cognitive Category Distribution & Lifecycle State */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Memory Types Breakdown */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">
              Cognitive Category Breakdown
            </h3>
            <span className="text-[11px] font-mono text-indigo-500">
              5-Tier Architecture
            </span>
          </div>

          <div className="space-y-3 pt-2">
            {[
              { key: "semantic", label: "Semantic Concepts", color: "bg-indigo-500" },
              { key: "episodic", label: "Episodic Experiences", color: "bg-cyan-500" },
              { key: "procedural", label: "Procedural Skills", color: "bg-emerald-500" },
              { key: "working", label: "Working Buffer", color: "bg-amber-500" },
              { key: "associative", label: "Associative Links", color: "bg-purple-500" },
            ].map((cat) => {
              const count = usage?.by_category?.[cat.key] || 0;
              const total = usage?.total_memories || 1;
              const pct = Math.round((count / total) * 100);

              return (
                <div key={cat.key} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-700 dark:text-slate-300">
                      {cat.label}
                    </span>
                    <span className="text-slate-500 dark:text-slate-400">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${cat.color}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Lifecycle State Machine */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">
              Lifecycle State Machine
            </h3>
            <span className="text-[11px] font-mono text-emerald-500">
              Epistemic Status
            </span>
          </div>

          <div className="space-y-3 pt-2">
            {[
              { key: "active", label: "Active", desc: "Available for high-priority recall" },
              { key: "decaying", label: "Decaying", desc: "Confidence fading under half-life" },
              { key: "consolidated", label: "Consolidated", desc: "Abstracted into higher-order concept" },
              { key: "superseded", label: "Superseded", desc: "Overruled by newer contradiction" },
              { key: "archived", label: "Archived", desc: "Long-term cold store" },
            ].map((st) => {
              const count = usage?.by_status?.[st.key] || 0;
              return (
                <div
                  key={st.key}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/40 text-xs font-mono"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-indigo-500" />
                    <div>
                      <div className="text-slate-800 dark:text-slate-200 font-medium">
                        {st.label}
                      </div>
                      <div className="text-[10px] text-slate-400">{st.desc}</div>
                    </div>
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

      {/* Recent Memory Stream */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-indigo-500" />
            Recent Memory Ingestions
          </h3>
          <Link
            href="/dashboard/memories"
            className="text-xs font-mono text-indigo-500 hover:text-indigo-400 flex items-center gap-1"
          >
            <span>Explore All</span>
            <ArrowRightIcon className="w-3.5 h-3.5" />
          </Link>
        </div>

        {recentMemories.length === 0 ? (
          <div className="py-8 text-center text-xs font-mono text-slate-500">
            No memories stored yet in this workspace. Click &ldquo;Ingest Memory&rdquo; to add one.
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {recentMemories.map((mem) => (
              <div
                key={mem.id}
                className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-slate-50/50 dark:hover:bg-slate-800/20 px-2 rounded-lg transition-colors"
              >
                <div className="space-y-1 max-w-3xl">
                  <div className="flex items-center gap-2">
                    <MemoryCategoryBadge category={mem.memory_type} />
                    <LifecycleStatusBadge status={mem.status} />
                    <span className="text-[10px] font-mono text-slate-400">
                      v{mem.version} • conf: {(mem.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs font-mono text-slate-800 dark:text-slate-200 line-clamp-2">
                    {mem.content}
                  </p>
                </div>

                <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 sm:text-right">
                  <Link
                    href={`/dashboard/memories/${mem.id}`}
                    className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 text-indigo-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                  >
                    Inspect
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Ingest Proposition Modal */}
      <Modal
        isOpen={isIngestOpen}
        onClose={() => setIsIngestOpen(false)}
        title="Ingest Cognitive Proposition"
      >
        <form onSubmit={handleIngestMemory} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
              Proposition Content / Observation
            </label>
            <textarea
              required
              rows={3}
              placeholder="e.g. User requested primary PostgreSQL replication with HNSW vector index."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
                Category
              </label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                className="w-full px-2 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="episodic">Episodic</option>
                <option value="semantic">Semantic</option>
                <option value="procedural">Procedural</option>
                <option value="working">Working</option>
                <option value="associative">Associative</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
                Confidence (0 - 1.0)
              </label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={newConfidence}
                onChange={(e) => setNewConfidence(parseFloat(e.target.value))}
                className="w-full px-2 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
                Importance (0 - 1.0)
              </label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={newImportance}
                onChange={(e) => setNewImportance(parseFloat(e.target.value))}
                className="w-full px-2 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsIngestOpen(false)}
              className="px-3 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-1.5 text-xs font-mono rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium disabled:opacity-50"
            >
              {isSubmitting ? "Encoding..." : "Ingest Proposition"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
