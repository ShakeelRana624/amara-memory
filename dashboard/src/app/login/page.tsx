"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { BrainIcon, ArrowRightIcon, ShieldIcon } from "../../components/icons";
import { useToast } from "../../components/Toast";

export default function LoginPage() {
  const router = useRouter();
  const { login, toggleSandbox } = useAuth();
  const toast = useToast();

  const [apiKey, setApiKey] = useState("");
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
  const [tenantId, setTenantId] = useState("tenant-default");
  const [isLoading, setIsLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      toast.error("Please provide an AMARA API key or enter Sandbox Mode.");
      return;
    }
    setIsLoading(true);
    try {
      await login(apiKey.trim(), apiUrl.trim(), tenantId.trim());
      toast.success("Connected to AMARA cognitive backend.");
      router.push("/dashboard");
    } catch {
      toast.error("Could not reach backend. Verify URL or explore in Sandbox Mode.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSandboxEnter = () => {
    login("sandbox_demo_key", "http://localhost:8000", "tenant-sandbox");
    toggleSandbox();
    toast.info("Entered Sample Sandbox Mode with preloaded cognitive data.");
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
          Developer Sign In
        </h2>
        <p className="mt-1 text-center text-xs font-mono text-slate-400">
          Connect your API credentials to access the cognitive memory engine
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10 px-4">
        <div className="bg-slate-900 border border-slate-800 py-8 px-6 shadow-2xl rounded-xl sm:px-10">
          <form className="space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                AMARA API Key
              </label>
              <div className="relative">
                <input
                  type="password"
                  required
                  placeholder="amara_live_... or master token"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-700 bg-slate-950 text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <p className="mt-1 text-[11px] font-mono text-slate-500">
                Bearer secret token minted by AMARA Server or SDK.
              </p>
            </div>

            <div>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-[11px] font-mono text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                <span>{showAdvanced ? "▼ Hide" : "▶ Show"} Advanced Endpoint & Tenant</span>
              </button>
            </div>

            {showAdvanced && (
              <div className="space-y-4 pt-2 border-t border-slate-800">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">
                    API Base URL
                  </label>
                  <input
                    type="url"
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-700 bg-slate-950 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">
                    Tenant Scope ID
                  </label>
                  <input
                    type="text"
                    value={tenantId}
                    onChange={(e) => setTenantId(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-700 bg-slate-950 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-xs font-mono font-medium text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors disabled:opacity-50"
              >
                {isLoading ? "Authenticating..." : "Connect to Backend"}
                <ArrowRightIcon className="w-4 h-4" />
              </button>
            </div>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-800" />
              </div>
              <div className="relative flex justify-center text-xs font-mono">
                <span className="bg-slate-900 px-2 text-slate-500">Or explore without backend</span>
              </div>
            </div>

            <div className="mt-4">
              <button
                onClick={handleSandboxEnter}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 text-xs font-mono font-medium transition-colors"
              >
                <ShieldIcon className="w-4 h-4" />
                Launch Sample Sandbox Mode
              </button>
            </div>
          </div>

          <div className="mt-6 text-center text-xs font-mono text-slate-500">
            Need a new tenant workspace?{" "}
            <Link href="/register" className="text-indigo-400 hover:underline">
              Register Workspace
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
