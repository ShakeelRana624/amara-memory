"use client";

import React, { useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  FolderIcon,
  PlusIcon,
  CheckIcon,
  BrainIcon,
  ShieldIcon,
} from "../../../components/icons";
import { Modal } from "../../../components/Modal";
import { useToast } from "../../../components/Toast";

export default function WorkspacesPage() {
  const { workspace, workspaces, setWorkspace, addWorkspace, tenantId } = useAuth();
  const toast = useToast();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newNamespace, setNewNamespace] = useState("");
  const [description, setDescription] = useState("");

  const handleCreateWorkspace = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNamespace.trim()) return;
    const clean = newNamespace.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "-");
    addWorkspace(clean);
    toast.success(`Created and switched to workspace "${clean}"`);
    setNewNamespace("");
    setDescription("");
    setIsCreateOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Projects & Workspaces
          </h1>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
            Tenant-isolated namespace partitions for agent reasoning loops and sub-tasks
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-medium transition-colors shadow-md shadow-indigo-600/20"
        >
          <PlusIcon className="w-3.5 h-3.5" />
          New Workspace
        </button>
      </div>

      {/* Info Callout */}
      <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 text-xs font-mono text-slate-700 dark:text-slate-300 space-y-1">
        <div className="flex items-center gap-2 text-indigo-500 font-semibold">
          <ShieldIcon className="w-4 h-4" />
          Multi-Tenant Isolation Architecture
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed font-sans">
          All workspaces belong to tenant <strong>{tenantId}</strong>. Each workspace maintains an isolated vector similarity index, BM25 vocabulary cache, and context recall boundary so observations from one agent cannot pollute another.
        </p>
      </div>

      {/* Workspaces Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workspaces.map((ws) => {
          const isCurrent = ws === workspace;

          return (
            <div
              key={ws}
              className={`p-5 rounded-xl border transition-all ${
                isCurrent
                  ? "border-indigo-500/50 bg-indigo-50/50 dark:bg-indigo-950/20 shadow-md ring-1 ring-indigo-500/20"
                  : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:border-slate-300 dark:hover:border-slate-700"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                      isCurrent
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                    }`}
                  >
                    <FolderIcon className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100">
                      {ws}
                    </h3>
                    <div className="text-[10px] font-mono text-slate-400">
                      Tenant: {tenantId}
                    </div>
                  </div>
                </div>

                {isCurrent && (
                  <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Active
                  </span>
                )}
              </div>

              <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs font-mono">
                <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                  <BrainIcon className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Isolated Memory Store</span>
                </div>

                {!isCurrent ? (
                  <button
                    onClick={() => {
                      setWorkspace(ws);
                      toast.info(`Switched active workspace to "${ws}"`);
                    }}
                    className="px-2.5 py-1 rounded text-xs font-mono border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
                  >
                    Select
                  </button>
                ) : (
                  <span className="text-[11px] font-mono text-indigo-500 flex items-center gap-1">
                    <CheckIcon className="w-3.5 h-3.5" />
                    Current
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal: New Workspace */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Provision New Namespace / Workspace"
      >
        <form onSubmit={handleCreateWorkspace} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
              Workspace Identifier (Slug)
            </label>
            <input
              type="text"
              required
              placeholder="e.g. eval-benchmark-run-01"
              value={newNamespace}
              onChange={(e) => setNewNamespace(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <p className="mt-1 text-[11px] font-mono text-slate-400">
              Only alphanumeric characters, dashes, and underscores.
            </p>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
              Description / Notes (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="Intended purpose for this cognitive memory domain..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-3 py-1.5 text-xs font-mono rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 text-xs font-mono rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
            >
              Create Workspace
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
