"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "../../../context/AuthContext";
import {
  NetworkIcon,
  FilterIcon,
  PlusIcon,
} from "../../../components/icons";
import { RelationBadge } from "../../../components/Badge";
import { Modal } from "../../../components/Modal";
import { useToast } from "../../../components/Toast";
import { SAMPLE_MEMORIES } from "../../../lib/sample-data";

interface GraphEdge {
  id: string;
  sourceId: string;
  sourceText: string;
  targetId: string;
  targetText: string;
  relationType: "contradicts" | "derived_from" | "depends_on" | "causal" | "associated_with";
  weight: number;
  reason?: string;
}

const INITIAL_EDGES: GraphEdge[] = [
  {
    id: "edge-1",
    sourceId: SAMPLE_MEMORIES[1].id,
    sourceText: "PostgreSQL 16 connection pool must use PgBouncer in transaction pooling mode...",
    targetId: SAMPLE_MEMORIES[4].id,
    targetText: "Previous cluster configuration used single-AZ deployment in eu-west-1.",
    relationType: "contradicts",
    weight: 0.92,
    reason: "New multi-AZ US-East-1 architecture overrules legacy single-AZ EU deployment.",
  },
  {
    id: "edge-2",
    sourceId: SAMPLE_MEMORIES[5].id,
    sourceText: "Consolidated infrastructure architectural standard: AMARA production instances...",
    targetId: SAMPLE_MEMORIES[0].id,
    targetText: "User requested deployment to US-East-1 AWS region with multi-AZ replication.",
    relationType: "derived_from",
    weight: 0.95,
    reason: "Synthesized during episodic-to-semantic consolidation run #82.",
  },
  {
    id: "edge-3",
    sourceId: SAMPLE_MEMORIES[1].id,
    sourceText: "PostgreSQL 16 connection pool must use PgBouncer in transaction pooling mode...",
    targetId: SAMPLE_MEMORIES[2].id,
    targetText: "Deployment checklist step 1: Run alembic migrations, step 2: Verify pgvector index creation...",
    relationType: "depends_on",
    weight: 0.88,
    reason: "Pool configuration requires alembic migrations to complete first.",
  },
  {
    id: "edge-4",
    sourceId: SAMPLE_MEMORIES[0].id,
    sourceText: "User requested deployment to US-East-1 AWS region with multi-AZ replication.",
    targetId: SAMPLE_MEMORIES[1].id,
    targetText: "PostgreSQL 16 connection pool must use PgBouncer in transaction pooling mode...",
    relationType: "causal",
    weight: 0.85,
    reason: "High throughput requirement triggered connection pooling decision.",
  },
  {
    id: "edge-5",
    sourceId: SAMPLE_MEMORIES[3].id,
    sourceText: "Temporary staging cluster endpoint is staging-db.internal.amara.net...",
    targetId: SAMPLE_MEMORIES[1].id,
    targetText: "PostgreSQL 16 connection pool must use PgBouncer in transaction pooling mode...",
    relationType: "associated_with",
    weight: 0.65,
    reason: "Staging database shared environment parameters.",
  },
];

