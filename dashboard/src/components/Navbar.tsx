"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "../context/AuthContext";
import {
  BrainIcon,
  MoonIcon,
  SunIcon,
  PlusIcon,
} from "./icons";
import { Modal } from "./Modal";
import { useToast } from "./Toast";

export function Navbar() {
  const {
    workspace,
    workspaces,
    setWorkspace,
    addWorkspace,
    theme,
    toggleTheme,
    isBackendConnected,
    isSandbox,
    toggleSandbox,
    tenantId,
    apiKey,
    logout,
  } = useAuth();

  const toast = useToast();
  const [isAddWorkspaceOpen, setIsAddWorkspaceOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");

  const handleCreateWorkspace = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    addWorkspace(newWorkspaceName.trim().toLowerCase().replace(/\s+/g, "-"));
    toast.success(`Switched to workspace "${newWorkspaceName.trim()}"`);
    setNewWorkspaceName("");
    setIsAddWorkspaceOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md">
      <div className="flex items-center justify-between h-16 px-4 sm:px-6">
        {/* Brand identity */}
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600/10 text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-400 border border-indigo-500/30 group-hover:scale-105 transition-transform">
              <BrainIcon className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-wider font-mono text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                AMARA
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                  v0.1
                </span>
              </span>
              <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono hidden sm:inline">
                Cognitive Memory Platform
              </span>
            </div>
          </Link>

          {/* Workspace Switcher */}
          <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-200 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
              Namespace:
            </span>
            <div className="relative inline-flex items-center">
              <select
                value={workspace}
                onChange={(e) => {
                  if (e.target.value === "__new__") {
                    setIsAddWorkspaceOpen(true);
                  } else {
                    setWorkspace(e.target.value);
                    toast.info(`Active workspace: ${e.target.value}`);
                  }
                }}
                className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs font-mono rounded-md py-1.5 pl-2.5 pr-8 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer appearance-none"
              >
                {workspaces.map((ws) => (
                  <option key={ws} value={ws}>
                    {ws}
                  </option>
                ))}
                <option value="__new__">+ New Workspace...</option>
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
                <svg className="w-3 h-3 fill-current" viewBox="0 0 20 20">
                  <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Right controls: Connection status, Sandbox pill, Theme, Tenant */}
        <div className="flex items-center gap-3">
          {/* Connection probe indicator */}
          <div className="hidden lg:flex items-center gap-2">
            {isBackendConnected && !isSandbox ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Backend: Connected</span>
              </div>
            ) : (
              <button
                onClick={toggleSandbox}
                title="Click to toggle sandbox / real backend"
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>Sandbox Mode</span>
              </button>
            )}
          </div>

          {/* Tenant pill */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            <span className="text-slate-400">Tenant:</span>
            <span className="font-semibold">{tenantId}</span>
          </div>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle Dark/Light Mode"
            className="p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>

          {/* Auth status / link */}
          {apiKey ? (
            <button
              onClick={() => {
                logout();
                toast.info("Logged out from AMARA session");
              }}
              className="text-xs font-mono px-3 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              Disconnect
            </button>
          ) : (
            <Link
              href="/login"
              className="text-xs font-mono px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors shadow-sm"
            >
              Connect API
            </Link>
          )}
        </div>
      </div>

      {/* New Workspace Modal */}
      <Modal
        isOpen={isAddWorkspaceOpen}
        onClose={() => setIsAddWorkspaceOpen(false)}
        title="Create New Workspace / Namespace"
      >
        <form onSubmit={handleCreateWorkspace} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1">
              Workspace Identifier (Namespace)
            </label>
            <input
              type="text"
              required
              placeholder="e.g. customer-support-agent"
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
              className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Namespaces logically isolate memory partitions, vector spaces, and recall contexts within the same tenant.
            </p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsAddWorkspaceOpen(false)}
              className="px-3 py-1.5 text-xs font-mono rounded-md border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-md bg-indigo-600 text-white hover:bg-indigo-700 font-medium"
            >
              <PlusIcon className="w-3.5 h-3.5" />
              Create Workspace
            </button>
          </div>
        </form>
      </Modal>
    </header>
  );
}

