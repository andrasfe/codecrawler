"""Test that all public symbols from cobol_penetrator.llm_providers are importable."""

import pytest


class TestProtocolImports:
    """Verify core protocol types are importable and functional."""

    def test_message_importable(self) -> None:
        from cobol_penetrator.llm_providers import Message

        assert Message is not None

    def test_completion_response_importable(self) -> None:
        from cobol_penetrator.llm_providers import CompletionResponse

        assert CompletionResponse is not None

    def test_llm_provider_importable(self) -> None:
        from cobol_penetrator.llm_providers import LLMProvider

        assert LLMProvider is not None


class TestFactoryImports:
    """Verify factory functions are importable."""

    def test_create_provider_importable(self) -> None:
        from cobol_penetrator.llm_providers import create_provider

        assert callable(create_provider)

    def test_get_provider_from_env_importable(self) -> None:
        from cobol_penetrator.llm_providers import get_provider_from_env

        assert callable(get_provider_from_env)

    def test_register_provider_importable(self) -> None:
        from cobol_penetrator.llm_providers import register_provider

        assert callable(register_provider)

    def test_get_available_providers_importable(self) -> None:
        from cobol_penetrator.llm_providers import get_available_providers

        assert callable(get_available_providers)


class TestConfigImports:
    """Verify configuration classes are importable."""

    def test_provider_config_importable(self) -> None:
        from cobol_penetrator.llm_providers import ProviderConfig

        assert ProviderConfig is not None

    def test_openrouter_config_importable(self) -> None:
        from cobol_penetrator.llm_providers import OpenRouterConfig

        assert OpenRouterConfig is not None

    def test_anthropic_config_importable(self) -> None:
        from cobol_penetrator.llm_providers import AnthropicConfig

        assert AnthropicConfig is not None

    def test_openai_config_importable(self) -> None:
        from cobol_penetrator.llm_providers import OpenAIConfig

        assert OpenAIConfig is not None


class TestProviderImports:
    """Verify provider implementations are importable."""

    def test_openrouter_provider_importable(self) -> None:
        from cobol_penetrator.llm_providers import OpenRouterProvider

        assert OpenRouterProvider is not None

    def test_anthropic_provider_importable(self) -> None:
        from cobol_penetrator.llm_providers import AnthropicProvider
        # May be None if anthropic SDK is not installed, but the import
        # itself should not raise.
        # We just check it was imported without error.

    def test_openai_provider_importable(self) -> None:
        from cobol_penetrator.llm_providers import OpenAIProvider
        # May be None if openai SDK is not installed, but the import
        # itself should not raise.


class TestMessageDataclass:
    """Verify Message dataclass works correctly."""

    def test_create_user_message(self) -> None:
        from cobol_penetrator.llm_providers import Message

        msg = Message(role="user", content="Hello!")
        assert msg.role == "user"
        assert msg.content == "Hello!"

    def test_create_system_message(self) -> None:
        from cobol_penetrator.llm_providers import Message

        msg = Message(role="system", content="You are helpful.")
        assert msg.role == "system"
        assert msg.content == "You are helpful."

    def test_create_assistant_message(self) -> None:
        from cobol_penetrator.llm_providers import Message

        msg = Message(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_invalid_role_raises(self) -> None:
        from cobol_penetrator.llm_providers import Message

        with pytest.raises(ValueError, match="Invalid role"):
            Message(role="invalid", content="test")

    def test_message_is_frozen(self) -> None:
        from cobol_penetrator.llm_providers import Message

        msg = Message(role="user", content="Hello!")
        with pytest.raises(AttributeError):
            msg.role = "system"  # type: ignore[misc]


class TestCompletionResponseDataclass:
    """Verify CompletionResponse dataclass works correctly."""

    def test_create_response(self) -> None:
        from cobol_penetrator.llm_providers import CompletionResponse

        resp = CompletionResponse(
            content="Hello!",
            model="test-model",
            tokens_used=42,
        )
        assert resp.content == "Hello!"
        assert resp.model == "test-model"
        assert resp.tokens_used == 42
        assert resp.raw_response is None

    def test_has_content_true(self) -> None:
        from cobol_penetrator.llm_providers import CompletionResponse

        resp = CompletionResponse(content="Hello!", model="m", tokens_used=0)
        assert resp.has_content is True

    def test_has_content_false_empty(self) -> None:
        from cobol_penetrator.llm_providers import CompletionResponse

        resp = CompletionResponse(content="", model="m", tokens_used=0)
        assert resp.has_content is False

    def test_has_content_false_whitespace(self) -> None:
        from cobol_penetrator.llm_providers import CompletionResponse

        resp = CompletionResponse(content="   ", model="m", tokens_used=0)
        assert resp.has_content is False

    def test_raw_response_stored(self) -> None:
        from cobol_penetrator.llm_providers import CompletionResponse

        raw = {"chunks": 5, "elapsed": 1.2}
        resp = CompletionResponse(
            content="Hi", model="m", tokens_used=10, raw_response=raw
        )
        assert resp.raw_response == raw


class TestAllExports:
    """Verify __all__ exports are complete and consistent."""

    def test_all_symbols_importable(self) -> None:
        import cobol_penetrator.llm_providers as llm_mod

        for name in llm_mod.__all__:
            assert hasattr(llm_mod, name), f"Missing export: {name}"

    def test_version_defined(self) -> None:
        import cobol_penetrator.llm_providers as llm_mod

        assert hasattr(llm_mod, "__version__")
        assert isinstance(llm_mod.__version__, str)