export default function RelationshipsPage() {
  const { workspace } = useAuth();
  const toast = useToast();

  const [edges, setEdges] = useState<GraphEdge[]>(INITIAL_EDGES);
  const [selectedRelation, setSelectedRelation] = useState<string>("all");
  const [isAddOpen, setIsAddOpen] = useState(false);

  // New Edge State
  const [newSourceId, setNewSourceId] = useState("");
  const [newTargetId, setNewTargetId] = useState("");
  const [newRelation, setNewRelation] = useState<GraphEdge["relationType"]>("associated_with");
  const [newWeight, setNewWeight] = useState(0.85);

  const filteredEdges = edges.filter((e) => {
    if (selectedRelation !== "all" && e.relationType !== selectedRelation) {
      return false;
    }
    return true;
  });

  const handleCreateEdge = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSourceId.trim() || !newTargetId.trim()) return;

    const newEdge: GraphEdge = {
      id: `edge-${Date.now()}`,
      sourceId: newSourceId.trim(),
      sourceText: `Memory Node ${newSourceId.slice(0, 8)}...`,
      targetId: newTargetId.trim(),
      targetText: `Memory Node ${newTargetId.slice(0, 8)}...`,
      relationType: newRelation,
      weight: newWeight,
      reason: "Manually asserted associative link",
    };

    setEdges([newEdge, ...edges]);
    toast.success("Associative graph relationship created");
    setNewSourceId("");
    setNewTargetId("");
    setIsAddOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Associative Relationship Graph
          </h1>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
            Semantic edges, causal chains, and contradiction graphs across namespace: <strong className="text-indigo-500">{workspace}</strong>
          </p>
        </div>

        <button
          onClick={() => setIsAddOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-medium transition-colors shadow-md shadow-indigo-600/20"
        >
          <PlusIcon className="w-3.5 h-3.5" />
          Link Memories
        </button>
      </div>

      {/* Architecture Explainer Callout */}
      <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 text-xs font-mono text-slate-700 dark:text-slate-300 space-y-1">
        <div className="flex items-center gap-2 text-indigo-500 font-semibold">
          <NetworkIcon className="w-4 h-4" />
          Relational Multi-Hop Graph Traversal
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed font-sans">
          AMARA indexes associative edges to enable graph-augmented retrieval. When a query targets a proposition, the engine traverses linked dependencies (<code className="text-amber-400">DEPENDS_ON</code>), checks for active contradictions (<code className="text-rose-400">CONTRADICTS</code>), and expands ancestor lineages (<code className="text-indigo-400">DERIVED_FROM</code>) up to configurable hop depths.
        </p>
      </div>

      {/* Filter Row */}
      <div className="flex items-center justify-between gap-4 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 text-xs font-mono">
        <div className="flex items-center gap-2">
          <FilterIcon className="w-4 h-4 text-slate-400" />
          <span className="text-slate-500">Filter by Edge Relation:</span>
          <select
            value={selectedRelation}
            onChange={(e) => setSelectedRelation(e.target.value)}
            className="px-2.5 py-1 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Relations ({edges.length})</option>
            <option value="contradicts">CONTRADICTS</option>
            <option value="derived_from">DERIVED_FROM</option>
            <option value="depends_on">DEPENDS_ON</option>
            <option value="causal">CAUSAL</option>
            <option value="associated_with">ASSOCIATED_WITH</option>
          </select>
        </div>

        <div className="text-slate-400 text-[11px]">
          Showing {filteredEdges.length} active edge(s)
        </div>
      </div>

      {/* Edges List Cards */}
      <div className="space-y-3">
        {filteredEdges.map((edge) => (
          <div
            key={edge.id}
            className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-3 hover:border-indigo-500/30 transition-colors"
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Source Node */}
              <div className="flex-1 p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-1">
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                  <span className="uppercase tracking-wider">Source Memory</span>
                  <Link
                    href={`/dashboard/memories/${edge.sourceId}`}
                    className="text-indigo-400 hover:underline"
                  >
                    {edge.sourceId.slice(0, 8)}...
                  </Link>
                </div>
                <p className="text-xs font-mono text-slate-800 dark:text-slate-200 line-clamp-2">
                  {edge.sourceText}
                </p>
              </div>

              {/* Edge Relation Badge */}
              <div className="flex flex-col items-center justify-center px-2 flex-shrink-0">
                <RelationBadge relation={edge.relationType} />
                <div className="mt-1 text-[10px] font-mono text-slate-400">
                  Weight: {(edge.weight * 100).toFixed(0)}%
                </div>
              </div>

              {/* Target Node */}
              <div className="flex-1 p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-1">
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                  <span className="uppercase tracking-wider">Target Memory</span>
                  <Link
                    href={`/dashboard/memories/${edge.targetId}`}
                    className="text-indigo-400 hover:underline"
                  >
                    {edge.targetId.slice(0, 8)}...
                  </Link>
                </div>
                <p className="text-xs font-mono text-slate-800 dark:text-slate-200 line-clamp-2">
                  {edge.targetText}
                </p>
              </div>
            </div>

            {edge.reason && (
              <div className="text-[11px] font-mono text-slate-400 bg-slate-50 dark:bg-slate-950/30 px-3 py-1.5 rounded border border-slate-100 dark:border-slate-800/80">
                <span className="text-slate-500 font-semibold mr-1">Semantic Rationale:</span>
                {edge.reason}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Link Memories Modal */}
      <Modal
        isOpen={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        title="Create Knowledge Graph Relationship Edge"
      >
        <form onSubmit={handleCreateEdge} className="space-y-4 text-xs font-mono">
          <div>
            <label className="block text-slate-700 dark:text-slate-300 mb-1">
              Source Memory UUID
            </label>
            <input
              type="text"
              required
              placeholder="e.g. b2c3d4e5-f6a7-8901-bcde-f12345678901"
              value={newSourceId}
              onChange={(e) => setNewSourceId(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-700 dark:text-slate-300 mb-1">
              Target Memory UUID
            </label>
            <input
              type="text"
              required
              placeholder="e.g. a1b2c3d4-e5f6-7890-abcd-ef1234567890"
              value={newTargetId}
              onChange={(e) => setNewTargetId(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-700 dark:text-slate-300 mb-1">
                Relation Type
              </label>
              <select
                value={newRelation}
                onChange={(e) => setNewRelation(e.target.value as GraphEdge["relationType"])}
                className="w-full px-2 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value="contradicts">CONTRADICTS</option>
                <option value="derived_from">DERIVED_FROM</option>
                <option value="depends_on">DEPENDS_ON</option>
                <option value="causal">CAUSAL</option>
                <option value="associated_with">ASSOCIATED_WITH</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-700 dark:text-slate-300 mb-1">
                Edge Weight (0 - 1.0)
              </label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={newWeight}
                onChange={(e) => setNewWeight(parseFloat(e.target.value))}
                className="w-full px-2 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsAddOpen(false)}
              className="px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
            >
              Link Graph Edge
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
