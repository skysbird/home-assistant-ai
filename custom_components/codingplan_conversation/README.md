# CodingPlan Conversation Integration for Home Assistant

阿里云 Codeup CodingPlan 的 Home Assistant 对话集成。支持自定义 API Endpoint 和自动获取模型列表。

## 功能特点

- ✅ 自定义 API Endpoint（支持 CodingPlan 的 OpenAI 兼容接口）
- ✅ 自动拉取可用模型列表
- ✅ 支持配置温度、最大 token 等参数
- ✅ 支持 Home Assistant 的 LLM API（控制设备）

## 安装

1. 将 `codingplan_conversation` 文件夹复制到 Home Assistant 的 `custom_components` 目录：

```bash
cp -r custom_components/codingplan_conversation /config/custom_components/
```

2. 重启 Home Assistant

3. 在 **设置** → **设备与服务** → **添加集成** 中搜索 "CodingPlan Conversation"

## 配置

### 第一步：API 配置

- **API Base URL**: CodingPlan 的 API 地址，例如 `https://codingplan.aliyuncs.com/v1`
- **API Key**: 你的 CodingPlan API Key

### 第二步：模型配置

配置向导会自动获取可用的模型列表，你可以：
- 选择要使用的模型（从 API 拉取）
- 设置最大 token 数
- 调整温度和 Top P 参数

## 使用

配置完成后，你可以在：
- **语音助手** 中选择 CodingPlan 作为对话代理
- 在 **Assist** 中使用自然语言控制设备

## 文件结构

```
custom_components/codingplan_conversation/
├── __init__.py          # 组件初始化
├── config_flow.py       # 配置流程（支持自定义 endpoint 和模型选择）
├── conversation.py      # 对话实体实现
├── const.py             # 常量定义
├── manifest.json        # 组件元数据
├── strings.json         # 翻译字符串
└── services.yaml        # 服务定义
```

## 开发说明

### 依赖

- `openai>=1.0.0`（利用 OpenAI 兼容接口）

### 架构

该组件基于 Home Assistant 的 `conversation` 平台构建：

1. `config_flow.py` - 处理配置流程：
   - 验证 API 连接
   - 获取可用模型列表
   - 保存配置参数

2. `conversation.py` - 实现 `ConversationEntity`：
   - 处理用户输入
   - 调用 CodingPlan API
   - 支持工具调用（控制 Home Assistant 设备）

## 许可证

MIT License
