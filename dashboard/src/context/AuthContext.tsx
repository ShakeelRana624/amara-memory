"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { AmaraApiClient } from "../lib/api";
import { HealthResponse } from "../lib/types";

interface AuthContextType {
  apiKey: string | null;
  apiUrl: string;
  tenantId: string;
  workspace: string;
  workspaces: string[];
  theme: "dark" | "light";
  isSandbox: boolean;
  isBackendConnected: boolean;
  health: HealthResponse | null;
  client: AmaraApiClient;
  login: (key: string, url?: string, tenant?: string) => Promise<void>;
  logout: () => void;
  setWorkspace: (ws: string) => void;
  addWorkspace: (ws: string) => void;
  toggleTheme: () => void;
  toggleSandbox: () => void;
  refreshHealth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [apiUrl, setApiUrl] = useState<string>("http://localhost:8000");
  const [tenantId, setTenantId] = useState<string>("tenant-default");
  const [workspace, setWorkspaceState] = useState<string>("default");
  const [workspaces, setWorkspaces] = useState<string[]>([
    "default",
    "agent-reasoning",
    "production-mesh",
    "staging-eval",
  ]);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [isSandbox, setIsSandbox] = useState<boolean>(false);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isInitialized, setIsInitialized] = useState<boolean>(false);

  // Initialize from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;

    const savedKey = localStorage.getItem("amara_api_key");
    const savedUrl = localStorage.getItem("amara_api_url") || "http://localhost:8000";
    const savedTenant = localStorage.getItem("amara_tenant_id") || "tenant-default";
    const savedWorkspace = localStorage.getItem("amara_workspace") || "default";
    const savedWorkspaces = localStorage.getItem("amara_workspaces");
    const savedTheme = (localStorage.getItem("amara_theme") as "dark" | "light") || "dark";
    const savedSandbox = localStorage.getItem("amara_sandbox") === "true";

    if (savedKey) setApiKey(savedKey);
    setApiUrl(savedUrl);
    setTenantId(savedTenant);
    setWorkspaceState(savedWorkspace);
    if (savedWorkspaces) {
      try {
        setWorkspaces(JSON.parse(savedWorkspaces));
      } catch {
        // use default
      }
    }
    setTheme(savedTheme);
    setIsSandbox(savedSandbox);
    setIsInitialized(true);

    // Apply dark class to document
    if (savedTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, []);

  // Sync theme changes to document
  useEffect(() => {
    if (typeof window === "undefined" || !isInitialized) return;
    localStorage.setItem("amara_theme", theme);
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme, isInitialized]);

  const client = useMemo(() => {
    return new AmaraApiClient({
      baseUrl: apiUrl,
      apiKey,
      isSandbox,
    });
  }, [apiUrl, apiKey, isSandbox]);

  const checkConnectivity = async () => {
    try {
      const res = await fetch(`${apiUrl.replace(/\/$/, "")}/api/v1/health`, {
        cache: "no-store",
      });
      if (res.ok) {
        const json = await res.json();
        setHealth(json);
        setIsBackendConnected(true);
      } else {
        setIsBackendConnected(false);
      }
    } catch {
      setIsBackendConnected(false);
    }
  };

  useEffect(() => {
    if (isInitialized) {
      checkConnectivity();
    }
  }, [apiUrl, isInitialized]);

  const login = async (key: string, url = "http://localhost:8000", tenant = "tenant-default") => {
    setApiKey(key);
    setApiUrl(url);
    setTenantId(tenant);
    setIsSandbox(false);
    if (typeof window !== "undefined") {
      localStorage.setItem("amara_api_key", key);
      localStorage.setItem("amara_api_url", url);
      localStorage.setItem("amara_tenant_id", tenant);
      localStorage.setItem("amara_sandbox", "false");
    }
    await checkConnectivity();
  };

  const logout = () => {
    setApiKey(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("amara_api_key");
    }
  };

  const setWorkspace = (ws: string) => {
    setWorkspaceState(ws);
    if (typeof window !== "undefined") {
      localStorage.setItem("amara_workspace", ws);
    }
  };

  const addWorkspace = (ws: string) => {
    if (!workspaces.includes(ws)) {
      const updated = [...workspaces, ws];
      setWorkspaces(updated);
      if (typeof window !== "undefined") {
        localStorage.setItem("amara_workspaces", JSON.stringify(updated));
      }
    }
    setWorkspace(ws);
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const toggleSandbox = () => {
    setIsSandbox((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        localStorage.setItem("amara_sandbox", String(next));
      }
      return next;
    });
  };

  const refreshHealth = async () => {
    await checkConnectivity();
  };

  return (
    <AuthContext.Provider
      value={{
        apiKey,
        apiUrl,
        tenantId,
        workspace,
        workspaces,
        theme,
        isSandbox,
        isBackendConnected,
        health,
        client,
        login,
        logout,
        setWorkspace,
        addWorkspace,
        toggleTheme,
        toggleSandbox,
        refreshHealth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

