"""Constants for CodingPlan Conversation integration."""

DOMAIN = "codingplan_conversation"

CONF_BASE_URL = "base_url"
CONF_API_VERSION = "api_version"
CONF_CHAT_MODEL = "chat_model"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_PROMPT = "prompt"
CONF_REASONING_EFFORT = "reasoning_effort"
CONF_WEB_SEARCH = "web_search"

DEFAULT_BASE_URL = "https://codingplan.aliyuncs.com/v1"
DEFAULT_API_VERSION = "2024-05-01"
DEFAULT_CHAT_MODEL = "codingplan-turbo"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 1.0

RECOMMENDED_CHAT_MODEL = "codingplan-turbo"
RECOMMENDED_MAX_TOKENS = 1024
RECOMMENDED_TEMPERATURE = 1.0
RECOMMENDED_TOP_P = 1.0
