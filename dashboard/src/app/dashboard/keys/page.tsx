"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  PlusIcon,
  RefreshIcon,
  ShieldIcon,
  CopyIcon,
  CheckIcon,
} from "../../../components/icons";
import { Modal } from "../../../components/Modal";
import { useToast } from "../../../components/Toast";
import { APIKeyCreatedResponse, APIKeyInfoResponse } from "../../../lib/types";

export default function ApiKeysPage() {
  const { client, tenantId, workspace } = useAuth();
  const toast = useToast();

  const [keys, setKeys] = useState<APIKeyInfoResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Create Key Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [scopes, setScopes] = useState<string[]>(["read", "write"]);
  const [expiresInDays, setExpiresInDays] = useState<number | "">("");

  // Revealed Key Modal (single exposure)
  const [revealedKey, setRevealedKey] = useState<APIKeyCreatedResponse | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Revoke Modal
  const [revokingKeyId, setRevokingKeyId] = useState<string | null>(null);

  const fetchKeys = async () => {
    setIsLoading(true);
    try {
      const data = await client.listKeys();
      setKeys(data);
    } catch {
      toast.error("Failed to fetch API keys");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, [client]);

  const handleToggleScope = (scope: string) => {
    if (scopes.includes(scope)) {
      setScopes(scopes.filter((s) => s !== scope));
    } else {
      setScopes([...scopes, scope]);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;

    try {
      const res = await client.createKey({
        name: keyName.trim(),
        scopes: scopes.length ? scopes : ["read"],
        workspace_id: workspace,
        expires_in_days: expiresInDays ? Number(expiresInDays) : undefined,
      });

      setRevealedKey(res);
      setIsCreateOpen(false);
      setKeyName("");
      setScopes(["read", "write"]);
      setExpiresInDays("");
      await fetchKeys();
      toast.success("New API key generated");
    } catch {
      toast.error("Failed to generate API key");
    }
  };

  const handleRotateKey = async (keyId: string) => {
    try {
      const res = await client.rotateKey(keyId);
      setRevealedKey(res);
      await fetchKeys();
      toast.success("API key secret rotated");
    } catch {
      toast.error("Failed to rotate key");
    }
  };

  const handleRevokeKey = async () => {
    if (!revokingKeyId) return;
    try {
      await client.revokeKey(revokingKeyId);
      toast.success("API key revoked");
      setRevokingKeyId(null);
      await fetchKeys();
    } catch {
      toast.error("Failed to revoke key");
    }
  };

  const handleCopyRawKey = () => {
    if (revealedKey) {
      navigator.clipboard.writeText(revealedKey.raw_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            API Key Management
          </h1>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
            Provision, rotate, and revoke scoped credentials for tenant: <strong className="text-indigo-500">{tenantId}</strong>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchKeys}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
            title="Refresh keys"
          >
            <RefreshIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-medium transition-colors shadow-md shadow-indigo-600/20"
          >
            <PlusIcon className="w-3.5 h-3.5" />
            Generate New Key
          </button>
        </div>
      </div>

      {/* Security Architecture Callout */}
      <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 text-xs font-mono text-slate-700 dark:text-slate-300 space-y-1">
        <div className="flex items-center gap-2 text-indigo-500 font-semibold">
          <ShieldIcon className="w-4 h-4" />
          Cryptographic Secret Protection
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed font-sans">
          AMARA hashes all raw keys with SHA-256 before persistence. Raw keys are never stored in plain text and cannot be retrieved after initial generation. Authenticate using <code className="text-indigo-400">Authorization: Bearer &lt;key&gt;</code> or <code className="text-indigo-400">X-API-Key: &lt;key&gt;</code>.
        </p>
      </div>

      {/* Keys Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-xs font-mono text-slate-400">
            Fetching tenant credentials...
          </div>
        ) : keys.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-slate-500">
            No API keys issued yet. Generate one above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-slate-500 dark:text-slate-400">
                  <th className="py-3 px-4">Key Label</th>
                  <th className="py-3 px-4">Prefix</th>
                  <th className="py-3 px-4">Scopes</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4">Last Used</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {keys.map((k) => (
                  <tr
                    key={k.key_id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">
                      {k.name}
                    </td>

                    <td className="py-3 px-4 text-slate-500 dark:text-slate-400 font-mono">
                      <code>{k.key_prefix}...</code>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {k.scopes.map((s) => (
                          <span
                            key={s}
                            className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      {k.is_active ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono bg-rose-500/10 text-rose-500 border border-rose-500/20">
                          Revoked
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>

                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
                    </td>

                    <td className="py-3 px-4 text-right">
                      {k.is_active && (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleRotateKey(k.key_id)}
                            className="text-[11px] font-mono text-indigo-500 hover:underline"
                          >
                            Rotate
                          </button>
                          <button
                            onClick={() => setRevokingKeyId(k.key_id)}
                            className="text-[11px] font-mono text-rose-500 hover:underline"
                          >
                            Revoke
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Generate Key Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Generate New API Key"
      >
        <form onSubmit={handleCreateKey} className="space-y-4 text-xs font-mono">
          <div>
            <label className="block text-slate-700 dark:text-slate-300 mb-1">
              Key Name / Label
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Production Ingestion Worker"
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              className="w-full px-3 py-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-700 dark:text-slate-300 mb-2">
              Permission Scopes
            </label>
            <div className="space-y-2">
              {[
                { scope: "read", desc: "Allows recall, memory inspection, search, and metrics" },
                { scope: "write", desc: "Allows remembering propositions, updates, and consolidation" },
                { scope: "admin", desc: "Allows issuing, rotating, and revoking API keys" },
              ].map(({ scope, desc }) => (
                <label key={scope} className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={scopes.includes(scope)}
                    onChange={() => handleToggleScope(scope)}
                    className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="font-bold text-slate-800 dark:text-slate-200 uppercase">
                      {scope}
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 block">
                      {desc}
                    </span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-slate-700 dark:text-slate-300 mb-1">
              Expiration in Days (Optional)
            </label>
            <input
              type="number"
              min="1"
              max="365"
              placeholder="Leave empty for non-expiring key"
              value={expiresInDays}
              onChange={(e) => setExpiresInDays(e.target.value ? parseInt(e.target.value) : "")}
              className="w-full px-3 py-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
            >
              Generate Key
            </button>
          </div>
        </form>
      </Modal>

      {/* Revealed Secret Key Modal */}
      <Modal
        isOpen={!!revealedKey}
        onClose={() => setRevealedKey(null)}
        title="⚠️ Copy Your New API Key Secret"
      >
        <div className="space-y-4 text-xs font-mono">
          <p className="text-slate-600 dark:text-slate-300 font-sans">
            Please copy this API key immediately. <strong>It will never be displayed again.</strong>
          </p>

          <div className="p-3 rounded-lg border border-indigo-500/30 bg-slate-950 text-indigo-300 flex items-center justify-between break-all">
            <span>{revealedKey?.raw_key}</span>
            <button
              onClick={handleCopyRawKey}
              className="ml-2 flex-shrink-0 p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
              title="Copy Key"
            >
              {copiedKey ? <CheckIcon className="w-4 h-4 text-emerald-400" /> : <CopyIcon className="w-4 h-4" />}
            </button>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setRevealedKey(null)}
              className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
            >
              I have saved the key
            </button>
          </div>
        </div>
      </Modal>

      {/* Revoke Confirmation Modal */}
      <Modal
        isOpen={!!revokingKeyId}
        onClose={() => setRevokingKeyId(null)}
        title="Revoke API Key"
      >
        <div className="space-y-4 text-xs font-mono">
          <p className="text-slate-600 dark:text-slate-300 font-sans">
            Are you sure you want to revoke this API key? Applications using this credential will immediately be rejected with 401 Unauthorized.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setRevokingKeyId(null)}
              className="px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              onClick={handleRevokeKey}
              className="px-4 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium"
            >
              Confirm Revocation
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
