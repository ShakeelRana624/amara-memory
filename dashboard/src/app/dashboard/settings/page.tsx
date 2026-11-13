"use client";

import React, { useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  SettingsIcon,
  ShieldIcon,
  DatabaseIcon,
  CheckIcon,
} from "../../../components/icons";
import { useToast } from "../../../components/Toast";

export default function SettingsPage() {
  const {
    apiUrl,
    tenantId,
    theme,
    toggleTheme,
    isSandbox,
    toggleSandbox,
    refreshHealth,
    isBackendConnected,
    login,
    apiKey,
  } = useAuth();
  const toast = useToast();

  const [formApiUrl, setFormApiUrl] = useState(apiUrl);
  const [formTenantId, setFormTenantId] = useState(tenantId);
  const [decayHalfLife, setDecayHalfLife] = useState(30);
  const [defaultTokenBudget, setDefaultTokenBudget] = useState(2048);
  const [allowHardPurge, setAllowHardPurge] = useState(false);
  const [isTestingProbe, setIsTestingProbe] = useState(false);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (apiKey) {
      await login(apiKey, formApiUrl.trim(), formTenantId.trim());
    }
    toast.success("Platform settings updated successfully");
  };

  const handleTestProbe = async () => {
    setIsTestingProbe(true);
    try {
      const res = await fetch(`${formApiUrl.replace(/\/$/, "")}/api/v1/health`, {
        cache: "no-store",
      });
      if (res.ok) {
        const json = await res.json();
        toast.success(`Connected to AMARA Server v${json.version} (${json.storage_backend})`);
      } else {
        toast.error(`Backend returned status ${res.status}`);
      }
    } catch {
      toast.error("Could not reach backend URL. Is AMARA Server running?");
    } finally {
      setIsTestingProbe(false);
      refreshHealth();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
          Platform Settings
        </h1>
        <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
          Configure API endpoints, tenant boundaries, cognitive decay rates, and security policies
        </p>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-6 max-w-4xl">
        {/* Backend Connectivity */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold flex items-center gap-2">
              <DatabaseIcon className="w-4 h-4 text-indigo-500" />
              Backend Connection & Endpoint
            </h3>
            <div className="flex items-center gap-2">
              {isBackendConnected && !isSandbox ? (
                <span className="text-xs font-mono text-emerald-500 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live Connected
                </span>
              ) : (
                <span className="text-xs font-mono text-amber-500">
                  {isSandbox ? "Sandbox Mode" : "Disconnected"}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            <div>
              <label className="block text-slate-700 dark:text-slate-300 mb-1">
                API Base URL
              </label>
              <div className="flex gap-2">
                <input
                  type="url"
                  required
                  value={formApiUrl}
                  onChange={(e) => setFormApiUrl(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <button
                  type="button"
                  onClick={handleTestProbe}
                  disabled={isTestingProbe}
                  className="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
                >
                  {isTestingProbe ? "Testing..." : "Test Probe"}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-slate-700 dark:text-slate-300 mb-1">
                Tenant Scope ID
              </label>
              <input
                type="text"
                required
                value={formTenantId}
                onChange={(e) => setFormTenantId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between border-t border-slate-100 dark:border-slate-800 text-xs font-mono">
            <span className="text-slate-500">Developer Sandbox Mode:</span>
            <button
              type="button"
              onClick={toggleSandbox}
              className={`px-3 py-1 rounded border text-xs font-mono transition-colors ${
                isSandbox
                  ? "bg-amber-500/20 text-amber-400 border-amber-500/40"
                  : "bg-slate-100 dark:bg-slate-800 text-slate-500 border-slate-300 dark:border-slate-700"
              }`}
            >
              {isSandbox ? "Enabled (Using Sample Data)" : "Disabled (Using Real API)"}
            </button>
          </div>
        </div>

        {/* Cognitive Policies */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4 text-xs font-mono">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold flex items-center gap-2">
            <ShieldIcon className="w-4 h-4 text-amber-500" />
            Epistemic Decay & Context Knapsack
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-700 dark:text-slate-300 mb-1">
                Decay Half-Life (Days)
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={decayHalfLife}
                onChange={(e) => setDecayHalfLife(parseInt(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
              <p className="mt-1 text-[11px] text-slate-400">
                Determines how rapidly confidence scores decay when propositions remain unreinforced.
              </p>
            </div>

            <div>
              <label className="block text-slate-700 dark:text-slate-300 mb-1">
                Default Context Budget (Tokens)
              </label>
              <input
                type="number"
                min="128"
                max="16384"
                step="256"
                value={defaultTokenBudget}
                onChange={(e) => setDefaultTokenBudget(parseInt(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
              <p className="mt-1 text-[11px] text-slate-400">
                Upper token limit allocated for context reconstruction prompt blocks.
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={allowHardPurge}
                onChange={(e) => setAllowHardPurge(e.target.checked)}
                className="rounded border-slate-700 text-indigo-600"
              />
              <span className="text-slate-700 dark:text-slate-300">
                Allow physical row deletion (Hard Purge) without retention lock checks
              </span>
            </label>
          </div>
        </div>

        {/* Appearance & Interface */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4 text-xs font-mono">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold flex items-center gap-2">
            <SettingsIcon className="w-4 h-4 text-cyan-500" />
            Appearance & Session
          </h3>

          <div className="flex items-center justify-between">
            <span className="text-slate-700 dark:text-slate-300">Color Theme:</span>
            <button
              type="button"
              onClick={toggleTheme}
              className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
            >
              Current: {theme === "dark" ? "Dark Theme" : "Light Theme"} (Click to Toggle)
            </button>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <button
            type="submit"
            className="flex items-center gap-1.5 px-6 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-medium transition-colors shadow-lg shadow-indigo-600/20"
          >
            <CheckIcon className="w-4 h-4" />
            Save Platform Settings
          </button>
        </div>
      </form>
    </div>
  );
}
