# CodingPlan Conversation

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/custom-components/hacs)

阿里云百炼 CodingPlan 的 Home Assistant 对话集成。

## 功能

- 支持千问、GLM、Kimi、MiniMax 等顶级模型
- OpenAI 兼容接口
- 自动模型选择
- 支持 Home Assistant 设备控制

## 快速开始

1. 在 [阿里云 CodingPlan](https://bailian.console.aliyun.com/#/codingplan) 订阅
2. 获取 API Key（`sk-sp-xxxxx` 格式）
3. 配置 Base URL：`https://coding.dashscope.aliyuncs.com/v1`
4. 选择模型（推荐 `qwen3.6-plus`）

## 通过 HACS 安装

1. 添加自定义仓库：`https://github.com/skysbird/home-assistant-ai`
2. 类型：**Integration**
3. 安装后重启 Home Assistant

## 配置

在 **设置** → **设备与服务** → **添加集成** 中搜索 "CodingPlan"。

## 支持的模型

- qwen3.6-plus（默认）
- kimi-k2.5
- glm-5
- minimax-m2.5
- qwen3-coder 系列
- 更多...

## 使用

在 **语音助手** 设置中选择 CodingPlan 作为对话代理。

## 文档

详见 [GitHub 仓库](https://github.com/skysbird/home-assistant-ai)
