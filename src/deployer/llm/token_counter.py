"""Token counting using tiktoken for pre-request estimation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import tiktoken

if TYPE_CHECKING:
    from deployer.llm.providers.base import Message

# Fallback encoding for unknown models
_FALLBACK_ENCODING = "cl100k_base"

# Tokens added per message by the chat format overhead
_TOKENS_PER_MESSAGE = 3  # <|start|>{role}\n{content}<|end|>
_TOKENS_PER_NAME = 1  # if "name" key present in message
_REPLY_PRIMING = 3  # assistant reply priming tokens


def _get_encoding(model: str) -> tiktoken.Encoding:
    """Return tiktoken encoding for a model, falling back to cl100k_base."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding(_FALLBACK_ENCODING)


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count the number of tokens in a plain text string."""
    enc = _get_encoding(model)
    return len(enc.encode(text, disallowed_special=()))


def count_message_tokens(messages: list[Message], model: str = "gpt-4o-mini") -> int:
    """Estimate input token count for a list of chat messages.

    Accounts for per-message formatting overhead and the assistant reply priming
    tokens that OpenAI's chat format adds automatically.
    """
    enc = _get_encoding(model)
    num_tokens = _REPLY_PRIMING
    for message in messages:
        num_tokens += _TOKENS_PER_MESSAGE
        num_tokens += len(enc.encode(message.role, disallowed_special=()))
        num_tokens += len(enc.encode(message.content, disallowed_special=()))
    return num_tokens
