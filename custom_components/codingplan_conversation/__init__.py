"""The CodingPlan Conversation integration."""

from __future__ import annotations

import openai

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.typing import ConfigType

from .const import CONF_BASE_URL, DOMAIN

PLATFORMS = (Platform.CONVERSATION,)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type CodingPlanConfigEntry = ConfigEntry[openai.AsyncOpenAI]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up CodingPlan Conversation."""
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: CodingPlanConfigEntry
) -> bool:
    """Set up CodingPlan from a config entry."""
    base_url = entry.data[CONF_BASE_URL]
    api_key = entry.data[CONF_API_KEY]

    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=get_async_client(hass),
    )

    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: CodingPlanConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant, entry: CodingPlanConfigEntry
) -> None:
    """Reload the config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
