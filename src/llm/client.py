"""Unified LLM client with multi-provider support and structured output."""

from typing import Optional, TypeVar

from pydantic import BaseModel

from src.llm.providers import AnthropicProvider, BaseProvider, LocalProvider, OpenAIProvider
from src.llm.structured import build_json_schema_hint, parse_structured_output
from src.utils.config import load_yaml
from src.utils.logging import logger

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Unified LLM client that routes to different providers based on task config.

    Usage:
        client = LLMClient()
        result = await client.chat("simulation", system_prompt, user_prompt)
        parsed = await client.chat_json("simulation", system_prompt, user_prompt, MySchema)
    """

    def __init__(self, config_path: str = "models.yaml"):
        self._config = load_yaml(config_path)
        self._providers: dict[str, BaseProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize provider instances from config."""
        providers_cfg = self._config.get("providers", {})

        # Always create default providers
        self._providers["openai"] = OpenAIProvider(
            base_url=providers_cfg.get("openai", {}).get("base_url"),
        )
        self._providers["anthropic"] = AnthropicProvider()
        self._providers["deepseek"] = OpenAIProvider(
            base_url=providers_cfg.get("deepseek", {}).get(
                "base_url", "https://api.deepseek.com/v1"
            ),
            api_key=None,
            env_var="DEEPSEEK_API_KEY",
        )

        # Zhipu AI (智谱) — GLM series, OpenAI-compatible API
        zhipu_cfg = providers_cfg.get("zhipu", {})
        self._providers["zhipu"] = OpenAIProvider(
            base_url=zhipu_cfg.get(
                "base_url", "https://open.bigmodel.cn/api/paas/v4/"
            ),
            api_key=None,
            env_var="ZHIPU_API_KEY",
        )

        # Local provider
        local_cfg = providers_cfg.get("local", {})
        if local_cfg.get("base_url"):
            self._providers["local"] = LocalProvider(
                base_url=local_cfg["base_url"],
                api_key=local_cfg.get("api_key", "local"),
            )

    def _get_task_config(self, task_name: str) -> dict:
        """Get model configuration for a specific task."""
        models_cfg = self._config.get("models", {})
        if task_name not in models_cfg:
            # Fallback to simulation config
            logger.warning("Task config not found, using default", task=task_name)
            return {
                "provider": "openai",
                "model_name": "gpt-4o-mini",
                "max_tokens": 2000,
                "temperature": 0.7,
            }
        return models_cfg[task_name]

    def _get_provider(self, provider_name: str) -> BaseProvider:
        """Get a provider instance by name."""
        if provider_name not in self._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        return self._providers[provider_name]

    async def chat(
        self,
        task_name: str,
        system: str,
        user: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a chat request using the task's configured model.

        Args:
            task_name: Name of the task (maps to config/models.yaml)
            system: System prompt
            user: User prompt
            max_tokens: Override max tokens (uses config if None)
            temperature: Override temperature (uses config if None)

        Returns:
            Assistant response text
        """
        task_cfg = self._get_task_config(task_name)
        provider = self._get_provider(task_cfg["provider"])

        return await provider.chat(
            model=task_cfg["model_name"],
            system=system,
            user=user,
            max_tokens=max_tokens or task_cfg.get("max_tokens", 2000),
            temperature=temperature if temperature is not None else task_cfg.get("temperature", 0.7),
        )

    async def chat_json(
        self,
        task_name: str,
        system: str,
        user: str,
        schema: type[T],
        max_retries: int = 2,
    ) -> T:
        """Send a chat request and parse the response as structured JSON.

        Automatically appends JSON schema hint to the system prompt.
        Retries up to max_retries times if parsing fails.

        Args:
            task_name: Name of the task
            system: System prompt
            user: User prompt
            schema: Pydantic model to parse response into
            max_retries: Max retry attempts on parse failure

        Returns:
            Parsed Pydantic model instance
        """
        # Append JSON schema hint to system prompt
        enhanced_system = system + build_json_schema_hint(schema)

        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                response = await self.chat(task_name, enhanced_system, user)
                return parse_structured_output(response, schema)
            except (ValueError, Exception) as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        "Structured output parse failed, retrying",
                        task=task_name,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    # Append error feedback for retry
                    user = user + f"\n\n[上次输出格式错误: {str(e)[:200]}，请严格按JSON格式输出]"

        raise ValueError(
            f"Failed to get valid structured output after {max_retries + 1} attempts: {last_error}"
        )
