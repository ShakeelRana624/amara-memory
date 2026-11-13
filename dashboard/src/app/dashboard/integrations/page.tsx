"use client";

import React, { useState } from "react";
import {
  PlugIcon,
  CpuIcon,
  CopyIcon,
  CheckIcon,
  SparklesIcon,
  ExternalLinkIcon,
  ActivityIcon,
} from "../../../components/icons";
import { useToast } from "../../../components/Toast";

interface IntegrationItem {
  id: string;
  name: string;
  category: string;
  badge: string;
  status: "native" | "active" | "ready";
  description: string;
  packageName: string;
  installCommand: string;
  codeSnippet: string;
  highlights: string[];
}

const INTEGRATIONS: IntegrationItem[] = [
  {
    id: "langgraph",
    name: "LangGraph",
    category: "Multi-Agent Orchestration",
    badge: "Official Adapter",
    status: "native",
    description:
      "Seamlessly inject episodic and semantic memory into LangGraph agent loops without coupling core AMARA logic to LangGraph internal state schemas.",
    packageName: "amara[langgraph]",
    installCommand: "pip install \"amara-ai[langgraph]\"",
    highlights: [
      "AmaraMemoryNode: Reusable pre-decision recall & post-decision reflection",
      "Dynamic prompt context injection with token bounds",
      "Shared multi-agent project memory namespaces",
      "Full citation traceability and provenance linking",
    ],
    codeSnippet: `import asyncio
from amara.sdk import MemoryEngine, MemoryConfig
from amara.integrations.langgraph import AmaraMemoryNode, AmaraLangGraphAdapter
from langgraph.graph import StateGraph, END

async def build_langgraph_agent():
    # 1. Initialize AMARA Engine
    engine = MemoryEngine(MemoryConfig(storage_backend="postgres"))
    await engine.initialize()

    # 2. Instantiate LangGraph Adapter
    adapter = AmaraLangGraphAdapter(engine=engine)

    # 3. Define Graph Nodes
    # - Pre-hook: Injects relevant past memories into state before LLM turn
    memory_retrieve_node = AmaraMemoryNode(
        adapter=adapter,
        mode="retrieve",
        top_k=5,
        target_state_key="reconstructed_context",
    )

    # - Post-hook: Extracts new observations and facts from LLM response
    memory_reflect_node = AmaraMemoryNode(
        adapter=adapter,
        mode="reflect",
        min_importance=0.6,
    )

    print("AMARA LangGraph Memory Nodes successfully mounted.")

if __name__ == "__main__":
    asyncio.run(build_langgraph_agent())`,
  },
  {
    id: "transformers",
    name: "Hugging Face Transformers",
    category: "Foundation Models & LLMs",
    badge: "Prompt Augmenter",
    status: "native",
    description:
      "Augment open-weights foundation models (Llama 3, Mistral, Qwen, DeepSeek) with dynamic cognitive context before generation without modifying model weights or GPU cache.",
    packageName: "amara[transformers]",
    installCommand: "pip install \"amara-ai[transformers]\"",
    highlights: [
      "AmaraTransformersAugmenter: Clean pre-generation prompt contextualizer",
      "Zero interference with PyTorch CUDA memory or GPU key-value cache",
      "Strict token budgeting preventing context window overflow",
      "Automatic markdown citation formatting ([REF-1], [REF-2])",
    ],
    codeSnippet: `import asyncio
from amara.sdk import MemoryEngine, MemoryConfig
from amara.integrations.transformers import AmaraTransformersAugmenter

async def run_transformers_pipeline():
    # 1. Connect AMARA Memory Engine
    engine = MemoryEngine(MemoryConfig(storage_backend="postgres"))
    await engine.initialize()

    # 2. Initialize Augmenter with strict 600-token context budget
    augmenter = AmaraTransformersAugmenter(
        engine=engine,
        max_context_tokens=600,
        citation_style="bracketed",  # [REF-N]
    )

    # 3. Augment input prompt with relevant facts & experiences
    user_query = "What database topology did the infrastructure team select?"
    system_prompt = "You are a senior site reliability engineering assistant."

    augmented_prompt = await augmenter.augment_prompt(
        user_query=user_query,
        system_prompt=system_prompt,
        tenant_id="enterprise_prod",
    )

    print("=== Augmented Prompt Prepared for Transformers ===")
    print(augmented_prompt)

if __name__ == "__main__":
    asyncio.run(run_transformers_pipeline())`,
  },
  {
    id: "fastapi",
    name: "FastAPI External Memory Service",
    category: "Microservices & Distributed Systems",
    badge: "Cloud Client",
    status: "active",
    description:
      "Deploy AMARA as a centralized enterprise microservice cluster, allowing distributed agent services to recall and record context across microservices over secure HTTP/2.",
    packageName: "amara[fastapi]",
    installCommand: "pip install \"amara-ai[fastapi]\"",
    highlights: [
      "AmaraFastAPIClient: Async connection pooling via HTTPX",
      "Cryptographic HMAC-SHA256 API key bearer authentication",
      "FastAPI Dependency Injection: Depends(get_amara_memory)",
      "Automatic distributed failover and request retries",
    ],
    codeSnippet: `from fastapi import FastAPI, Depends
from amara.integrations.fastapi import AmaraFastAPIClient, setup_amara_memory

app = FastAPI(title="Distributed AI Agent Gateway")

# Mount AMARA distributed memory client
memory_client = AmaraFastAPIClient(
    base_url="http://localhost:8000",
    api_key="amara_live_secret_key_here",
    timeout_seconds=5.0,
)
setup_amara_memory(app, client=memory_client)

@app.post("/agent/chat")
async def chat_endpoint(user_message: str):
    # 1. Reconstruct token-budgeted memory context
    context = await memory_client.reconstruct_context(
        query=user_message,
        max_tokens=500,
    )

    # 2. Call LLM (using context.formatted_context)...
    llm_reply = f"Acknowledged based on memories: {len(context.sources)} sources."

    # 3. Asynchronously record interaction
    await memory_client.remember(
        content=f"User: {user_message}\\nAgent: {llm_reply}",
        memory_type="episodic",
    )

    return {"reply": llm_reply, "citations": context.citations}`,
  },
  {
    id: "generic-agent",
    name: "Generic Python Agent Loop",
    category: "Autonomous Agent Architectures",
    badge: "Turnkey Loop",
    status: "ready",
    description:
      "Standard turn-by-turn memory loop wrapper for custom agent frameworks, AutoGen, CrewAI, or bespoke Python reasoning scripts.",
    packageName: "amara",
    installCommand: "pip install amara-ai",
    highlights: [
      "AgentMemoryLoop: Turnkey session & context manager",
      "Automatic before-turn recall and after-turn persistence",
      "Contradiction detection and salience decay handling",
      "Zero external framework dependencies",
    ],
    codeSnippet: `import asyncio
from amara.sdk import MemoryEngine, MemoryConfig
from amara.integrations.generic_agent import AgentMemoryLoop

async def run_conversational_agent():
    # 1. Initialize AMARA Engine
    engine = MemoryEngine(MemoryConfig(storage_backend="postgres"))
    await engine.initialize()

    # 2. Attach turn-by-turn memory loop
    loop = AgentMemoryLoop(
        engine=engine,
        tenant_id="customer_success",
        session_id="sess_live_1092",
    )

    # Turn 1: User introduces preference
    await loop.before_turn("I prefer technical markdown and hate marketing jargon.")
    # ... Agent generates response ...
    await loop.after_turn(
        agent_response="Understood. All future answers will use concise technical markdown.",
        importance=0.9,
    )

    # Turn 2: Verify contextual recall
    prompt_context = await loop.before_turn("Explain our database architecture.")
    print("Injected Memory Context for Turn 2:")
    print(prompt_context)

if __name__ == "__main__":
    asyncio.run(run_conversational_agent())`,
  },
];

