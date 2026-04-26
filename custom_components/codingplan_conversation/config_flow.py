"""Config flow for CodingPlan Conversation integration."""

from __future__ import annotations

import logging
from typing import Any

import openai
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_REASONING_EFFORT,
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

async def get_available_models(
    hass: HomeAssistant,
    base_url: str,
    api_key: str,
) -> list[str]:
    """Fetch available models from CodingPlan API."""
    try:
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=get_async_client(hass),
        )
        response = await client.models.list(timeout=30.0)
        # Filter to chat completion models
        models = [
            model.id for model in response.data
            if any(x in model.id.lower() for x in ["gpt", "turbo", "claude", "qwen", "codingplan"])
        ]
        return sorted(models) if models else [DEFAULT_CHAT_MODEL]
    except Exception as err:
        _LOGGER.warning("Failed to fetch models: %s", err)
        return [DEFAULT_CHAT_MODEL]


async def validate_api_connection(
    hass: HomeAssistant,
    base_url: str,
    api_key: str,
) -> bool:
    """Validate the API connection."""
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=get_async_client(hass),
    )
    await client.models.list(timeout=10.0)
    return True


class CodingPlanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CodingPlan Conversation."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.base_url: str = DEFAULT_BASE_URL
        self.api_key: str = ""
        self.available_models: list[str] = []

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
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Fetch available models
                self.available_models = await get_available_models(
                    self.hass, self.base_url, self.api_key
                )
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
                "url": "https://codingplan.aliyuncs.com",
            },
        )

    async def async_step_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle model selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Save the configuration
            return self.async_create_entry(
                title="CodingPlan",
                data={
                    CONF_BASE_URL: self.base_url,
                    CONF_API_KEY: self.api_key,
                    CONF_CHAT_MODEL: user_input[CONF_CHAT_MODEL],
                    CONF_MAX_TOKENS: user_input[CONF_MAX_TOKENS],
                    CONF_TEMPERATURE: user_input[CONF_TEMPERATURE],
                    CONF_TOP_P: user_input[CONF_TOP_P],
                },
            )

        # Build model selector
        model_options = {model: model for model in self.available_models}
        default_model = (
            self.available_models[0] if self.available_models else DEFAULT_CHAT_MODEL
        )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CHAT_MODEL, default=default_model): vol.In(
                    model_options
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
            }
        )

        return self.async_show_form(
            step_id="model",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Perform reauth upon API authentication error."""
        return await self.async_step_user()
