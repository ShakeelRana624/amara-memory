"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../../context/AuthContext";
import {
  BrainIcon,
  ShieldIcon,
  ClockIcon,
  NetworkIcon,
  CopyIcon,
  CheckIcon,
  TrashIcon,
  EditIcon,
} from "../../../../components/icons";
import { LifecycleStatusBadge, MemoryCategoryBadge, RelationBadge } from "../../../../components/Badge";
import { Modal } from "../../../../components/Modal";
import { useToast } from "../../../../components/Toast";
import { MemoryInspection } from "../../../../lib/types";

export default function MemoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { client } = useAuth();
  const toast = useToast();

  const memoryId = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);

  const [inspection, setInspection] = useState<MemoryInspection | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedId, setCopiedId] = useState(false);

  // Edit State
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editContent, setEditContent] = useState("");

  // Delete State
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  const loadMemoryDetail = async () => {
    if (!memoryId) return;
    setIsLoading(true);
    try {
      const data = await client.inspectMemory(memoryId);
      setInspection(data);
      setEditContent(data.record.content);
    } catch {
      toast.error("Failed to load memory inspection");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMemoryDetail();
  }, [memoryId]);

  const handleCopyId = () => {
    if (inspection?.record.id) {
      navigator.clipboard.writeText(inspection.record.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inspection || !editContent.trim()) return;
    try {
      await client.updateMemory(inspection.record.id, {
        content: editContent.trim(),
      });
      toast.success("Memory updated");
      setIsEditOpen(false);
      await loadMemoryDetail();
    } catch {
      toast.error("Failed to update memory");
    }
  };

  const handleDelete = async () => {
    if (!inspection) return;
    try {
      await client.deleteMemory(inspection.record.id, false);
      toast.success("Memory marked as tombstoned");
      setIsDeleteOpen(false);
      router.push("/dashboard/memories");
    } catch {
      toast.error("Failed to delete memory");
    }
  };

  if (isLoading) {
    return (
      <div className="p-12 text-center text-xs font-mono text-slate-400">
        Loading cognitive memory provenance...
      </div>
    );
  }

  if (!inspection) {
    return (
      <div className="p-12 text-center text-xs font-mono text-slate-500 space-y-4">
        <div>Memory record not found.</div>
        <Link
          href="/dashboard/memories"
          className="inline-flex items-center gap-1 text-indigo-500 hover:underline"
        >
          Return to Memory Explorer
        </Link>
      </div>
    );
  }

  const { record, relationships, evidence } = inspection;

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
          <Link href="/dashboard/memories" className="hover:text-indigo-500">
            Memory Explorer
          </Link>
          <span>/</span>
          <span className="text-slate-800 dark:text-slate-200 truncate max-w-[200px]">
            {record.id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsEditOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-mono hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
          >
            <EditIcon className="w-3.5 h-3.5" />
            Edit
          </button>
          <button
            onClick={() => setIsDeleteOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 text-rose-500 hover:bg-rose-500/20 text-xs font-mono"
          >
            <TrashIcon className="w-3.5 h-3.5" />
            Tombstone
          </button>
        </div>
      </div>

      {/* Main Header Card */}
      <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <MemoryCategoryBadge category={record.memory_type} />
            <LifecycleStatusBadge status={record.status} />
            <span className="text-xs font-mono text-slate-400">
              v{record.version} • Namespace: {record.namespace}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
            <span>ID:</span>
            <span className="text-slate-700 dark:text-slate-300">{record.id}</span>
            <button
              onClick={handleCopyId}
              className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              title="Copy ID"
            >
              {copiedId ? <CheckIcon className="w-3.5 h-3.5 text-emerald-400" /> : <CopyIcon className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <div>
          <h2 className="text-lg font-mono font-bold text-slate-900 dark:text-slate-100 leading-relaxed">
            {record.content}
          </h2>
          {record.normalized_content && record.normalized_content !== record.content && (
            <div className="mt-2 text-xs font-mono text-slate-400 bg-slate-50 dark:bg-slate-950/40 p-2.5 rounded border border-slate-100 dark:border-slate-800">
              <span className="text-slate-500 uppercase text-[10px] block mb-0.5">
                Normalized Lexical Representation:
              </span>
              {record.normalized_content}
            </div>
          )}
        </div>
      </div>

      {/* Epistemic & Provenance Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="text-xs font-mono text-slate-500 flex items-center justify-between">
            <span>Confidence Score</span>
            <ShieldIcon className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {(record.confidence * 100).toFixed(1)}%
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            Epistemic certainty score
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="text-xs font-mono text-slate-500 flex items-center justify-between">
            <span>Cognitive Salience</span>
            <BrainIcon className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {(record.importance * 100).toFixed(1)}%
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            Retention priority weight
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="text-xs font-mono text-slate-500 flex items-center justify-between">
            <span>Source Attribution</span>
            <ClockIcon className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-2 text-sm font-bold font-mono text-slate-900 dark:text-slate-100 truncate">
            {record.author_id}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400 truncate">
            {record.source_id}
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm">
          <div className="text-xs font-mono text-slate-500 flex items-center justify-between">
            <span>Temporal Interval</span>
            <ClockIcon className="w-4 h-4 text-cyan-500" />
          </div>
          <div className="mt-2 text-xs font-mono text-slate-900 dark:text-slate-100">
            {new Date(record.valid_from).toLocaleDateString()}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-400">
            To: {record.valid_to ? new Date(record.valid_to).toLocaleDateString() : "Indefinite"}
          </div>
        </div>
      </div>

      {/* Relational Graph Associations */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-2">
          <NetworkIcon className="w-4 h-4 text-indigo-500" />
          Associative Knowledge Graph Edges ({relationships.length})
        </h3>

        {relationships.length === 0 ? (
          <p className="text-xs font-mono text-slate-400 py-2">
            No relational edges linked directly to this memory node.
          </p>
        ) : (
          <div className="space-y-2">
            {relationships.map((rel, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-xs font-mono"
              >
                <div className="flex items-center gap-3">
                  <RelationBadge relation={rel.relation_type} />
                  <span className="text-slate-600 dark:text-slate-400">
                    Target: <code className="text-indigo-400">{rel.target_id.slice(0, 12)}...</code>
                  </span>
                </div>
                <div className="text-slate-500 text-[11px]">
                  Edge Weight: {(rel.weight * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Evidence Items */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-2">
          <ShieldIcon className="w-4 h-4 text-emerald-500" />
          Corroborating Evidence Items ({evidence.length})
        </h3>

        {evidence.length === 0 ? (
          <p className="text-xs font-mono text-slate-400 py-2">
            No raw corroborating evidence payloads attached.
          </p>
        ) : (
          <div className="space-y-2">
            {evidence.map((ev) => (
              <div
                key={ev.id}
                className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-xs font-mono space-y-1"
              >
                <div className="flex items-center justify-between text-slate-500 text-[11px]">
                  <span>Source: {ev.source_reference}</span>
                  <span className="text-emerald-500">
                    Evidence Conf: {(ev.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-slate-700 dark:text-slate-300 font-mono text-[11px] break-words">
                  {ev.raw_payload}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Metadata JSON */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">
            Structured Metadata Attributes
          </h3>
          <button
            onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(record.metadata, null, 2));
              toast.info("Metadata JSON copied to clipboard");
            }}
            className="text-xs font-mono text-indigo-500 hover:underline flex items-center gap-1"
          >
            <CopyIcon className="w-3.5 h-3.5" />
            Copy JSON
          </button>
        </div>
        <pre className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 font-mono text-xs text-indigo-300 overflow-x-auto max-h-48">
          {JSON.stringify(record.metadata, null, 2)}
        </pre>
      </div>

      {/* Edit Modal */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Edit Proposition Content"
      >
        <form onSubmit={handleUpdate} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
              Proposition Text
            </label>
            <textarea
              required
              rows={4}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsEditOpen(false)}
              className="px-3 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 text-xs font-mono rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
            >
              Update Record
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete / Tombstone Modal */}
      <Modal
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        title="Tombstone Memory Record"
      >
        <div className="space-y-4 text-xs font-mono">
          <p className="text-slate-600 dark:text-slate-300 font-sans">
            Tombstoning transitions this memory to the <code className="text-rose-400">tombstoned</code> state, preventing it from appearing in standard recall while preserving provenance and audit history.
          </p>
          <div className="flex justify-end gap-2 pt-4">
            <button
              onClick={() => setIsDeleteOpen(false)}
              className="px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              className="px-4 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium"
            >
              Confirm Tombstone
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