export default function IntegrationsPage() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<string>("langgraph");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const selectedIntegration =
    INTEGRATIONS.find((item) => item.id === activeTab) || INTEGRATIONS[0];

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    toast.success("Snippet copied to clipboard");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <PlugIcon className="w-6 h-6 text-indigo-500" />
              AI Framework Integrations
            </h1>
            <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
              Production-ready adapters connecting AMARA cognitive memory to LangGraph, Hugging Face, FastAPI, and autonomous agent loops
            </p>
          </div>
          <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            4 Native Adapters Ready
          </span>
        </div>
      </div>

      {/* Integration Selector Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {INTEGRATIONS.map((item) => {
          const isSelected = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`text-left p-4 rounded-xl border transition-all duration-150 flex flex-col justify-between ${
                isSelected
                  ? "border-indigo-500/80 bg-indigo-500/5 dark:bg-indigo-500/10 shadow-sm ring-1 ring-indigo-500/30"
                  : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50/50 dark:hover:bg-slate-800/40"
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    {item.category}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
                    {item.badge}
                  </span>
                </div>
                <h3 className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <CpuIcon className="w-4 h-4 text-indigo-500" />
                  {item.name}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-sans line-clamp-2">
                  {item.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] font-mono">
                <span className="text-slate-400">Status</span>
                <span className="text-emerald-500 font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Ready
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected Integration Detail & Code Sandbox */}
      <section className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold font-mono text-slate-900 dark:text-slate-100">
                {selectedIntegration.name} Integration
              </h2>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
                {selectedIntegration.category}
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 font-sans mt-1">
              {selectedIntegration.description}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() =>
                handleCopy(selectedIntegration.installCommand, "install-cmd")
              }
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 font-mono text-xs text-slate-700 dark:text-slate-300 hover:text-indigo-400 flex items-center gap-1.5 transition-colors"
            >
              {copiedKey === "install-cmd" ? (
                <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <CopyIcon className="w-3.5 h-3.5" />
              )}
              <span>{selectedIntegration.installCommand}</span>
            </button>
          </div>
        </div>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {selectedIntegration.highlights.map((highlight, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg border border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/40 flex items-start gap-2.5 text-xs font-sans text-slate-700 dark:text-slate-300"
            >
              <SparklesIcon className="w-4 h-4 text-indigo-500 flex-shrink-0 mt-0.5" />
              <span>{highlight}</span>
            </div>
          ))}
        </div>

        {/* Executable Code Block */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <ActivityIcon className="w-3.5 h-3.5 text-indigo-400" />
              Executable Integration Pattern
            </span>
            <button
              onClick={() =>
                handleCopy(selectedIntegration.codeSnippet, "code-snippet")
              }
              className="flex items-center gap-1.5 text-xs font-mono text-indigo-500 hover:text-indigo-400 transition-colors"
            >
              {copiedKey === "code-snippet" ? (
                <CheckIcon className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <CopyIcon className="w-3.5 h-3.5" />
              )}
              <span>
                {copiedKey === "code-snippet" ? "Copied" : "Copy Code"}
              </span>
            </button>
          </div>

          <pre className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-950 text-indigo-300 font-mono text-xs overflow-x-auto leading-relaxed">
            <code>{selectedIntegration.codeSnippet}</code>
          </pre>
        </div>
      </section>
    </div>
  );
}

