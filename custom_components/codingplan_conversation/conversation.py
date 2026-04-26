"""CodingPlan conversation entity."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr, intent, llm
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import ulid

from .const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10


def _format_tool(tool: llm.Tool) -> dict[str, Any]:
    """Format tool specification for OpenAI API."""
    unsupported_keys = {"oneOf", "anyOf", "allOf", "enum", "not"}
    schema = convert(tool.parameters)
    if unsupported_keys.intersection(schema):
        schema = {k: v for k, v in schema.items() if k not in unsupported_keys}

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "parameters": schema,
            "description": tool.description,
        },
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CodingPlan conversation entity."""
    _LOGGER.debug("Setting up CodingPlan conversation entity for entry %s", entry.entry_id)

    async_add_entities([CodingPlanConversationEntity(hass, entry)])


class CodingPlanConversationEntity(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    """CodingPlan conversation agent entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self._entry = entry
        self._client: AsyncOpenAI = entry.runtime_data
        self._attr_unique_id = entry.entry_id

        # Set supported features based on LLM API config
        if CONF_LLM_HASS_API in entry.options:
            self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL

        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="CodingPlan",
            manufacturer="Alibaba Cloud",
            model=entry.data.get(CONF_CHAT_MODEL, "CodingPlan"),
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._entry, self)
        _LOGGER.info("CodingPlan conversation entity added successfully")

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self._entry)
        await super().async_will_remove_from_hass()

    def _get_all_states_tool(self) -> dict[str, Any]:
        """Create a tool to get all entity states."""
        return {
            "type": "function",
            "function": {
                "name": "get_all_states",
                "description": "Get the current state of all Home Assistant entities including sensors, switches, lights, climate, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_filter": {
                            "type": "string",
                            "description": "Optional filter (e.g., 'sensor', 'climate', 'light')",
                        }
                    },
                    "required": ["entity_filter"],
                },
            },
        }

    def _get_state_tool(self) -> dict[str, Any]:
        """Create a tool to get a specific entity state."""
        return {
            "type": "function",
            "function": {
                "name": "get_state",
                "description": "Get the current state of a specific entity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID (e.g., sensor.living_room_temperature)",
                        }
                    },
                    "required": ["entity_id"],
                },
            },
        }

    def _call_service_tool(self) -> dict[str, Any]:
        """Create a tool to call Home Assistant services."""
        return {
            "type": "function",
            "function": {
                "name": "call_service",
                "description": "Call a Home Assistant service to control devices",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Service domain"},
                        "service": {"type": "string", "description": "Service name"},
                        "entity_id": {"type": "string", "description": "Entity ID"},
                        "service_data": {"type": "object", "description": "Service data"},
                    },
                    "required": ["domain", "service"],
                },
            },
        }

    async def _handle_tool_call(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Handle a tool call."""
        if tool_name == "get_all_states":
            entity_filter = tool_args.get("entity_filter", "")
            states = []
            for state in self.hass.states.async_all():
                if not entity_filter or state.domain == entity_filter:
                    states.append({
                        "entity_id": state.entity_id,
                        "state": state.state,
                        "attributes": dict(state.attributes),
                    })
            return {"entities": states[:50]}

        elif tool_name == "get_state":
            entity_id = tool_args.get("entity_id")
            state = self.hass.states.get(entity_id)
            if state:
                return {
                    "entity_id": state.entity_id,
                    "state": state.state,
                    "attributes": dict(state.attributes),
                }
            return {"error": f"Entity {entity_id} not found"}

        elif tool_name == "call_service":
            domain = tool_args.get("domain")
            service = tool_args.get("service")
            entity_id = tool_args.get("entity_id")
            service_data = tool_args.get("service_data", {})
            if entity_id:
                service_data["entity_id"] = entity_id
            try:
                await self.hass.services.async_call(domain, service, service_data, blocking=True)
                return {"success": True}
            except Exception as err:
                return {"error": str(err)}

        return {"error": f"Unknown tool: {tool_name}"}

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        _LOGGER.debug("Processing: %s", user_input.text)

        conversation_id = user_input.conversation_id or ulid.ulid_now()
        enable_ha_control = CONF_LLM_HASS_API in self._entry.options

        llm_api: llm.APIInstance | None = None
        if enable_ha_control:
            try:
                llm_context = llm.LLMContext(
                    platform=DOMAIN,
                    context=user_input.context,
                    language=user_input.language,
                    assistant="conversation",
                    device_id=user_input.device_id,
                )
                llm_api = await llm.async_get_api(
                    self.hass,
                    self._entry.options[CONF_LLM_HASS_API],
                    llm_context,
                )
            except HomeAssistantError as err:
                _LOGGER.error("Error getting LLM API: %s", err)

        messages: list[dict[str, Any]] = []
        custom_prompt = self._entry.data.get(CONF_PROMPT, "")

        if llm_api:
            system_prompt = llm_api.api_prompt
            if custom_prompt:
                system_prompt += f"\n\nAdditional instructions: {custom_prompt}"
        else:
            system_prompt = custom_prompt or "You are a helpful assistant."

        if enable_ha_control:
            system_prompt += "\n\nYou have FULL ACCESS to all Home Assistant entities. Use tools to get information."

        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input.text})

        tools: list[dict[str, Any]] = []
        if enable_ha_control:
            tools.extend([self._get_all_states_tool(), self._get_state_tool(), self._call_service_tool()])
            if llm_api:
                for tool in llm_api.tools:
                    tools.append(_format_tool(tool))

        try:
            response = await self._client.chat.completions.create(
                model=self._entry.data[CONF_CHAT_MODEL],
                messages=messages,
                tools=tools if tools else None,
                max_tokens=self._entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                temperature=self._entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                top_p=self._entry.data.get(CONF_TOP_P, DEFAULT_TOP_P),
            )
        except openai.AuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except openai.OpenAIError as err:
            raise HomeAssistantError(f"Error: {err}") from err

        message = response.choices[0].message
        iteration = 0

        while message.tool_calls and iteration < MAX_TOOL_ITERATIONS:
            iteration += 1
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                args = json.loads(tc.function.arguments)
                _LOGGER.debug("Tool: %s, args: %s", tc.function.name, args)

                if tc.function.name in ["get_all_states", "get_state", "call_service"]:
                    result = await self._handle_tool_call(tc.function.name, args)
                elif llm_api:
                    try:
                        result = await llm_api.async_call_tool(llm.ToolInput(tc.function.name, args))
                    except Exception as err:
                        result = {"error": str(err)}
                else:
                    result = {"error": "Unknown tool"}

                messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": json.dumps(result)})

            try:
                response = await self._client.chat.completions.create(
                    model=self._entry.data[CONF_CHAT_MODEL],
                    messages=messages,
                    tools=tools if tools else None,
                    max_tokens=self._entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                )
            except openai.OpenAIError as err:
                raise HomeAssistantError(f"Error: {err}") from err

            message = response.choices[0].message

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(message.content or "")
        return conversation.ConversationResult(response=intent_response, conversation_id=conversation_id)