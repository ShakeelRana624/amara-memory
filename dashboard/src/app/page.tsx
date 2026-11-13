"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  BrainIcon,
  DatabaseIcon,
  SearchIcon,
  ShieldIcon,
  LayersIcon,
  ActivityIcon,
  ArrowRightIcon,
  CheckIcon,
  CopyIcon,
  TerminalIcon,
} from "../components/icons";

export default function LandingPage() {
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  const installCmd = "pip install amara-ai";
  const pythonSnippet = `from amara import MemoryEngine, MemoryConfig

# Initialize cognitive memory engine
engine = MemoryEngine(MemoryConfig(storage_backend="postgres"))
await engine.initialize()

# Ingest an epistemic observation
await engine.remember(
    content="User prefers PostgreSQL 16 with PgBouncer pooling.",
    author_id="agent_assistant",
    namespace="production"
)

# Hybrid recall with context reconstruction
context = await engine.reconstruct(
    query="What database connection config was chosen?",
    budget=1024
)
print(context.formatted_context)`;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white">
      {/* Background technical grid */}
      <div className="absolute inset-0 bg-tech-grid opacity-30 pointer-events-none" />

      {/* Navigation header */}
      <header className="relative border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
              <BrainIcon className="w-5 h-5" />
            </div>
            <span className="font-mono font-bold tracking-wider text-base text-white">
              AMARA
            </span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              v0.1
            </span>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-xs font-mono text-slate-400">
            <a href="#architecture" className="hover:text-indigo-400 transition-colors">
              Architecture
            </a>
            <a href="#comparison" className="hover:text-indigo-400 transition-colors">
              Why Not RAG?
            </a>
            <a href="#sdk" className="hover:text-indigo-400 transition-colors">
              Python SDK
            </a>
            <Link href="/dashboard/docs" className="hover:text-indigo-400 transition-colors">
              API Reference
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-xs font-mono px-3 py-1.5 rounded-md border border-slate-700 text-slate-300 hover:bg-slate-900 transition-colors"
            >
              Log In
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 text-xs font-mono px-3.5 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors shadow-lg shadow-indigo-600/20"
            >
              Open Console
              <ArrowRightIcon className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero section */}
      <section className="relative pt-20 pb-24 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono mb-8 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            Adaptive Memory Architecture for Reasoning & AI
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-tight sm:leading-none">
            Cognitive Memory for Autonomous AI Agents.
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Move beyond static vector lookup. AMARA gives reasoning models an epistemic state machine with episodic consolidation, temporal validity, contradiction tracking, and verifiable citations.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-mono font-medium transition-all shadow-xl shadow-indigo-600/25 hover:translate-y-[-1px]"
            >
              Launch Dashboard Console
              <ArrowRightIcon className="w-4 h-4" />
            </Link>

            <Link
              href="/dashboard/retrieval"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-lg border border-slate-700 hover:border-slate-600 bg-slate-900/60 hover:bg-slate-900 text-slate-300 text-sm font-mono transition-all"
            >
              <SearchIcon className="w-4 h-4 text-cyan-400" />
              Test Retrieval Playground
            </Link>
          </div>

          {/* Quick install pill */}
          <div className="mt-8 flex items-center justify-center">
            <div className="inline-flex items-center gap-3 px-4 py-2 rounded-lg bg-slate-900/90 border border-slate-800 font-mono text-xs text-slate-300">
              <span className="text-slate-500">$</span>
              <span>{installCmd}</span>
              <button
                onClick={() => handleCopy(installCmd)}
                className="text-slate-400 hover:text-white transition-colors"
                title="Copy install command"
              >
                {copiedSnippet ? (
                  <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <CopyIcon className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture Highlights Grid */}
      <section id="architecture" className="py-20 border-t border-slate-800/80 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-mono uppercase tracking-widest text-indigo-400 mb-2">
              Cognitive Subsystems
            </h2>
            <h3 className="text-3xl font-bold text-white tracking-tight">
              An Architectural Leap Past Naive Vector Stores
            </h3>
            <p className="mt-4 text-sm text-slate-400 leading-relaxed">
              Standard vector databases store frozen text chunks. AMARA implements living memory systems inspired by human cognitive science.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500/40 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4">
                <BrainIcon className="w-5 h-5" />
              </div>
              <h4 className="text-base font-semibold text-white font-mono mb-2">
                5-Tier Epistemic Hierarchy
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Separates fast Working memory, chronological Episodic events, generalized Semantic concepts, executable Procedural workflows, and associative Graph linkages.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500/40 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mb-4">
                <SearchIcon className="w-5 h-5" />
              </div>
              <h4 className="text-base font-semibold text-white font-mono mb-2">
                Multi-Channel Hybrid Retrieval
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Simultaneously fuses HNSW cosine similarity, BM25 lexical precision, exponential temporal decay, and graph hop traversal with Reciprocal Rank Fusion (RRF).
              </p>
            </div>

            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500/40 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4">
                <ActivityIcon className="w-5 h-5" />
              </div>
              <h4 className="text-base font-semibold text-white font-mono mb-2">
                Continuous Consolidation
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                As episodic memories accumulate, AMARA automatically detects near-duplicate patterns, merges complementary observations, and updates semantic abstractions without hallucinated conflation.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500/40 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mb-4">
                <ShieldIcon className="w-5 h-5" />
              </div>
              <h4 className="text-base font-semibold text-white font-mono mb-2">
                Contradiction Resolution
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Tracks temporal precedence and source reliability. When new facts contradict previous assumptions, AMARA supersedes outdated records while preserving the audit lineage.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500/40 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mb-4">
                <LayersIcon className="w-5 h-5" />
              </div>
              <h4 className="text-base font-semibold text-white font-mono mb-2">
                Token-Bounded Reconstruction
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Knapsack-packs top relevant propositions into an LLM context budget with verifiable citation brackets ([REF-1], [REF-2]), eliminating token bloat and hallucinated references.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500/40 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mb-4">
                <DatabaseIcon className="w-5 h-5" />
              </div>
              <h4 className="text-base font-semibold text-white font-mono mb-2">
                PostgreSQL + pgvector Engine
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Built on battle-tested SQL foundations with strict tenant isolation, ACID guarantees, Alembic migrations, connection pooling, and sub-millisecond index queries.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Comparison Table vs Basic RAG */}
      <section id="comparison" className="py-20 border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-mono uppercase tracking-widest text-indigo-400 mb-2">
              Architectural Comparison
            </h2>
            <h3 className="text-3xl font-bold text-white tracking-tight">
              AMARA vs Traditional Vector RAG
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse border border-slate-800 rounded-lg">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Cognitive Capability</th>
                  <th className="py-3 px-4 text-indigo-400">AMARA Cognitive Memory</th>
                  <th className="py-3 px-4 text-slate-500">Standard Vector RAG</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-200">Epistemic State Machine</td>
                  <td className="py-3 px-4 text-emerald-400">Active, Decaying, Consolidated, Superseded</td>
                  <td className="py-3 px-4 text-rose-400">Static documents only</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-200">Temporal Validity Ranges</td>
                  <td className="py-3 px-4 text-emerald-400">valid_from / valid_to interval validation</td>
                  <td className="py-3 px-4 text-rose-400">None (obsolete data returned equally)</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-200">Contradiction Handling</td>
                  <td className="py-3 px-4 text-emerald-400">Automated conflict detection & audit trail</td>
                  <td className="py-3 px-4 text-rose-400">Returns contradictory facts simultaneously</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-200">Retrieval Strategies</td>
                  <td className="py-3 px-4 text-emerald-400">Hybrid (Dense + Lexical + Temporal + Graph)</td>
                  <td className="py-3 px-4 text-rose-400">Cosine similarity only</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-200">Context Reconstruction</td>
                  <td className="py-3 px-4 text-emerald-400">Token-bounded knapsack with verifiable citations</td>
                  <td className="py-3 px-4 text-rose-400">Raw chunk concatenation</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-200">Tenant & Namespace Isolation</td>
                  <td className="py-3 px-4 text-emerald-400">Enforced at SQL engine & API key boundary</td>
                  <td className="py-3 px-4 text-rose-400">Manual metadata filtering prone to leakage</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Code Sample SDK Section */}
      <section id="sdk" className="py-20 border-t border-slate-800/80 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono mb-4">
                <TerminalIcon className="w-3.5 h-3.5" />
                Developer-First SDK
              </div>
              <h3 className="text-3xl font-bold text-white tracking-tight">
                Integrate with Any LLM or Agent Loop in Seconds.
              </h3>
              <p className="mt-4 text-sm text-slate-400 leading-relaxed">
                Whether you use LangChain, LlamaIndex, AutoGen, CrewAI, or raw OpenAI / Anthropic / Gemini SDKs, AMARA acts as your sovereign memory engine.
              </p>

              <ul className="mt-6 space-y-3 text-xs font-mono text-slate-300">
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span> Fully typed with Pydantic v2 schemas
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span> Async-first architecture with safe synchronous wrappers
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span> Zero required external cloud dependencies to run locally
                </li>
              </ul>

              <div className="mt-8 flex gap-4">
                <Link
                  href="/dashboard/docs"
                  className="px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-medium transition-colors"
                >
                  View SDK Documentation
                </Link>
                <Link
                  href="/dashboard/memories"
                  className="px-4 py-2 rounded-md border border-slate-700 hover:bg-slate-800 text-slate-300 font-mono text-xs transition-colors"
                >
                  Browse Memory Explorer
                </Link>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-slate-300 shadow-2xl relative overflow-hidden">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800 text-slate-500 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                  <span className="ml-2 text-slate-400">example_agent.py</span>
                </div>
                <button
                  onClick={() => handleCopy(pythonSnippet)}
                  className="hover:text-slate-300 flex items-center gap-1"
                >
                  {copiedSnippet ? <CheckIcon className="w-3.5 h-3.5 text-emerald-400" /> : <CopyIcon className="w-3.5 h-3.5" />}
                  <span>{copiedSnippet ? "Copied" : "Copy"}</span>
                </button>
              </div>
              <pre className="overflow-x-auto text-indigo-300 leading-relaxed">
                <code>{pythonSnippet}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-8 text-center text-xs font-mono text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            AMARA — Adaptive Memory Architecture for Reasoning & AI © 2026. Open Source (MIT).
          </div>
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="hover:text-slate-300 transition-colors">
              Console
            </Link>
            <Link href="/dashboard/docs" className="hover:text-slate-300 transition-colors">
              Documentation
            </Link>
            <Link href="/dashboard/retrieval" className="hover:text-slate-300 transition-colors">
              Playground
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
