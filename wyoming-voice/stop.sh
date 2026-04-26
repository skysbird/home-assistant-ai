#!/bin/bash
# 停止 Wyoming 语音服务

cd "$(dirname "$0")"

echo "停止 Wyoming 语音服务..."
docker compose down

echo "服务已停止"