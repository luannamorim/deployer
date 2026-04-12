"""Unit tests for the tiktoken-based token counter."""

from __future__ import annotations

from deployer.llm.providers.base import Message
from deployer.llm.token_counter import count_message_tokens, count_tokens


class TestCountTokens:
    def test_empty_string(self) -> None:
        assert count_tokens("") == 0

    def test_single_word(self) -> None:
        # "hello" is one token in cl100k_base / o200k_base
        assert count_tokens("hello") == 1

    def test_known_token_count(self) -> None:
        # "Hello world!" → 3 tokens for gpt-4o-mini (cl100k_base)
        assert count_tokens("Hello world!", model="gpt-4o-mini") == 3

    def test_longer_text(self) -> None:
        text = "The quick brown fox jumps over the lazy dog"
        token_count = count_tokens(text)
        # Should be between 8–12 tokens for this phrase
        assert 8 <= token_count <= 12

    def test_unknown_model_falls_back(self) -> None:
        # Unknown models fall back to cl100k_base — should not raise
        count = count_tokens("hello world", model="unknown-model-xyz")
        assert count > 0

    def test_different_models_may_differ(self) -> None:
        text = "Testing tokenization across models."
        # Both should return positive values
        assert count_tokens(text, model="gpt-4o-mini") > 0
        assert count_tokens(text, model="gpt-4") > 0


class TestCountMessageTokens:
    def test_single_user_message(self) -> None:
        messages = [Message(role="user", content="Hello!")]
        tokens = count_message_tokens(messages)
        assert tokens > 0

    def test_includes_overhead(self) -> None:
        # Message tokens should be more than just the content token count
        messages = [Message(role="user", content="Hello")]
        message_tokens = count_message_tokens(messages)
        content_tokens = count_tokens("Hello")
        assert message_tokens > content_tokens

    def test_more_messages_means_more_tokens(self) -> None:
        one_msg = [Message(role="user", content="Hi")]
        two_msgs = [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello!"),
        ]
        assert count_message_tokens(two_msgs) > count_message_tokens(one_msg)

    def test_system_message_counted(self) -> None:
        no_system = [Message(role="user", content="Hi")]
        with_system = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hi"),
        ]
        assert count_message_tokens(with_system) > count_message_tokens(no_system)

    def test_empty_messages(self) -> None:
        # Should return the reply priming tokens only
        tokens = count_message_tokens([])
        assert tokens == 3  # _REPLY_PRIMING constant

    def test_model_parameter_accepted(self) -> None:
        messages = [Message(role="user", content="test")]
        count = count_message_tokens(messages, model="gpt-4")
        assert count > 0
