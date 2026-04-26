"""CodingPlan conversation entity."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import intent, llm
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CodingPlan conversation agent."""
    _LOGGER.debug("Setting up CodingPlan conversation agent for entry %s", entry.entry_id)

    agent = CodingPlanAgent(hass, entry)

    # Register the agent with Home Assistant
    conversation.async_set_agent(hass, entry, agent)

    _LOGGER.info("CodingPlan conversation agent registered successfully")


class CodingPlanAgent(conversation.AbstractConversationAgent):
    """CodingPlan conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.client: AsyncOpenAI = entry.runtime_data

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    @property
    def id(self) -> str:
        """Return the agent id."""
        return self.entry.entry_id

    def _get_all_states_tool(self) -> dict[str, Any]:
        """Create a tool to get all entity states."""
        return {
            "type": "function",
            "function": {
                "name": "get_all_states",
                "description": "Get the current state of all Home Assistant entities including sensors, switches, lights, climate, etc. Use this to answer questions about home status, temperature, air quality, device states, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_filter": {
                            "type": "string",
                            "description": "Optional filter to get specific entity types (e.g., 'sensor', 'climate', 'light', 'switch', 'binary_sensor'). Use empty string for all entities.",
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
                "description": "Get the current state of a specific Home Assistant entity by entity_id",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The entity_id to get state for (e.g., sensor.living_room_temperature, climate.bedroom_ac)",
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
                "description": "Call a Home Assistant service to control devices (turn on/off lights, set climate temperature, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Service domain (e.g., light, switch, climate, media_player)",
                        },
                        "service": {
                            "type": "string",
                            "description": "Service name (e.g., turn_on, turn_off, set_temperature, media_play)",
                        },
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID to control (optional for some services)",
                        },
                        "service_data": {
                            "type": "object",
                            "description": "Additional service data/parameters",
                        },
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
            return {"entities": states[:50]}  # Limit to 50 entities

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
                await self.hass.services.async_call(
                    domain, service, service_data, blocking=True
                )
                return {"success": True, "message": f"Called {domain}.{service}"}
            except Exception as err:
                return {"success": False, "error": str(err)}

        return {"error": f"Unknown tool: {tool_name}"}

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        _LOGGER.debug("Processing user input: %s", user_input.text)

        # Get conversation id or create new one
        if user_input.conversation_id:
            conversation_id = user_input.conversation_id
        else:
            conversation_id = ulid.ulid_now()

        # Check if HA control is enabled
        enable_ha_control = CONF_LLM_HASS_API in self.entry.options

        # Get LLM API if configured (for additional tools)
        llm_api: llm.APIInstance | None = None
        if enable_ha_control:
            try:
                llm_api = await llm.async_get_api(
                    self.hass,
                    self.entry.options[CONF_LLM_HASS_API],
                    llm.LLMContext(
                        platform=DOMAIN,
                        context=user_input.context,
                        user_prompt=user_input.text,
                        language=user_input.language,
                        assistant="conversation",
                        device_id=user_input.device_id,
                    ),
                )
            except HomeAssistantError as err:
                _LOGGER.error("Error getting LLM API: %s", err)

        # Build messages
        messages: list[dict[str, Any]] = []

        # Get system prompt
        custom_prompt = self.entry.data.get(CONF_PROMPT, "")
        if llm_api:
            system_prompt = llm_api.api_prompt
            if custom_prompt:
                system_prompt = f"{system_prompt}\n\nAdditional instructions: {custom_prompt}"
        elif custom_prompt:
            system_prompt = custom_prompt
        else:
            system_prompt = "You are a helpful assistant."

        # Add default system prompt for full access
        if enable_ha_control:
            system_prompt += (
                "\n\nYou have FULL ACCESS to all Home Assistant entities. "
                "You can read states of any sensor, switch, light, climate device, etc. "
                "You can also control devices by calling services. "
                "Always use the available tools to get accurate information before answering."
            )

        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input.text})

        # Prepare tools - always include our custom tools for full access
        tools: list[dict[str, Any]] = []
        if enable_ha_control:
            tools.append(self._get_all_states_tool())
            tools.append(self._get_state_tool())
            tools.append(self._call_service_tool())

            # Also add LLM API tools if available
            if llm_api:
                for tool in llm_api.async_get_tools():
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        },
                    })

            _LOGGER.debug("Available tools: %s", [t["function"]["name"] for t in tools])

        # Call API
        try:
            response = await self.client.chat.completions.create(
                model=self.entry.data[CONF_CHAT_MODEL],
                messages=messages,
                tools=tools if tools else None,
                max_tokens=self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                temperature=self.entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                top_p=self.entry.data.get(CONF_TOP_P, DEFAULT_TOP_P),
                user=conversation_id,
            )
        except openai.AuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except openai.OpenAIError as err:
            raise HomeAssistantError(f"Error communicating with CodingPlan: {err}") from err

        choice: Choice = response.choices[0]
        message: ChatCompletionMessage = choice.message

        # Handle tool calls
        max_iterations = MAX_TOOL_ITERATIONS
        current_iteration = 0

        while message.tool_calls and current_iteration < max_iterations:
            current_iteration += 1

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # Process each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                _LOGGER.debug("Calling tool: %s with args: %s", tool_name, tool_args)

                # First try our custom tools
                if tool_name in ["get_all_states", "get_state", "call_service"]:
                    tool_result = await self._handle_tool_call(tool_name, tool_args)
                elif llm_api:
                    # Try LLM API tool
                    try:
                        tool_result = await llm_api.async_call_tool(tool_name, tool_args)
                    except Exception as err:
                        tool_result = {"error": str(err)}
                        _LOGGER.error("Tool call failed: %s", err)
                else:
                    tool_result = {"error": f"Unknown tool: {tool_name}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result),
                })

            # Get next response
            try:
                response = await self.client.chat.completions.create(
                    model=self.entry.data[CONF_CHAT_MODEL],
                    messages=messages,
                    tools=tools if tools else None,
                    max_tokens=self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                    temperature=self.entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                    top_p=self.entry.data.get(CONF_TOP_P, DEFAULT_TOP_P),
                    user=conversation_id,
                )
            except openai.OpenAIError as err:
                raise HomeAssistantError(f"Error communicating with CodingPlan: {err}") from err

            message = response.choices[0].message

        # Build response
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(message.content or "")

        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=conversation_id,
        )
