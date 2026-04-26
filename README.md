# home-assistant-ai

Home Assistant 自定义组件集合，用于集成各种 AI 服务。

## 组件列表

### CodingPlan Conversation

阿里云 Codeup CodingPlan 的 Home Assistant 对话集成。支持自定义 API Endpoint 和自动获取模型列表。

#### 特性
- 自定义 API Endpoint（支持 OpenAI 兼容接口）
- 自动拉取可用模型列表
- 支持配置温度、最大 token 等参数
- 支持 Home Assistant 的 LLM API（控制设备）

#### 安装

1. 将 `custom_components/codingplan_conversation` 复制到你的 Home Assistant `config/custom_components/` 目录
2. 重启 Home Assistant
3. 在 **设置** → **设备与服务** → **添加集成** 中搜索 "CodingPlan Conversation"

#### 配置
- **API Base URL**: CodingPlan API 地址（如 `https://codingplan.aliyuncs.com/v1`）
- **API Key**: 你的 CodingPlan API Key

详见 [codingplan_conversation/README.md](custom_components/codingplan_conversation/README.md)

