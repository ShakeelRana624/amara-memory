"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import {
  ActivityIcon,
  BookOpenIcon,
  BrainIcon,
  FolderIcon,
  KeyIcon,
  LayersIcon,
  NetworkIcon,
  SearchIcon,
  SettingsIcon,
} from "./icons";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const navItems: NavItem[] = [
  { name: "Overview", href: "/dashboard", icon: ActivityIcon },
  { name: "Workspaces", href: "/dashboard/workspaces", icon: FolderIcon },
  { name: "Memory Explorer", href: "/dashboard/memories", icon: BrainIcon },
  { name: "Relationships", href: "/dashboard/relationships", icon: NetworkIcon },
  { name: "Retrieval Playground", href: "/dashboard/retrieval", icon: SearchIcon },
  { name: "API Keys", href: "/dashboard/keys", icon: KeyIcon },
  { name: "Usage & Metrics", href: "/dashboard/usage", icon: LayersIcon },
  { name: "Settings", href: "/dashboard/settings", icon: SettingsIcon },
  { name: "Documentation", href: "/dashboard/docs", icon: BookOpenIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  const { health, isSandbox } = useAuth();

  return (
    <aside className="w-64 flex-shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm flex flex-col justify-between hidden md:flex">
      <div className="py-4 px-3 space-y-1">
        <div className="px-3 pb-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 dark:text-slate-500">
          Platform Navigation
        </div>
        <nav className="space-y-1" aria-label="Sidebar Navigation">
          {navItems.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname?.startsWith(item.href);

            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-mono transition-all duration-150 ${
                  isActive
                    ? "bg-indigo-600/10 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-400 font-semibold border-l-2 border-indigo-600 dark:border-indigo-400 pl-2.5"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60"
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                    isActive
                      ? "text-indigo-600 dark:text-indigo-400"
                      : "text-slate-400 dark:text-slate-500"
                  }`}
                />
                <span className="flex-1">{item.name}</span>
                {item.badge && (
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-500 border border-indigo-500/20 font-mono">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Engine Status Widget */}
      <div className="p-3 m-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-[11px] font-mono space-y-1.5">
        <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
          <span>Engine Status</span>
          <span className="flex items-center gap-1 text-emerald-500 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {health?.status || (isSandbox ? "sandbox" : "online")}
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
          <span>Storage</span>
          <span className="text-slate-700 dark:text-slate-300 font-mono">
            {health?.storage_backend || "postgresql"}
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
          <span>Version</span>
          <span className="text-slate-700 dark:text-slate-300 font-mono">
            v{health?.version || "0.1.0"}
          </span>
        </div>
      </div>
    </aside>
  );
}
