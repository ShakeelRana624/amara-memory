"""AMARA Framework Integrations.

Provides plug-and-play cognitive memory adapters for:
- LangGraph (StateGraph nodes for pre-retrieval, post-extraction, actions, shared project memory)
- Hugging Face Transformers (context-augmented text generation pipelines)
- FastAPI (HTTP client, route dependencies, session middleware)
- Generic Python Agents (autonomous loop memory manager)
"""

from __future__ import annotations

from amara.integrations.fastapi import (
    AmaraClient,
    AmaraMemoryDependency,
    AmaraSessionMiddleware,
)
from amara.integrations.generic_agent import (
    AmaraAgentMemory,
    GroundedContext,
)
from amara.integrations.huggingface import (
    AmaraGenerationResult,
    AmaraTransformersWrapper,
)
from amara.integrations.langgraph import (
    AmaraLangGraphAdapter,
)

__all__ = [
    "AmaraAgentMemory",
    "AmaraClient",
    "AmaraGenerationResult",
    "AmaraLangGraphAdapter",
    "AmaraMemoryDependency",
    "AmaraSessionMiddleware",
    "AmaraTransformersWrapper",
    "GroundedContext",
]
