"use client";

import React, { useState } from "react";
import {
  BookOpenIcon,
  TerminalIcon,
  CopyIcon,
  CheckIcon,
  BrainIcon,
  PlugIcon,
  CpuIcon,
  SparklesIcon,
} from "../../../components/icons";
import { useToast } from "../../../components/Toast";

export default function DocsPage() {
  const toast = useToast();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    toast.success("Snippet copied to clipboard");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const curlRemember = `curl -X POST "http://localhost:8000/api/v1/memories" \\
  -H "Authorization: Bearer amara_live_YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "User selected PostgreSQL 16 with PgBouncer pooling.",
    "author_id": "agent_primary",
    "memory_type": "episodic",
    "confidence": 0.98,
    "importance": 0.85,
    "namespace": "production"
  }'`;

  const curlSearch = `curl -X POST "http://localhost:8000/api/v1/memories/search" \\
  -H "Authorization: Bearer amara_live_YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "database connection pooling recommendations",
    "strategy": "hybrid",
    "top_k": 5,
    "namespace": "production"
  }'`;

  const curlReconstruct = `curl -X POST "http://localhost:8000/api/v1/context/reconstruct" \\
  -H "Authorization: Bearer amara_live_YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "What database setup did we select?",
    "budget_tokens": 1024,
    "strategy": "hybrid",
    "namespace": "production"
  }'`;

  const pythonQuickstart = `import asyncio
from amara import MemoryEngine, MemoryConfig
from amara.enums import MemoryCategory
from amara.retrieval.types import RetrievalStrategy

async def main():
    # 1. Initialize engine
    config = MemoryConfig(storage_backend="postgres")
    engine = MemoryEngine(config)
    await engine.initialize()

    # 2. Ingest observation
    item = await engine.remember(
        content="Primary database upgraded to PostgreSQL 16 with pgvector extension.",
        author_id="devops_lead",
        memory_type=MemoryCategory.SEMANTIC,
        confidence=0.99,
        importance=0.90,
        namespace="agent-infra"
    )
    print(f"Ingested memory ID: {item.id}")

    # 3. Hybrid search
    results = await engine.recall(
        query="What postgresql version is running?",
        strategy=RetrievalStrategy.HYBRID,
        top_k=3,
        namespace="agent-infra"
    )
    for r in results.results:
        print(f"Score: {r.relevance_score:.2f} | {r.item.content}")

    # 4. Context prompt reconstruction
    context = await engine.reconstruct(
        query="Synthesize summary of database setup",
        budget=1024,
        namespace="agent-infra"
    )
    print("\\nReconstructed Prompt Context:\\n", context.formatted_context)

if __name__ == "__main__":
    asyncio.run(main())`;

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
          Developer Documentation & API Reference
        </h1>
        <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
          Complete guide to the AMARA Python SDK, REST endpoints, and cognitive memory lifecycle
        </p>
      </div>

      {/* Python SDK Quickstart */}
      <section className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TerminalIcon className="w-5 h-5 text-indigo-500" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-slate-900 dark:text-slate-100">
              Python SDK Quickstart
            </h2>
          </div>
          <button
            onClick={() => handleCopy(pythonQuickstart, "py-quickstart")}
            className="flex items-center gap-1.5 text-xs font-mono text-indigo-500 hover:text-indigo-400"
          >
            {copiedKey === "py-quickstart" ? (
              <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <CopyIcon className="w-3.5 h-3.5" />
            )}
            <span>{copiedKey === "py-quickstart" ? "Copied" : "Copy Code"}</span>
          </button>
        </div>

        <p className="text-xs text-slate-600 dark:text-slate-400 font-sans leading-relaxed">
          Install the package with <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-indigo-400">pip install amara-ai</code> and initialize the <code className="font-mono text-indigo-400">MemoryEngine</code>.
        </p>

        <pre className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-950 text-indigo-300 font-mono text-xs overflow-x-auto leading-relaxed">
          <code>{pythonQuickstart}</code>
        </pre>
      </section>

      {/* AI Framework Integrations Overview */}
      <section className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PlugIcon className="w-5 h-5 text-indigo-500" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-slate-900 dark:text-slate-100">
              AI Framework Integrations (LangGraph & Hugging Face)
            </h2>
          </div>
          <a
            href="/dashboard/integrations"
            className="text-xs font-mono text-indigo-500 hover:text-indigo-400 font-semibold"
          >
            Explore Integrations Hub &rarr;
          </a>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 font-sans leading-relaxed">
          AMARA provides decoupled adapters for <strong>LangGraph</strong> (pre-decision retrieval and post-decision reflection), <strong>Hugging Face Transformers</strong> (pre-generation prompt augmentation without GPU interference), and <strong>FastAPI microservices</strong>.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          <div className="p-4 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-2">
            <h3 className="text-xs font-bold font-mono text-indigo-400 flex items-center gap-1.5">
              <CpuIcon className="w-4 h-4 text-indigo-500" />
              LangGraph Reusable Node
            </h3>
            <pre className="p-2.5 rounded bg-slate-950 text-[11px] font-mono text-indigo-300 overflow-x-auto">
              <code>{`from amara.integrations.langgraph import AmaraMemoryNode, AmaraLangGraphAdapter

adapter = AmaraLangGraphAdapter(engine=engine)
# Injects memory into state before LLM
recall_node = AmaraMemoryNode(adapter=adapter, mode="retrieve")
# Extracts facts from state after LLM
reflect_node = AmaraMemoryNode(adapter=adapter, mode="reflect")`}</code>
            </pre>
          </div>

          <div className="p-4 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-2">
            <h3 className="text-xs font-bold font-mono text-emerald-400 flex items-center gap-1.5">
              <SparklesIcon className="w-4 h-4 text-emerald-500" />
              Hugging Face Prompt Augmenter
            </h3>
            <pre className="p-2.5 rounded bg-slate-950 text-[11px] font-mono text-emerald-300 overflow-x-auto">
              <code>{`from amara.integrations.transformers import AmaraTransformersAugmenter

augmenter = AmaraTransformersAugmenter(engine=engine, max_context_tokens=600)
prompt = await augmenter.augment_prompt(
    user_query="How do I deploy Postgres?",
    system_prompt="You are a DevOps assistant."
)`}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* REST API Endpoints Reference */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <BookOpenIcon className="w-5 h-5 text-indigo-500" />
          REST API Reference (v1)
        </h2>

        {/* POST /api/v1/memories */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                POST
              </span>
              <code className="text-xs font-mono text-slate-900 dark:text-slate-100 font-semibold">
                /api/v1/memories
              </code>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Scope: write</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 font-sans">
            Ingest, extract, deduplicate, and persist a new cognitive memory proposition.
          </p>

          <div className="relative">
            <pre className="p-3 rounded-lg bg-slate-950 text-slate-300 font-mono text-[11px] overflow-x-auto leading-relaxed">
              <code>{curlRemember}</code>
            </pre>
            <button
              onClick={() => handleCopy(curlRemember, "curl-rem")}
              className="absolute top-2 right-2 p-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
              title="Copy curl"
            >
              {copiedKey === "curl-rem" ? (
                <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <CopyIcon className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* POST /api/v1/memories/search */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
                POST
              </span>
              <code className="text-xs font-mono text-slate-900 dark:text-slate-100 font-semibold">
                /api/v1/memories/search
              </code>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Scope: read</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 font-sans">
            Multi-channel hybrid retrieval combining dense vector similarity, lexical BM25 matching, temporal recency decay, and relational graph hops.
          </p>

          <div className="relative">
            <pre className="p-3 rounded-lg bg-slate-950 text-slate-300 font-mono text-[11px] overflow-x-auto leading-relaxed">
              <code>{curlSearch}</code>
            </pre>
            <button
              onClick={() => handleCopy(curlSearch, "curl-search")}
              className="absolute top-2 right-2 p-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
              title="Copy curl"
            >
              {copiedKey === "curl-search" ? (
                <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <CopyIcon className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* POST /api/v1/context/reconstruct */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-cyan-500/10 text-cyan-500 border border-cyan-500/20">
                POST
              </span>
              <code className="text-xs font-mono text-slate-900 dark:text-slate-100 font-semibold">
                /api/v1/context/reconstruct
              </code>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Scope: read</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 font-sans">
            Synthesize an 8-stage token-bounded context prompt block with verifiable citation references (<code className="text-indigo-400">[REF-1]</code>).
          </p>

          <div className="relative">
            <pre className="p-3 rounded-lg bg-slate-950 text-slate-300 font-mono text-[11px] overflow-x-auto leading-relaxed">
              <code>{curlReconstruct}</code>
            </pre>
            <button
              onClick={() => handleCopy(curlReconstruct, "curl-recon")}
              className="absolute top-2 right-2 p-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
              title="Copy curl"
            >
              {copiedKey === "curl-recon" ? (
                <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <CopyIcon className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      </section>

      {/* Cognitive Lifecycle Reference */}
      <section className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-4">
        <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <BrainIcon className="w-5 h-5 text-indigo-500" />
          Cognitive Architecture Foundations
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-4 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-2">
            <h3 className="font-bold text-indigo-400 uppercase">5 Memory Categories</h3>
            <ul className="space-y-1.5 text-slate-600 dark:text-slate-300 font-sans text-xs">
              <li><strong>Working:</strong> Ephemeral scratchpad for intermediate reasoning.</li>
              <li><strong>Episodic:</strong> Chronological autobiographical experiences.</li>
              <li><strong>Semantic:</strong> Generalized, consolidated facts and world models.</li>
              <li><strong>Procedural:</strong> Executable workflows and step-by-step skills.</li>
              <li><strong>Associative:</strong> Graph relations and multi-hop links.</li>
            </ul>
          </div>

          <div className="p-4 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-2">
            <h3 className="font-bold text-emerald-400 uppercase">7 Lifecycle States</h3>
            <ul className="space-y-1.5 text-slate-600 dark:text-slate-300 font-sans text-xs">
              <li><strong>Active:</strong> High-priority recall candidates.</li>
              <li><strong>Decaying:</strong> Relevance fading over half-life.</li>
              <li><strong>Consolidated:</strong> Abstracted into semantic concepts.</li>
              <li><strong>Superseded:</strong> Overruled by verified contradictions.</li>
              <li><strong>Archived:</strong> Cold storage preservation.</li>
              <li><strong>Tombstoned:</strong> Soft-deleted, provenance preserved.</li>
              <li><strong>Expired:</strong> Reached temporal <code className="text-indigo-400">valid_to</code> limit.</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
