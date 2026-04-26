"""Config flow for CodingPlan Conversation integration."""

from __future__ import annotations

import logging
from typing import Any

import openai
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_BASE_URL,
    DEFAULT_CHAT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# CodingPlan supported models (from official documentation)
PRESET_MODELS = [
    # 推荐模型
    "qwen3.6-plus",
    "kimi-k2.5",
    "glm-5",
    "minimax-m2.5",
    # 更多模型
    "qwen3.5-plus",
    "qwen3-max-2026-01-23",
    "qwen3-coder-next",
    "qwen3-coder-plus",
    "glm-4.7",
    # 其他兼容模型
    "qwen3.6-max-preview",
    "qwen3.6-flash",
    "qwen3-vl-plus",
    "qwen3-coder",
    "qwen3-max",
    "qwen3.5-omni-plus",
    "wan2.6-t2v",
    "wan2.7-image",
    "wan2.7-video",
    "wan2.6-i2v",
]


async def validate_api_connection(
    hass: HomeAssistant,
    base_url: str,
    api_key: str,
) -> bool:
    """Validate the API connection with a simple request."""
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=get_async_client(hass),
    )
    # Try a simple chat completion to validate
    try:
        response = await client.chat.completions.create(
            model="qwen3.6-plus",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            timeout=10.0,
        )
        return True
    except openai.NotFoundError:
        # Model not found, but API is valid - that's OK
        return True
    except Exception:
        raise


class CodingPlanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CodingPlan Conversation."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.base_url: str = DEFAULT_BASE_URL
        self.api_key: str = ""
        self.options: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.base_url = user_input[CONF_BASE_URL].rstrip("/")
            self.api_key = user_input[CONF_API_KEY]

            try:
                await validate_api_connection(
                    self.hass, self.base_url, self.api_key
                )
            except openai.AuthenticationError:
                errors["base"] = "invalid_auth"
            except openai.APIConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during validation")
                errors["base"] = "unknown"
            else:
                return await self.async_step_model()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Required(CONF_API_KEY): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "url": "https://coding.dashscope.aliyuncs.com/v1",
            },
        )

    async def async_step_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle model selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.options[CONF_CHAT_MODEL] = user_input[CONF_CHAT_MODEL]
            self.options[CONF_MAX_TOKENS] = user_input[CONF_MAX_TOKENS]
            self.options[CONF_TEMPERATURE] = user_input[CONF_TEMPERATURE]
            self.options[CONF_TOP_P] = user_input[CONF_TOP_P]
            self.options[CONF_PROMPT] = user_input.get(CONF_PROMPT, "")
            return await self.async_step_llm()

        # Use preset models with dropdown selector
        data_schema = vol.Schema(
            {
                vol.Required(CONF_CHAT_MODEL, default=DEFAULT_CHAT_MODEL): vol.In(
                    {model: model for model in PRESET_MODELS}
                ),
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(
                    int, vol.Range(min=1, max=8192)
                ),
                vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
                    vol.Coerce(float), vol.Range(min=0.0, max=2.0)
                ),
                vol.Optional(CONF_TOP_P, default=DEFAULT_TOP_P): vol.All(
                    vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                ),
                vol.Optional(CONF_PROMPT, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="model",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_llm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle LLM API selection step."""
        if user_input is not None:
            # Save the configuration
            return self.async_create_entry(
                title="CodingPlan",
                data={
                    CONF_BASE_URL: self.base_url,
                    CONF_API_KEY: self.api_key,
                    CONF_CHAT_MODEL: self.options[CONF_CHAT_MODEL],
                    CONF_MAX_TOKENS: self.options[CONF_MAX_TOKENS],
                    CONF_TEMPERATURE: self.options[CONF_TEMPERATURE],
                    CONF_TOP_P: self.options[CONF_TOP_P],
                    CONF_PROMPT: self.options.get(CONF_PROMPT, ""),
                },
                options={
                    CONF_LLM_HASS_API: user_input.get(CONF_LLM_HASS_API, llm.LLM_API_ASSIST),
                },
            )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_LLM_HASS_API, default=llm.LLM_API_ASSIST): SelectSelector(
                    SelectSelectorConfig(
                        options=[llm.LLM_API_ASSIST],
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="llm_hass_api",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="llm",
            data_schema=data_schema,
            description_placeholders={
                "docs_url": "https://www.home-assistant.io/integrations/conversation/#control-home-assistant",
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Perform reauth upon API authentication error."""
        return await self.async_step_user()
