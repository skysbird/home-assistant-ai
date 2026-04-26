# CodingPlan Conversation

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/custom-components/hacs)

阿里云 Codeup CodingPlan 的 Home Assistant 对话集成。

## 功能

- 自定义 API Endpoint（支持 OpenAI 兼容接口）
- 自动拉取可用模型列表
- 支持配置温度、最大 token 等参数
- 支持 Home Assistant 的 LLM API（控制设备）

## 安装

### 通过 HACS

1. 在 HACS 中添加自定义仓库：`https://github.com/skysbird/home-assistant-ai`
2. 类型选择 **Integration**
3. 安装后重启 Home Assistant

### 手动安装

1. 下载最新 release
2. 将 `custom_components/codingplan_conversation` 复制到 Home Assistant 的 `config/custom_components/`
3. 重启 Home Assistant

## 配置

1. 前往 **设置** → **设备与服务** → **添加集成**
2. 搜索 "CodingPlan Conversation"
3. 输入 API 配置：
   - **API Base URL**: CodingPlan API 地址
   - **API Key**: 你的 CodingPlan API Key
4. 选择模型并配置参数

## 使用

配置完成后，在 **语音助手** 设置中选择 CodingPlan 作为对话代理。
