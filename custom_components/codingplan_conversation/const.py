"""Constants for CodingPlan Conversation integration."""

DOMAIN = "codingplan_conversation"

CONF_BASE_URL = "base_url"
CONF_CHAT_MODEL = "chat_model"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_PROMPT = "prompt"

DEFAULT_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
DEFAULT_CHAT_MODEL = "qwen3.6-plus"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 1.0

PRESET_MODELS = [
    "qwen3.6-plus",
    "kimi-k2.5",
    "glm-5",
    "minimax-m2.5",
    "qwen3.5-plus",
    "qwen3-max-2026-01-23",
    "qwen3-coder-next",
    "qwen3-coder-plus",
    "glm-4.7",
    "qwen3.6-max-preview",
    "qwen3.6-flash",
    "qwen3-vl-plus",
    "qwen3-coder",
    "qwen3-max",
    "qwen3.5-omni-plus",
]
