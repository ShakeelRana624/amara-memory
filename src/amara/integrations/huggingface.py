"""Hugging Face Transformers cognitive memory integration for AMARA.

Provides a generation wrapper for Transformers pipelines and causal language models that
automatically reconstructs verified, token-bounded memory context before model execution.
Does not modify model weights or claim parametric continual learning in this release.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from amara.enums import MemoryCategory
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.engine import MemoryEngine
from amara.sdk.sync import SyncMemoryEngine


@dataclass(frozen=True)
class AmaraGenerationResult:
    """Encapsulates the generated text along with the grounding memory provenance."""

    generated_text: str
    raw_output: Any
    reconstructed_context: str
    citations: tuple[dict[str, Any], ...]
    tokens_used: int
    augmented_prompt: str


class AmaraTransformersWrapper:
    """Augments Hugging Face Transformers generation with AMARA cognitive memory."""

    DEFAULT_PROMPT_TEMPLATE = "{cognitive_context}\n\nUser Prompt: {user_prompt}\n\nAssistant:"

    def __init__(
        self,
        engine: MemoryEngine | SyncMemoryEngine,
        model: Any = None,
        tokenizer: Any = None,
        pipeline: Any = None,
        namespace: str = "default",
        tenant_id: str | None = None,
        token_budget: int = 1536,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        auto_remember_turns: bool = False,
        prompt_template: str | None = None,
    ) -> None:
        """Initialize the Transformers memory wrapper.

        Args:
            engine: AMARA MemoryEngine (async) or SyncMemoryEngine (sync).
            model: Hugging Face PreTrainedModel or custom callable.
            tokenizer: Hugging Face PreTrainedTokenizer or compatible tokenizer.
            pipeline: Hugging Face pipeline object (e.g., text-generation).
            namespace: Memory partition namespace.
            tenant_id: Tenant scope identifier.
            token_budget: Maximum tokens allocated for context reconstruction.
            strategy: Hybrid or dense retrieval strategy.
            auto_remember_turns: Whether to persist prompt+response into episodic memory.
            prompt_template: Custom template formatting cognitive context and user prompt.
        """
        self.engine = engine
        self.model = model
        self.tokenizer = tokenizer
        self.pipeline = pipeline
        self.namespace = namespace
        self.tenant_id = tenant_id
        self.token_budget = token_budget
        self.strategy = strategy
        self.auto_remember_turns = auto_remember_turns
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT_TEMPLATE

    def _format_prompt(self, user_prompt: str, cognitive_context: str) -> str:
        """Format the final prompt with grounded context."""
        if not cognitive_context.strip():
            return user_prompt
        return self.prompt_template.format(
            cognitive_context=cognitive_context.strip(),
            user_prompt=user_prompt.strip(),
        )

    # -----------------------------------------------------------------------
    # Synchronous Generation
    # -----------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        namespace: str | None = None,
        max_new_tokens: int = 256,
        **kwargs: Any,
    ) -> AmaraGenerationResult:
        """Synchronously reconstruct context from AMARA and generate text."""
        ns = namespace or self.namespace

        # 1. Reconstruct token-bounded context
        if isinstance(self.engine, SyncMemoryEngine):
            recon = self.engine.reconstruct(
                query=prompt,
                namespace=ns,
                budget=self.token_budget,
                strategy=self.strategy,
                tenant_id=self.tenant_id,
            )
        else:
            raise RuntimeError(
                "Synchronous generate() requires a SyncMemoryEngine. Use agenerate() for async."
            )

        context_str = recon.formatted_context
        citations = tuple(
            {
                "citation_tag": c.citation_tag,
                "memory_id": str(c.memory_id),
                "source_id": c.source_id,
                "author_id": c.author_id,
                "snippet": c.snippet,
                "temporal_anchor": c.temporal_anchor,
            }
            for c in recon.citations
        )

        augmented_prompt = self._format_prompt(prompt, context_str)

        # 2. Dispatch generation
        raw_output = self._dispatch_model(augmented_prompt, max_new_tokens=max_new_tokens, **kwargs)
        generated_text = self._extract_generated_text(raw_output, augmented_prompt)

        # 3. Optional episodic persistence
        if self.auto_remember_turns:
            turn_content = f"User: {prompt}\nResponse: {generated_text}"
            self.engine.remember(
                content=turn_content,
                author_id="transformers_agent",
                memory_type=MemoryCategory.EPISODIC,
                namespace=ns,
                tenant_id=self.tenant_id,
            )

        return AmaraGenerationResult(
            generated_text=generated_text,
            raw_output=raw_output,
            reconstructed_context=context_str,
            citations=citations,
            tokens_used=recon.total_tokens_used,
            augmented_prompt=augmented_prompt,
        )

    # -----------------------------------------------------------------------
    # Asynchronous Generation
    # -----------------------------------------------------------------------

    async def agenerate(
        self,
        prompt: str,
        namespace: str | None = None,
        max_new_tokens: int = 256,
        **kwargs: Any,
    ) -> AmaraGenerationResult:
        """Asynchronously reconstruct context from AMARA and generate text."""
        ns = namespace or self.namespace

        # 1. Reconstruct token-bounded context
        if isinstance(self.engine, MemoryEngine):
            recon = await self.engine.reconstruct(
                query=prompt,
                namespace=ns,
                budget=self.token_budget,
                strategy=self.strategy,
                tenant_id=self.tenant_id,
            )
        else:
            recon = self.engine.reconstruct(
                query=prompt,
                namespace=ns,
                budget=self.token_budget,
                strategy=self.strategy,
                tenant_id=self.tenant_id,
            )

        context_str = recon.formatted_context
        citations = tuple(
            {
                "citation_tag": c.citation_tag,
                "memory_id": str(c.memory_id),
                "source_id": c.source_id,
                "author_id": c.author_id,
                "snippet": c.snippet,
                "temporal_anchor": c.temporal_anchor,
            }
            for c in recon.citations
        )

        augmented_prompt = self._format_prompt(prompt, context_str)

        # 2. Dispatch generation
        raw_output = self._dispatch_model(augmented_prompt, max_new_tokens=max_new_tokens, **kwargs)
        generated_text = self._extract_generated_text(raw_output, augmented_prompt)

        # 3. Optional episodic persistence
        if self.auto_remember_turns:
            turn_content = f"User: {prompt}\nResponse: {generated_text}"
            if isinstance(self.engine, MemoryEngine):
                await self.engine.remember(
                    content=turn_content,
                    author_id="transformers_agent",
                    memory_type=MemoryCategory.EPISODIC,
                    namespace=ns,
                    tenant_id=self.tenant_id,
                )
            else:
                self.engine.remember(
                    content=turn_content,
                    author_id="transformers_agent",
                    memory_type=MemoryCategory.EPISODIC,
                    namespace=ns,
                    tenant_id=self.tenant_id,
                )

        return AmaraGenerationResult(
            generated_text=generated_text,
            raw_output=raw_output,
            reconstructed_context=context_str,
            citations=citations,
            tokens_used=recon.total_tokens_used,
            augmented_prompt=augmented_prompt,
        )

    # -----------------------------------------------------------------------
    # Model Invocation & Text Parsing
    # -----------------------------------------------------------------------

    def _dispatch_model(self, prompt: str, **kwargs: Any) -> Any:
        """Call either pipeline, model+tokenizer, or callable mock."""
        if self.pipeline is not None:
            return self.pipeline(prompt, **kwargs)

        if self.model is not None and self.tokenizer is not None:
            # Check for standard HF generate
            inputs = self.tokenizer(prompt, return_tensors="pt")
            return self.model.generate(**inputs, **kwargs)

        if callable(self.model):
            return self.model(prompt, **kwargs)

        # Fallback simulated response when running without heavy torch weights
        return f"[Simulated Response grounded in AMARA context for prompt: '{prompt[:40]}...']"

    def _extract_generated_text(self, raw_output: Any, augmented_prompt: str) -> str:
        """Extract clean text string from diverse Hugging Face return structures."""
        if isinstance(raw_output, str):
            return raw_output

        # Handle list of dicts from pipeline (e.g. [{"generated_text": "..."}])
        if isinstance(raw_output, list) and raw_output and isinstance(raw_output[0], dict):
            text = str(raw_output[0].get("generated_text", ""))
            if text.startswith(augmented_prompt):
                return text[len(augmented_prompt) :].strip()
            return text.strip()

        # Handle token tensors with tokenizer
        if self.tokenizer is not None and hasattr(raw_output, "shape"):
            decoded = str(self.tokenizer.decode(raw_output[0], skip_special_tokens=True))
            if decoded.startswith(augmented_prompt):
                return decoded[len(augmented_prompt) :].strip()
            return decoded.strip()

        return str(raw_output).strip()
