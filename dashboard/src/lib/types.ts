/**
 * TypeScript data models and API contracts for AMARA Developer Dashboard.
 * Strictly aligned with backend REST API schemas.
 */

export type MemoryCategory =
  | "working"
  | "episodic"
  | "semantic"
  | "procedural"
  | "associative";

export type LifecycleStatus =
  | "active"
  | "decaying"
  | "consolidated"
  | "superseded"
  | "archived"
  | "expired"
  | "tombstoned";

export type RetrievalStrategy =
  | "hybrid"
  | "dense_vector"
  | "lexical_sparse"
  | "temporal_recency"
  | "relational_graph";

export interface MemoryItem {
  id: string;
  tenant_id: string;
  namespace: string;
  content: string;
  normalized_content: string;
  memory_type: MemoryCategory;
  status: LifecycleStatus;
  confidence: number;
  importance: number;
  source_id: string;
  author_id: string;
  session_id?: string | null;
  asserted_at: string;
  valid_from: string;
  valid_to?: string | null;
  version: number;
  root_id: string;
  parent_ids: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RecallItem {
  item: MemoryItem;
  relevance_score: number;
  confidence: number;
  match_explanation: string;
}

export interface SearchResponse {
  query: string;
  tenant_id: string;
  namespace: string;
  results: RecallItem[];
  total_candidates: number;
  latency_ms: number;
}

export interface CitationItem {
  citation_tag: string;
  memory_id: string;
  source_id: string;
  author_id: string;
  confidence: number;
  importance: number;
  temporal_anchor: string;
  snippet: string;
}

export interface ReconstructResponse {
  query: string;
  formatted_context: string;
  citations: CitationItem[];
  total_tokens_used: number;
  remaining_token_budget: number;
  abstention_recommended: boolean;
  abstention_reason?: string | null;
  candidates_retrieved: number;
  candidates_packed: number;
}

export interface UsageResponse {
  tenant_id: string;
  namespace?: string | null;
  total_memories: number;
  by_category: Record<string, number>;
  by_status: Record<string, number>;
  average_confidence: number;
  average_importance: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  storage_backend: string;
  database_connected: boolean;
  timestamp: string;
}

export interface APIKeyInfoResponse {
  key_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
}

export interface APIKeyCreatedResponse {
  key_id: string;
  name: string;
  key_prefix: string;
  raw_key: string;
  scopes: string[];
  tenant_id: string;
  created_at: string;
  expires_at?: string | null;
}

export interface MemoryRelationship {
  source_id: string;
  target_id: string;
  relation_type: "causal" | "temporal_next" | "entity_attr" | "contradicts" | "depends_on" | "derived_from" | "associated_with";
  weight: number;
  metadata?: Record<string, unknown>;
}

export interface MemoryEvidence {
  id: string;
  source_reference: string;
  raw_payload: string;
  confidence_score: number;
  timestamp: string;
}

export interface MemoryInspection {
  record: MemoryItem;
  parents: MemoryItem[];
  relationships: MemoryRelationship[];
  evidence: MemoryEvidence[];
}

