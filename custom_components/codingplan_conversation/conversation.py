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
from homeassistant.helpers import device_registry as dr, intent, llm
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import ulid

from .const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
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

        # Get LLM API if configured
        llm_api: llm.APIInstance | None = None
        if CONF_LLM_HASS_API in self.entry.options:
            try:
                llm_api = await llm.async_get_api(
                    self.hass,
                    self.entry.options[CONF_LLM_HASS_API],
                    llm.LLMContext(
                        platform=DOMAIN,
                        context=user_input.context,
                        user_prompt=user_input.text,
                        language=user_input.language,
                        assistant=conversation.CONVERSATION_ASSISTANT,
                        device_id=user_input.device_id,
                    ),
                )
            except HomeAssistantError as err:
                _LOGGER.error("Error getting LLM API: %s", err)

        # Build messages
        messages: list[dict[str, Any]] = []

        # Add system prompt
        if llm_api:
            system_prompt = self.entry.options.get(CONF_LLM_HASS_API, llm.DEFAULT_INSTRUCTIONS_PROMPT)
        else:
            system_prompt = "You are a helpful assistant."

        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input.text})

        # Prepare tools
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
            _LOGGER.debug("Available tools: %s", [t["function"]["name"] for t in tools] if tools else "None")

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
        if message.tool_calls and llm_api:
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

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                _LOGGER.debug("Calling tool: %s with args: %s", tool_name, tool_args)

                try:
                    tool_result = await llm_api.async_call_tool(tool_name, tool_args)
                except Exception as err:
                    tool_result = {"error": str(err)}
                    _LOGGER.error("Tool call failed: %s", err)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result),
                })

            # Get final response after tool calls
            try:
                response = await self.client.chat.completions.create(
                    model=self.entry.data[CONF_CHAT_MODEL],
                    messages=messages,
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
