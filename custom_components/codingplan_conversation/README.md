# CodingPlan Conversation Integration for Home Assistant

阿里云百炼 CodingPlan 的 Home Assistant 对话集成。支持自定义 API Endpoint 和多种大模型。

## 功能特点

- ✅ 自定义 API Endpoint（OpenAI 兼容协议）
- ✅ 预设 CodingPlan 支持的模型列表
- ✅ 支持配置温度、最大 token 等参数
- ✅ 支持 Home Assistant 的 LLM API（控制设备）

## CodingPlan 简介

CodingPlan 整合了千问、GLM、Kimi、MiniMax 等顶级模型，兼容主流 AI 编程工具。通过固定月费模式，折算成本远低于常规 API 调用。

**官方文档：** https://help.aliyun.com/document_detail/xxxxxx.html

## 支持的模型

### 推荐模型
- `qwen3.6-plus`（支持图片理解）⭐ 默认
- `kimi-k2.5`（支持图片理解）
- `glm-5`
- `minimax-m2.5`

### 更多模型
- `qwen3.5-plus`（支持图片理解）
- `qwen3-max-2026-01-23`
- `qwen3-coder-next`
- `qwen3-coder-plus`
- `glm-4.7`
- `qwen3.6-max-preview`
- `qwen3.6-flash`
- `qwen3-vl-plus`
- `qwen3-coder`
- `qwen3-max`
- `qwen3.5-omni-plus`
- 视频/图像生成模型：`wan2.6-t2v`、`wan2.7-image`、`wan2.7-video`、`wan2.6-i2v`

## 安装

### 通过 HACS（推荐）

1. 在 HACS 中添加自定义仓库：`https://github.com/skysbird/home-assistant-ai`
2. 类型选择 **Integration**
3. 安装后重启 Home Assistant

### 手动安装

1. 下载最新 release
2. 将 `custom_components/codingplan_conversation` 复制到 Home Assistant 的 `config/custom_components/`
3. 重启 Home Assistant

## 配置

### 第一步：订阅 CodingPlan

1. 访问 [CodingPlan 购买页](https://bailian.console.aliyun.com/#/codingplan)
2. 选择并购买套餐（Lite 或 Pro）

### 第二步：获取专属 API Key 和 Base URL

在 [CodingPlan 页面](https://bailian.console.aliyun.com/#/codingplan) 获取：

- **API Key**: 格式为 `sk-sp-xxxxx`（注意：不是普通的 `sk-xxxxx`）
- **Base URL**: `https://coding.dashscope.aliyuncs.com/v1`

⚠️ **重要提示：** CodingPlan 专属的 API Key 和 Base URL 与百炼按量计费的 API Key 不互通，请勿混用！

### 第三步：配置集成

1. 前往 **设置** → **设备与服务** → **添加集成**
2. 搜索 "CodingPlan Conversation"
3. 输入配置：
   - **API Base URL**: `https://coding.dashscope.aliyuncs.com/v1`
   - **API Key**: 你的 `sk-sp-xxxxx` 格式 Key
4. 选择模型（推荐 `qwen3.6-plus`）并配置参数

## 配置参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 模型 | `qwen3.6-plus` | 选择 CodingPlan 支持的模型 |
| Max Tokens | 1024 | 生成文本的最大 token 数 (1-8192) |
| Temperature | 1.0 | 采样温度，值越大越随机 (0.0-2.0) |
| Top P | 1.0 | 核采样参数 (0.0-1.0) |

## 使用

配置完成后：

1. 前往 **设置** → **语音助手**
2. 在 **对话代理** 中选择 "CodingPlan"
3. 现在可以使用 Assist 进行语音或文字对话控制 Home Assistant

## 用量限制

根据套餐不同，用量限制不同：

**Pro 套餐（¥200/月）：**
- 每 5 小时：6,000 次请求
- 每周：45,000 次请求
- 每月：90,000 次请求

额度恢复规则：
- 每 5 小时额度：滚动恢复，每分钟自动释放
- 每周额度：每周一 00:00:00 重置
- 每月额度：下个月订阅日 00:00:00 重置

## 文件结构

```
custom_components/codingplan_conversation/
├── __init__.py          # 组件初始化
├── config_flow.py       # 配置流程
├── conversation.py      # 对话实体实现
├── const.py             # 常量定义
├── manifest.json        # 组件元数据
├── strings.json         # 翻译字符串
├── services.yaml        # 服务定义
└── README.md            # 本文件
```

## 依赖

- `openai>=1.0.0`（利用 OpenAI 兼容接口）

## 注意事项

1. **仅限编程工具使用**：CodingPlan 仅限在编程工具中使用，禁止用于自动化脚本、自定义应用后端或批量调用。

2. **数据使用授权**：使用期间，模型输入及生成内容将用于服务改进与模型优化。

3. **账号共享禁止**：套餐为订阅人专享，禁止共享账号。

## 故障排查

### 配置时提示 "cannot_connect"
- 检查 Base URL 是否为 `https://coding.dashscope.aliyuncs.com/v1`
- 确认网络可以访问阿里云

### 配置时提示 "invalid_auth"
- 确认使用的是 CodingPlan 专属的 `sk-sp-xxxxx` 格式 API Key
- 不要与普通百炼 API Key (`sk-xxxxx`) 混淆

### 模型调用失败
- 检查是否选择了 CodingPlan 支持的模型
- 查看 CodingPlan 页面确认剩余额度

## 许可证

MIT License
