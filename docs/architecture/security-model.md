# AMARA Security Model: Isolation, Access Control, and Compliance

**Author**: AMARA Architecture & AI Research Team  
**Date**: November 2026  
**Status**: Specification Baseline (v0.1)  
**Related Documents**: [`data-model.md`](data-model.md), [`memory-lifecycle.md`](memory-lifecycle.md), [`system-design.md`](system-design.md)

---

## 1. Threat Model & Security Objectives

Agent memory systems introduce unique security surfaces not present in standard databases or stateless LLM APIs. Persistent memory creates risks of:
1. **Cross-Tenant Context Poisoning & Leakage**: Information from Tenant A being surfaced to Tenant B.
2. **Indirect Prompt Injection via Memory**: An adversary embedding malicious instructions in web content or tool outputs that gets stored in memory and later executed by the agent as a trusted instruction.
3. **Secret & Credential Ingestion**: An agent inadvertently recording OAuth tokens, API keys, passwords, or personal credentials into persistent vector stores.
4. **Regulatory Non-Compliance**: Inability to mathematically verify and guarantee complete deletion of user data and derived knowledge (GDPR Right-to-be-Forgotten).

AMARA enforces **defense-in-depth** across isolation, access control, sanitization, and cryptographic provenance.

---

## 2. Multi-Tenant Isolation Architecture

```text
+-------------------------------------------------------------------------------+
|                             Client Application                                |
|                      Context: (tenant_id="tenant_corp_42")                    |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| AMARA Core Security Interceptor                                               |
|  - Validates tenant_id format and authorization token                         |
|  - Injects tenant_id into session configuration variable                      |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| PostgreSQL Row-Level Security (RLS) Enforcement                               |
|  SET LOCAL app.current_tenant_id = 'tenant_corp_42';                          |
|                                                                               |
|  CREATE POLICY tenant_isolation_policy ON memory_records                      |
|      USING (tenant_id = current_setting('app.current_tenant_id', true));      |
+-------------------------------------------------------------------------------+
```

### 2.1 Hard Database-Level Row Security
Tenant isolation in AMARA is not an application-layer `WHERE` clause convention. It is enforced directly at the database engine level using PostgreSQL **Row-Level Security (RLS)**:
- Every query executes within a database transaction where `app.current_tenant_id` is set.
- Attempting to query, insert, update, or delete rows outside the caller's authorized tenant is blocked by the database kernel, even if an application bug omits the tenant parameter.

### 2.2 Namespace Partitioning
Within a single tenant, memory is segmented by `namespace` (e.g., `agent_researcher`, `agent_coder`, `session_123`). Namespaces prevent inter-agent context collisions while allowing controlled cross-namespace read sharing via explicit access grants.

---

## 3. Access Control: RBAC & ABAC

AMARA defines granular permissions for memory operations:

| Permission | Description | Scope |
| :--- | :--- | :--- |
| `memory:read` | Retrieve and query active memory records | Namespace / Tenant |
| `memory:write` | Ingest and store new memory records | Namespace / Tenant |
| `memory:update` | Modify salience, validity, or attributes of existing memories | Namespace / Tenant |
| `memory:consolidate` | Execute asynchronous episodic-to-semantic consolidation jobs | Tenant Admin |
| `memory:delete` | Soft-delete / tombstone specific memory records | Namespace / Tenant |
| `memory:purge` | Execute irreversible hard purge and GDPR cascading deletion | Tenant Admin |

---

## 4. Memory Ingestion Sanitization Pipeline

Every memory record must pass through the `SanitizationInterceptor` before entering the storage engine:

```text
Incoming Percept / Text
         |
         v
+-------------------------------------------------------------+
| Step 1: Secret & Credential Detection                       |
|  - High-entropy string detection (Shannon entropy > 4.5)     |
|  - Known pattern matching (AWS, OpenAI, GitHub, Bearer, SSH)|
|  - Action: Redact with [REDACTED_CREDENTIAL] or reject      |
+-------------------------------------------------------------+
         |
         v
+-------------------------------------------------------------+
| Step 2: Indirect Prompt Injection Defense                   |
|  - Strip delimiter collision tokens (`### System:`, etc.)   |
|  - Tag untrusted inputs with origin metadata                |
|  - Wrap stored content in immutable boundary envelopes      |
+-------------------------------------------------------------+
         |
         v
+-------------------------------------------------------------+
| Step 3: PII Sensitivity Classification                      |
|  - Named entity scrubbing for phone, SSN, credit cards      |
|  - Mark record with sensitivity level for restricted access |
+-------------------------------------------------------------+
         |
         v
Persistent Memory Engine
```

---

## 5. Cryptographic Provenance & Tamper-Evident Lineage

To ensure memories cannot be fabricated or silently altered:
1. **Content Hashing**: Every record stores a SHA-256 hash of its original textual content computed at ingestion time:
   $$\text{content\_hash} = \text{SHA256}(\text{content} \parallel \text{author\_id} \parallel \text{asserted\_at})$$
2. **Immutable Lineage DAG**: When consolidation workers derive semantic nodes from episodic parents, the parents' IDs and cryptographic hashes are embedded into the child's `lineage` block.
3. **Audit Trail**: Any update to memory metadata generates an auditable, timestamped entry in the audit log table.

---

## 6. Privacy & Regulatory Compliance (GDPR / CCPA)

### 6.1 The Cascading Deletion Problem
Under GDPR Article 17 ("Right to be Forgotten"), deleting a raw user message is insufficient if that message was consolidated into:
- 3 Semantic concept nodes.
- 5 Relational association edges.
- 1 Procedural skill.

### 6.2 AMARA Deterministic Deletion Cascade
When a purge request is issued for a user or source record $m_{root}$:

```text
                   Purge Request (Root Memory m_0)
                                 |
                                 v
        Traverse Provenance DAG: Identify All Descendants
                                 |
                 +---------------+---------------+
                 |                               |
                 v                               v
     Child Node m_1 (Semantic)       Child Node m_2 (Semantic)
    Parent Set: {m_0}               Parent Set: {m_0, m_other}
                 |                               |
                 v                               v
     No other parents remain:        Has other supporting parent:
        -> HARD PURGE                   -> RETAIN child, but
        -> DROP Embedding                  REMOVE m_0 from parent_ids
                                           RECALCULATE confidence
```

1. **Topological Lineage Traversal**: AMARA identifies all records where $m_{root}$ appears in `parent_ids`.
2. **Support Recalculation**:
   - If a derived node was derived *exclusively* from $m_{root}$, the child node is recursively purged.
   - If a derived node is supported by multiple independent parents ($m_{root}$ and $m_{other}$), $m_{root}$ is removed from the lineage set, and the node's confidence score is discounted proportionally.
3. **Index Cleanup**: Corresponding vector embeddings are immediately dropped from `pgvector` HNSW indexes.
4. **Cryptographic Proof of Erasure**: A signed certificate of erasure recording the count of purged records and hashes is generated for regulatory compliance.

