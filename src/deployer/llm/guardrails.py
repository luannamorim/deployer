"""Pre/post processing hooks for LLM calls.

Extensible injection points for input validation, PII redaction, output
filtering, etc. Hooks are plain async callables. A :class:`Guardrails`
pipeline applies them in order and can be replaced per deployment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from deployer.llm.providers.base import CompletionRequest, LLMResponse

    PreHook = Callable[[CompletionRequest], Awaitable[CompletionRequest]]
    PostHook = Callable[[LLMResponse], Awaitable[LLMResponse]]


class GuardrailViolation(Exception):
    """Raised by a hook to reject a request or response."""


class Guardrails:
    """Pipeline of pre- and post-processing hooks."""

    def __init__(
        self,
        pre_hooks: list[PreHook] | None = None,
        post_hooks: list[PostHook] | None = None,
    ) -> None:
        self._pre_hooks: list[PreHook] = list(pre_hooks or [])
        self._post_hooks: list[PostHook] = list(post_hooks or [])

    def register_pre(self, hook: PreHook) -> None:
        self._pre_hooks.append(hook)

    def register_post(self, hook: PostHook) -> None:
        self._post_hooks.append(hook)

    async def apply_pre(self, request: CompletionRequest) -> CompletionRequest:
        """Run all pre-hooks in order, threading the request through each."""
        for hook in self._pre_hooks:
            request = await hook(request)
        return request

    async def apply_post(self, response: LLMResponse) -> LLMResponse:
        """Run all post-hooks in order, threading the response through each."""
        for hook in self._post_hooks:
            response = await hook(response)
        return response
