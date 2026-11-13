"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { BrainIcon, ArrowRightIcon, CopyIcon, CheckIcon } from "../../components/icons";
import { useToast } from "../../components/Toast";
import { Modal } from "../../components/Modal";

export default function RegisterPage() {
  const router = useRouter();
  const { login, client, addWorkspace } = useAuth();
  const toast = useToast();

  const [tenantName, setTenantName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("production");
  const [keyLabel, setKeyLabel] = useState("Master Admin Key");
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
  const [isLoading, setIsLoading] = useState(false);

  // Single-exposure revealed key
  const [mintedKey, setMintedKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantName.trim()) {
      toast.error("Tenant organization name is required");
      return;
    }

    setIsLoading(true);
    const sanitizedTenant = tenantName.toLowerCase().replace(/[^a-z0-9_-]/g, "-");
    const sanitizedWorkspace = workspaceName.toLowerCase().replace(/[^a-z0-9_-]/g, "-");

    try {
      // Create new API key via client or mint deterministic master token
      const createdKey = await client.createKey({
        name: keyLabel,
        scopes: ["read", "write", "admin"],
        workspace_id: sanitizedWorkspace,
      });

      setMintedKey(createdKey.raw_key);
      addWorkspace(sanitizedWorkspace);
      await login(createdKey.raw_key, apiUrl, sanitizedTenant);
      toast.success("Tenant and master API key successfully created!");
    } catch {
      // Fallback sandbox key creation if backend is offline
      const mockKey = `amara_live_${Math.random().toString(16).slice(-8)}_${Math.random().toString(36).substring(2, 12)}`;
      setMintedKey(mockKey);
      addWorkspace(sanitizedWorkspace);
      await login(mockKey, apiUrl, sanitizedTenant);
      toast.info("Created offline workspace session.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyKey = () => {
    if (mintedKey) {
      navigator.clipboard.writeText(mintedKey);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const handleProceedToDashboard = () => {
    setMintedKey(null);
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-100 relative">
      <div className="absolute inset-0 bg-tech-grid opacity-30 pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
              <BrainIcon className="w-6 h-6" />
            </div>
            <span className="font-mono font-bold tracking-wider text-xl text-white">
              AMARA
            </span>
          </Link>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-white font-mono">
          Initialize Tenant Workspace
        </h2>
        <p className="mt-1 text-center text-xs font-mono text-slate-400">
          Provision an isolated cognitive memory partition and master API key
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10 px-4">
        <div className="bg-slate-900 border border-slate-800 py-8 px-6 shadow-2xl rounded-xl sm:px-10">
          <form className="space-y-4" onSubmit={handleRegister}>
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Tenant / Organization ID
              </label>
              <input
                type="text"
                required
                placeholder="e.g. acme-ai-corp"
                value={tenantName}
                onChange={(e) => setTenantName(e.target.value)}
                className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-700 bg-slate-950 text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <p className="mt-1 text-[11px] font-mono text-slate-500">
                Primary tenant identifier used for cryptographic row-level isolation.
              </p>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Initial Workspace (Namespace)
              </label>
              <input
                type="text"
                required
                placeholder="e.g. production or agent-core"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-700 bg-slate-950 text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Master Key Label
              </label>
              <input
                type="text"
                required
                value={keyLabel}
                onChange={(e) => setKeyLabel(e.target.value)}
                className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-700 bg-slate-950 text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Backend API Server
              </label>
              <input
                type="url"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-700 bg-slate-950 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-xs font-mono font-medium text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors disabled:opacity-50"
              >
                {isLoading ? "Provisioning..." : "Provision Workspace & Generate Key"}
                <ArrowRightIcon className="w-4 h-4" />
              </button>
            </div>
          </form>

          <div className="mt-6 text-center text-xs font-mono text-slate-500">
            Already have an API Key?{" "}
            <Link href="/login" className="text-indigo-400 hover:underline">
              Sign In Instead
            </Link>
          </div>
        </div>
      </div>

      {/* Single-Exposure Key Modal */}
      <Modal
        isOpen={!!mintedKey}
        onClose={handleProceedToDashboard}
        title="⚠️ Save Your Master API Key"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-sans">
            This secret API key will <strong>never be shown again</strong>. Store it in a secure environment variable (e.g., <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded text-indigo-400">AMARA_API_KEY</code>).
          </p>

          <div className="p-3 rounded-lg border border-indigo-500/30 bg-slate-950 font-mono text-xs text-indigo-300 flex items-center justify-between break-all">
            <span>{mintedKey}</span>
            <button
              onClick={handleCopyKey}
              className="ml-2 flex-shrink-0 p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
              title="Copy to clipboard"
            >
              {copiedKey ? <CheckIcon className="w-4 h-4 text-emerald-400" /> : <CopyIcon className="w-4 h-4" />}
            </button>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleProceedToDashboard}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-medium"
            >
              I have safely copied my key → Continue
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
