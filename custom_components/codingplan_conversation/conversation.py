"""CodingPlan conversation entity."""

from __future__ import annotations

import json
import logging
from typing import Any

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr, intent, llm
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import ulid

from .const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 1.0

# Simple in-memory conversation history storage
_conversation_history: dict[str, list[dict]] = {}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CodingPlan conversation entity."""
    client: AsyncOpenAI = entry.runtime_data

    await async_add_entities(
        [
            CodingPlanConversationEntity(
                hass=hass,
                entry=entry,
                client=client,
            )
        ]
    )


class CodingPlanConversationEntity(conversation.ConversationEntity):
    """CodingPlan conversation agent."""

    _attr_has_entity_name = True
    _attr_name = "CodingPlan Conversation"
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AsyncOpenAI,
    ) -> None:
        """Initialize the agent."""
        self.hass = hass
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_conversation"
        self.entity_id = f"conversation.codingplan_{entry.entry_id[:8]}"
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="CodingPlan",
            manufacturer="Alibaba Cloud",
            model=entry.data.get(CONF_CHAT_MODEL, "CodingPlan"),
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        _LOGGER.debug("CodingPlan entity initialized: %s", self.entity_id)

    @property
    def supported_features(self) -> int:
        """Return supported features."""
        return conversation.ConversationEntityFeature.CONTROL

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        global _conversation_history

        if user_input.conversation_id:
            conversation_id = user_input.conversation_id
            messages = _conversation_history.get(conversation_id, [])
        else:
            conversation_id = ulid.ulid_now()
            messages = []

        # Add system message if starting new conversation
        if not messages:
            messages.append({
                "role": "system",
                "content": "You are a helpful assistant controlling Home Assistant.",
            })

        # Add user message to history
        messages.append({
            "role": "user",
            "content": user_input.text,
        })

        # Get LLM API if configured
        llm_api: llm.API | None = None
        if CONF_LLM_HASS_API in self._entry.options:
            try:
                llm_api = llm.async_get_api(
                    self.hass, self._entry.options[CONF_LLM_HASS_API]
                )
            except HomeAssistantError as err:
                _LOGGER.error("Error getting LLM API: %s", err)

        tools: list[dict[str, Any]] | None = None
        if llm_api:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in llm_api.async_get_tools()
            ]

        try:
            response = await self._client.chat.completions.create(
                model=self._entry.data[CONF_CHAT_MODEL],
                messages=messages,
                tools=tools,
                max_tokens=self._entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                temperature=self._entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                top_p=self._entry.data.get(CONF_TOP_P, DEFAULT_TOP_P),
                user=conversation_id,
            )
        except openai.AuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except openai.OpenAIError as err:
            raise HomeAssistantError(f"Error communicating with CodingPlan: {err}") from err

        choice: Choice = response.choices[0]
        message: ChatCompletionMessage = choice.message

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
            }
        )

        # Handle tool calls if any
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if llm_api:
                    try:
                        tool_result = await llm_api.async_call_tool(tool_name, tool_args)
                    except Exception as err:
                        tool_result = {"error": str(err)}

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(tool_result),
                        }
                    )

            # Get final response after tool calls
            try:
                response = await self._client.chat.completions.create(
                    model=self._entry.data[CONF_CHAT_MODEL],
                    messages=messages,
                    max_tokens=self._entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                    temperature=self._entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                    top_p=self._entry.data.get(CONF_TOP_P, DEFAULT_TOP_P),
                    user=conversation_id,
                )
            except openai.OpenAIError as err:
                raise HomeAssistantError(f"Error communicating with CodingPlan: {err}") from err

            choice = response.choices[0]
            message = choice.message

            messages.append({
                "role": "assistant",
                "content": message.content,
            })

        # Store updated history
        _conversation_history[conversation_id] = messages

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(message.content or "")

        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=conversation_id,
        )
