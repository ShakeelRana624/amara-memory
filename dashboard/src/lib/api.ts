import {
  APIKeyCreatedResponse,
  APIKeyInfoResponse,
  HealthResponse,
  LifecycleStatus,
  MemoryCategory,
  MemoryInspection,
  MemoryItem,
  ReconstructResponse,
  RetrievalStrategy,
  SearchResponse,
  UsageResponse,
} from "./types";
import {
  SAMPLE_API_KEYS,
  SAMPLE_HEALTH,
  SAMPLE_INSPECTION_MAP,
  SAMPLE_MEMORIES,
  SAMPLE_RECALL_RESULTS,
  SAMPLE_RECONSTRUCTION,
  SAMPLE_USAGE,
} from "./sample-data";

export interface ApiClientConfig {
  baseUrl: string;
  apiKey: string | null;
  isSandbox?: boolean;
}

export class AmaraApiClient {
  private baseUrl: string;
  private apiKey: string | null;
  private isSandbox: boolean;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.apiKey = config.apiKey;
    this.isSandbox = !!config.isSandbox;
  }

  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  async checkHealth(): Promise<{ data: HealthResponse; isSandbox: boolean }> {
    if (this.isSandbox) {
      return { data: SAMPLE_HEALTH, isSandbox: true };
    }
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/health`, {
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      });
      if (!res.ok) {
        throw new Error(`Health check returned status ${res.status}`);
      }
      const data: HealthResponse = await res.json();
      return { data, isSandbox: false };
    } catch {
      return { data: SAMPLE_HEALTH, isSandbox: true };
    }
  }

  async getUsage(namespace?: string): Promise<UsageResponse> {
    if (this.isSandbox || !this.apiKey) {
      return SAMPLE_USAGE;
    }
    const url = new URL(`${this.baseUrl}/api/v1/usage`);
    if (namespace) {
      url.searchParams.set("namespace", namespace);
    }
    const res = await fetch(url.toString(), {
      headers: this.getHeaders(),
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch usage: ${res.statusText}`);
    }
    return res.json();
  }

  async getMemories(
    query = "all",
    namespace = "default",
    strategy: RetrievalStrategy = "temporal_recency",
    topK = 50
  ): Promise<MemoryItem[]> {
    if (this.isSandbox || !this.apiKey) {
      return SAMPLE_MEMORIES;
    }
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/memories/search`, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({
          query: query.trim() || "all",
          namespace,
          strategy,
          top_k: topK,
          include_historical: true,
        }),
      });
      if (!res.ok) {
        throw new Error(`Memory query failed with status ${res.status}`);
      }
      const data: SearchResponse = await res.json();
      return data.results.map((r) => r.item);
    } catch {
      return SAMPLE_MEMORIES;
    }
  }

  async getMemory(id: string): Promise<MemoryItem> {
    if (this.isSandbox || !this.apiKey) {
      const found = SAMPLE_MEMORIES.find((m) => m.id === id);
      if (found) return found;
      return SAMPLE_MEMORIES[0];
    }
    const res = await fetch(`${this.baseUrl}/api/v1/memories/${id}`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      throw new Error(`Memory '${id}' not found`);
    }
    const json = await res.json();
    return json.data;
  }

  async inspectMemory(id: string): Promise<MemoryInspection> {
    if (this.isSandbox || !this.apiKey) {
      const inspection = SAMPLE_INSPECTION_MAP[id];
      if (inspection) return inspection;
      const mem = SAMPLE_MEMORIES.find((m) => m.id === id) || SAMPLE_MEMORIES[0];
      return {
        record: mem,
        parents: [],
        relationships: [],
        evidence: [],
      };
    }
    // Backend get_memory returns record; we retrieve record and construct inspection
    const item = await this.getMemory(id);
    return {
      record: item,
      parents: [],
      relationships: [],
      evidence: [],
    };
  }

  async createMemory(payload: {
    content: string;
    author_id?: string;
    memory_type?: MemoryCategory;
    confidence?: number;
    importance?: number;
    namespace?: string;
    metadata?: Record<string, unknown>;
  }): Promise<MemoryItem> {
    if (this.isSandbox || !this.apiKey) {
      const mockItem: MemoryItem = {
        id: `mock-${Date.now()}`,
        tenant_id: "tenant-sandbox",
        namespace: payload.namespace || "default",
        content: payload.content,
        normalized_content: payload.content.toLowerCase(),
        memory_type: payload.memory_type || "episodic",
        status: "active",
        confidence: payload.confidence ?? 0.95,
        importance: payload.importance ?? 0.7,
        source_id: "sandbox_manual_input",
        author_id: payload.author_id || "sandbox_user",
        session_id: null,
        asserted_at: new Date().toISOString(),
        valid_from: new Date().toISOString(),
        valid_to: null,
        version: 1,
        root_id: `mock-${Date.now()}`,
        parent_ids: [],
        metadata: payload.metadata || {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      SAMPLE_MEMORIES.unshift(mockItem);
      return mockItem;
    }

    const res = await fetch(`${this.baseUrl}/api/v1/memories`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        content: payload.content,
        author_id: payload.author_id || "user",
        memory_type: payload.memory_type,
        confidence: payload.confidence ?? 1.0,
        importance: payload.importance ?? 0.5,
        namespace: payload.namespace || "default",
        metadata: payload.metadata || {},
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Failed to create memory (${res.status})`);
    }
    const json = await res.json();
    return json.data;
  }

  async updateMemory(
    id: string,
    payload: { content?: string; metadata?: Record<string, unknown> }
  ): Promise<MemoryItem> {
    if (this.isSandbox || !this.apiKey) {
      const idx = SAMPLE_MEMORIES.findIndex((m) => m.id === id);
      if (idx !== -1) {
        SAMPLE_MEMORIES[idx] = {
          ...SAMPLE_MEMORIES[idx],
          content: payload.content ?? SAMPLE_MEMORIES[idx].content,
          metadata: { ...SAMPLE_MEMORIES[idx].metadata, ...(payload.metadata || {}) },
          updated_at: new Date().toISOString(),
          version: SAMPLE_MEMORIES[idx].version + 1,
        };
        return SAMPLE_MEMORIES[idx];
      }
      throw new Error("Memory not found in sandbox");
    }

    const res = await fetch(`${this.baseUrl}/api/v1/memories/${id}`, {
      method: "PATCH",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Failed to update memory: ${res.statusText}`);
    }
    const json = await res.json();
    return json.data;
  }

  async deleteMemory(id: string, hard = false): Promise<boolean> {
    if (this.isSandbox || !this.apiKey) {
      const idx = SAMPLE_MEMORIES.findIndex((m) => m.id === id);
      if (idx !== -1) {
        if (hard) {
          SAMPLE_MEMORIES.splice(idx, 1);
        } else {
          SAMPLE_MEMORIES[idx].status = "tombstoned" as LifecycleStatus;
        }
        return true;
      }
      return false;
    }

    const res = await fetch(`${this.baseUrl}/api/v1/memories/${id}?hard=${hard}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    return res.ok;
  }

  async searchMemories(payload: {
    query: string;
    strategy?: RetrievalStrategy;
    top_k?: number;
    namespace?: string;
    memory_types?: MemoryCategory[];
    include_historical?: boolean;
  }): Promise<SearchResponse> {
    if (this.isSandbox || !this.apiKey) {
      return {
        query: payload.query,
        tenant_id: "tenant-sandbox",
        namespace: payload.namespace || "default",
        results: SAMPLE_RECALL_RESULTS,
        total_candidates: SAMPLE_RECALL_RESULTS.length,
        latency_ms: 14.2,
      };
    }

    const res = await fetch(`${this.baseUrl}/api/v1/memories/search`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        query: payload.query,
        strategy: payload.strategy || "hybrid",
        top_k: payload.top_k || 10,
        namespace: payload.namespace || "default",
        memory_types: payload.memory_types,
        include_historical: payload.include_historical ?? false,
      }),
    });
    if (!res.ok) {
      throw new Error(`Search failed: ${res.statusText}`);
    }
    return res.json();
  }

  async consolidate(namespace = "default"): Promise<{ consolidated_count: number; new_semantic_memories: MemoryItem[] }> {
    if (this.isSandbox || !this.apiKey) {
      return {
        consolidated_count: 1,
        new_semantic_memories: [SAMPLE_MEMORIES[5]],
      };
    }
    const res = await fetch(`${this.baseUrl}/api/v1/memories/consolidate`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ namespace }),
    });
    if (!res.ok) {
      throw new Error(`Consolidation failed: ${res.statusText}`);
    }
    return res.json();
  }

  async reconstructContext(payload: {
    query: string;
    budget_tokens?: number;
    strategy?: RetrievalStrategy;
    namespace?: string;
  }): Promise<ReconstructResponse> {
    if (this.isSandbox || !this.apiKey) {
      return {
        ...SAMPLE_RECONSTRUCTION,
        query: payload.query,
      };
    }

    const res = await fetch(`${this.baseUrl}/api/v1/context/reconstruct`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        query: payload.query,
        budget_tokens: payload.budget_tokens || 2048,
        strategy: payload.strategy || "hybrid",
        namespace: payload.namespace || "default",
      }),
    });
    if (!res.ok) {
      throw new Error(`Context reconstruction failed: ${res.statusText}`);
    }
    return res.json();
  }

  async listKeys(): Promise<APIKeyInfoResponse[]> {
    if (this.isSandbox || !this.apiKey) {
      return SAMPLE_API_KEYS;
    }
    const res = await fetch(`${this.baseUrl}/api/v1/auth/keys`, {
      headers: this.getHeaders(),
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`Failed to list API keys: ${res.statusText}`);
    }
    return res.json();
  }

  async createKey(payload: {
    name: string;
    scopes?: string[];
    workspace_id?: string;
    expires_in_days?: number;
  }): Promise<APIKeyCreatedResponse> {
    if (this.isSandbox || !this.apiKey) {
      const mockKey: APIKeyCreatedResponse = {
        key_id: `key-${Date.now()}`,
        name: payload.name,
        key_prefix: `live_${Date.now().toString(16).slice(-6)}`,
        raw_key: `amara_live_${Date.now().toString(16).slice(-6)}_${Math.random().toString(36).substring(2, 15)}`,
        scopes: payload.scopes || ["read", "write"],
        tenant_id: "tenant-sandbox",
        created_at: new Date().toISOString(),
        expires_at: null,
      };
      SAMPLE_API_KEYS.push({
        key_id: mockKey.key_id,
        name: mockKey.name,
        key_prefix: mockKey.key_prefix,
        scopes: mockKey.scopes,
        is_active: true,
        created_at: mockKey.created_at,
        last_used_at: null,
        expires_at: null,
      });
      return mockKey;
    }

    const res = await fetch(`${this.baseUrl}/api/v1/auth/keys`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        name: payload.name,
        scopes: payload.scopes || ["read", "write"],
        workspace_id: payload.workspace_id,
        expires_in_days: payload.expires_in_days,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Key creation failed (${res.status})`);
    }
    return res.json();
  }

  async rotateKey(keyId: string): Promise<APIKeyCreatedResponse> {
    if (this.isSandbox || !this.apiKey) {
      const newSecret = `amara_live_rotated_${Math.random().toString(36).substring(2, 12)}`;
      return {
        key_id: keyId,
        name: "Rotated Key",
        key_prefix: "live_rot",
        raw_key: newSecret,
        scopes: ["read", "write"],
        tenant_id: "tenant-sandbox",
        created_at: new Date().toISOString(),
        expires_at: null,
      };
    }
    const res = await fetch(`${this.baseUrl}/api/v1/auth/keys/${keyId}/rotate`, {
      method: "POST",
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      throw new Error(`Key rotation failed: ${res.statusText}`);
    }
    return res.json();
  }

  async revokeKey(keyId: string): Promise<boolean> {
    if (this.isSandbox || !this.apiKey) {
      const target = SAMPLE_API_KEYS.find((k) => k.key_id === keyId);
      if (target) {
        target.is_active = false;
        return true;
      }
      return false;
    }
    const res = await fetch(`${this.baseUrl}/api/v1/auth/keys/${keyId}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    return res.ok;
  }
}
