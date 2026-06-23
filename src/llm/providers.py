"""LLM provider adapters for different vendors."""

import os
from abc import ABC, abstractmethod
from typing import Optional

import anthropic
import openai


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat request and return the assistant's response text."""
        ...


class OpenAIProvider(BaseProvider):
    """OpenAI API provider (also compatible with OpenAI-compatible APIs)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        env_var: str = "OPENAI_API_KEY",
    ):
        self.api_key = api_key or os.getenv(env_var, "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self._client: Optional[openai.AsyncOpenAI] = None

    @property
    def client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def chat(
        self,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._client: Optional[anthropic.AsyncAnthropic] = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def chat(
        self,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Extract text from content blocks
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)


class LocalProvider(OpenAIProvider):
    """Local model provider using OpenAI-compatible API (e.g., Ollama, vLLM)."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__(
            base_url=base_url or os.getenv("LOCAL_MODEL_URL", "http://localhost:11434/v1"),
            api_key=api_key or "local",
        )
