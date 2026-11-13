import React from "react";
import { LifecycleStatus, MemoryCategory } from "../lib/types";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "outline" | "success" | "warning" | "danger" | "info" | "purple";
  className?: string;
}

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  const variantStyles = {
    default: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700",
    outline: "border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 bg-transparent",
    success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    danger: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
    info: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20",
    purple: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium border ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

export function MemoryCategoryBadge({ category }: { category: MemoryCategory }) {
  switch (category) {
    case "working":
      return <Badge variant="warning">working</Badge>;
    case "episodic":
      return <Badge variant="info">episodic</Badge>;
    case "semantic":
      return <Badge variant="purple">semantic</Badge>;
    case "procedural":
      return <Badge variant="success">procedural</Badge>;
    case "associative":
      return <Badge variant="default">associative</Badge>;
    default:
      return <Badge variant="outline">{category}</Badge>;
  }
}

export function LifecycleStatusBadge({ status }: { status: LifecycleStatus }) {
  switch (status) {
    case "active":
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          active
        </span>
      );
    case "decaying":
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          decaying
        </span>
      );
    case "consolidated":
      return <Badge variant="purple">consolidated</Badge>;
    case "superseded":
      return <Badge variant="outline">superseded</Badge>;
    case "archived":
      return <Badge variant="default">archived</Badge>;
    case "tombstoned":
      return <Badge variant="danger">tombstoned</Badge>;
    case "expired":
      return <Badge variant="danger">expired</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export function RelationBadge({ relation }: { relation: string }) {
  switch (relation) {
    case "contradicts":
      return <Badge variant="danger">CONTRADICTS</Badge>;
    case "derived_from":
      return <Badge variant="purple">DERIVED_FROM</Badge>;
    case "depends_on":
      return <Badge variant="warning">DEPENDS_ON</Badge>;
    case "causal":
      return <Badge variant="info">CAUSAL</Badge>;
    case "associated_with":
      return <Badge variant="default">ASSOCIATED_WITH</Badge>;
    default:
      return <Badge variant="outline">{relation.toUpperCase()}</Badge>;
  }
}

