# 2. Cognitive Memory Scope and System Boundaries

Date: 2026-11-13  
Status: Accepted

## Context

The term "memory" in machine learning encompasses disparate concepts:
1. **Hardware Memory**: GPU VRAM management, unified CPU/GPU paging, tensor memory allocations, FlashAttention KV-cache quantization.
2. **Parametric Continual Learning**: Modifying model weights continuously to prevent catastrophic forgetting.
3. **Cognitive Agent Memory**: Structured, externalized representations of experience (episodic), immediate reasoning context (working), factual knowledge (semantic), and operational routines (procedural).

Attempting to solve hardware memory management and cognitive agent memory simultaneously leads to bloated dependencies, conflicting performance targets, and architectural ambiguity.

## Decision

AMARA will exclusively focus on **Cognitive Memory Architecture**:
- Memory represents structured knowledge, context, and experience accessible to reasoning agents.
- AMARA explicitly excludes GPU memory optimizations, CUDA kernel management, model parameter weight training, and KV-cache tensor compression.
- Boundaries between cognitive tiers (Working, Episodic, Semantic, Procedural) will be enforced through explicit interfaces and domain models.

## Consequences

### Positive
- Crisp focus on reasoning quality, context persistence, and cognitive agent memory dynamics.
- Eliminates heavy C++/CUDA dependencies and hardware-specific compilation burdens.
- Framework remains lightweight, portable, and easily deployable across any environment (local, containerized, edge, cloud).

### Negative / Limitations
- Does not solve hardware VRAM exhaustion or low-level model inference paging; users must rely on dedicated inference runtimes (e.g., vLLM, TensorRT-LLM) for GPU memory management.
