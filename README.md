# home-assistant-ai

Home Assistant 自定义组件集合，用于集成各种 AI 服务。

## 组件列表

### CodingPlan Conversation

阿里云百炼 CodingPlan 的 Home Assistant 对话集成。

**功能：**
- 自定义 API Endpoint（OpenAI 兼容接口）
- 支持千问、GLM、Kimi、MiniMax 等顶级模型
- 自动模型选择
- 支持 Home Assistant LLM API（控制设备）

**快速开始：**
1. 在 [阿里云 CodingPlan](https://bailian.console.aliyun.com/#/codingplan) 订阅服务
2. 获取专属 API Key（`sk-sp-xxxxx` 格式）
3. 配置 Base URL：`https://coding.dashscope.aliyuncs.com/v1`
4. 选择模型（推荐 `qwen3.6-plus`）

详见 [codingplan_conversation/README.md](custom_components/codingplan_conversation/README.md)

## 安装

### 通过 HACS

1. 在 HACS 中添加自定义仓库：`https://github.com/skysbird/home-assistant-ai`
2. 类型选择 **Integration**
3. 安装后重启 Home Assistant

### 手动安装

```bash
git clone https://github.com/skysbird/home-assistant-ai.git
cp -r home-assistant-ai/custom_components/codingplan_conversation /config/custom_components/
```

重启 Home Assistant 后，在 **设置** → **设备与服务** → **添加集成** 中搜索 "CodingPlan Conversation"。

## 支持的模型

- qwen3.6-plus（默认，支持图片理解）
- kimi-k2.5（支持图片理解）
- glm-5
- minimax-m2.5
- qwen3.5-plus
- qwen3-coder、qwen3-coder-next
- 等更多模型

## 许可证

MIT License
