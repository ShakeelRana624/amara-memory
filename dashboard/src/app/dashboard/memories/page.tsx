"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "../../../context/AuthContext";
import {
  SearchIcon,
  PlusIcon,
  EditIcon,
  TrashIcon,
  RefreshIcon,
} from "../../../components/icons";
import { LifecycleStatusBadge, MemoryCategoryBadge } from "../../../components/Badge";
import { Modal } from "../../../components/Modal";
import { useToast } from "../../../components/Toast";
import { MemoryCategory, MemoryItem } from "../../../lib/types";

export default function MemoryExplorerPage() {
  const { client, workspace } = useAuth();
  const toast = useToast();

  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Ingest Modal
  const [isIngestOpen, setIsIngestOpen] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState<MemoryCategory>("episodic");
  const [newConfidence, setNewConfidence] = useState(1.0);
  const [newImportance, setNewImportance] = useState(0.7);

  // Edit Modal
  const [editingMemory, setEditingMemory] = useState<MemoryItem | null>(null);
  const [editContent, setEditContent] = useState("");

  // Delete Modal
  const [deletingMemory, setDeletingMemory] = useState<MemoryItem | null>(null);
  const [isHardDelete, setIsHardDelete] = useState(false);

  const fetchMemories = async () => {
    setIsLoading(true);
    try {
      const q = searchQuery.trim() || "all";
      const results = await client.getMemories(q, workspace, "temporal_recency", 100);
      setMemories(results);
    } catch {
      toast.error("Failed to fetch memories for active workspace");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMemories();
  }, [workspace]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchMemories();
  };

  // Filtered Memories
  const filteredMemories = useMemo(() => {
    return memories.filter((m) => {
      if (selectedCategory !== "all" && m.memory_type !== selectedCategory) {
        return false;
      }
      if (selectedStatus !== "all" && m.status !== selectedStatus) {
        return false;
      }
      if (searchQuery.trim() && !m.content.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [memories, selectedCategory, selectedStatus, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredMemories.length / pageSize));
  const paginatedMemories = filteredMemories.slice((page - 1) * pageSize, page * pageSize);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    try {
      await client.createMemory({
        content: newContent.trim(),
        memory_type: newCategory,
        confidence: newConfidence,
        importance: newImportance,
        namespace: workspace,
      });
      toast.success("Proposition ingested successfully");
      setNewContent("");
      setIsIngestOpen(false);
      await fetchMemories();
    } catch {
      toast.error("Failed to ingest proposition");
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMemory || !editContent.trim()) return;
    try {
      await client.updateMemory(editingMemory.id, {
        content: editContent.trim(),
      });
      toast.success("Memory updated");
      setEditingMemory(null);
      await fetchMemories();
    } catch {
      toast.error("Failed to update memory");
    }
  };

  const handleDelete = async () => {
    if (!deletingMemory) return;
    try {
      await client.deleteMemory(deletingMemory.id, isHardDelete);
      toast.success(isHardDelete ? "Memory physically purged" : "Memory tombstoned");
      setDeletingMemory(null);
      await fetchMemories();
    } catch {
      toast.error("Failed to delete memory");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Memory Explorer
          </h1>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
            Browse, filter, and inspect cognitive propositions in namespace: <strong className="text-indigo-500">{workspace}</strong>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchMemories}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
            title="Refresh list"
          >
            <RefreshIcon className="w-4 h-4" />
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

      {/* Search & Filters */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm flex flex-col md:flex-row items-center gap-3">
        <form onSubmit={handleSearch} className="flex-1 w-full relative">
          <input
            type="text"
            placeholder="Search proposition content, keywords, or entity terms..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <SearchIcon className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
        </form>

        <div className="flex items-center gap-2 w-full md:w-auto">
          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => {
              setSelectedCategory(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Categories</option>
            <option value="working">Working</option>
            <option value="episodic">Episodic</option>
            <option value="semantic">Semantic</option>
            <option value="procedural">Procedural</option>
            <option value="associative">Associative</option>
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => {
              setSelectedStatus(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="decaying">Decaying</option>
            <option value="consolidated">Consolidated</option>
            <option value="superseded">Superseded</option>
            <option value="archived">Archived</option>
            <option value="tombstoned">Tombstoned</option>
          </select>
        </div>
      </div>

      {/* Memory Data Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-xs font-mono text-slate-400">
            Querying cognitive memory engine...
          </div>
        ) : paginatedMemories.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-slate-500">
            No memories matched the search criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-slate-500 dark:text-slate-400">
                  <th className="py-3 px-4">Proposition</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Salience</th>
                  <th className="py-3 px-4">Source & Author</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {paginatedMemories.map((mem) => (
                  <tr
                    key={mem.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="py-3 px-4 max-w-md">
                      <div className="font-medium text-slate-900 dark:text-slate-100 line-clamp-2">
                        {mem.content}
                      </div>
                      <div className="mt-0.5 text-[10px] text-slate-400 font-mono flex items-center gap-2">
                        <span>ID: {mem.id.slice(0, 8)}...</span>
                        <span>v{mem.version}</span>
                      </div>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <MemoryCategoryBadge category={mem.memory_type} />
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <LifecycleStatusBadge status={mem.status} />
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                          <div
                            className="h-full bg-emerald-500 rounded-full"
                            style={{ width: `${mem.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-[11px] text-slate-600 dark:text-slate-300">
                          {(mem.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                          <div
                            className="h-full bg-amber-500 rounded-full"
                            style={{ width: `${mem.importance * 100}%` }}
                          />
                        </div>
                        <span className="text-[11px] text-slate-600 dark:text-slate-300">
                          {(mem.importance * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap text-[11px] text-slate-500 dark:text-slate-400">
                      <div>{mem.author_id}</div>
                      <div className="text-[10px] text-slate-400 truncate max-w-[120px]">
                        {mem.source_id}
                      </div>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Link
                          href={`/dashboard/memories/${mem.id}`}
                          className="px-2 py-1 rounded text-[11px] border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-indigo-500"
                        >
                          Inspect
                        </Link>
                        <button
                          onClick={() => {
                            setEditingMemory(mem);
                            setEditContent(mem.content);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                          title="Edit Memory"
                        >
                          <EditIcon className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            setDeletingMemory(mem);
                            setIsHardDelete(false);
                          }}
                          className="p-1 rounded text-rose-400 hover:text-rose-500 hover:bg-rose-500/10"
                          title="Delete / Tombstone"
                        >
                          <TrashIcon className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {filteredMemories.length > 0 && (
          <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs font-mono text-slate-500 dark:text-slate-400">
            <div>
              Showing {(page - 1) * pageSize + 1} to{" "}
              {Math.min(page * pageSize, filteredMemories.length)} of{" "}
              {filteredMemories.length} entries
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40"
              >
                Previous
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Ingest Modal */}
      <Modal
        isOpen={isIngestOpen}
        onClose={() => setIsIngestOpen(false)}
        title="Ingest Cognitive Proposition"
      >
        <form onSubmit={handleIngest} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
              Proposition Text
            </label>
            <textarea
              required
              rows={3}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
                Category
              </label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                className="w-full px-2 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
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
                Confidence
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
                Importance
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
              className="px-3 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 text-xs font-mono rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
            >
              Ingest Memory
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        isOpen={!!editingMemory}
        onClose={() => setEditingMemory(null)}
        title="Edit Memory Proposition"
      >
        <form onSubmit={handleUpdate} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
              Updated Content
            </label>
            <textarea
              required
              rows={3}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setEditingMemory(null)}
              className="px-3 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 text-xs font-mono rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
            >
              Save Changes
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deletingMemory}
        onClose={() => setDeletingMemory(null)}
        title="Delete Memory Record"
      >
        <div className="space-y-4 text-xs font-mono">
          <p className="text-slate-600 dark:text-slate-300 font-sans">
            Are you sure you want to delete this memory record?
          </p>
          <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-700 dark:text-slate-300 line-clamp-3">
            {deletingMemory?.content}
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="hardDelete"
              checked={isHardDelete}
              onChange={(e) => setIsHardDelete(e.target.checked)}
              className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="hardDelete" className="text-slate-700 dark:text-slate-300">
              Hard Purge (physically removes from PostgreSQL database instead of soft tombstoning)
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button
              onClick={() => setDeletingMemory(null)}
              className="px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              className="px-4 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium"
            >
              Confirm Deletion
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
