#!/bin/bash
# 启动 Wyoming 语音服务

cd "$(dirname "$0")"

echo "=== 启动 Wyoming 语音服务 ==="
echo ""
echo "包含服务："
echo "  - Piper (TTS/语音合成): 端口 10200"
echo "  - Whisper (STT/语音识别): 端口 10300"
echo "  - OpenWakeWord (唤醒词): 端口 10400"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    echo ""
    echo "安装方法："
    echo "  Windows/WSL: 安装 Docker Desktop for Windows"
    echo "  Mac: 安装 Docker Desktop for Mac"
    echo "  Linux: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: docker-compose 未安装"
    exit 1
fi

# 启动服务
echo "启动服务..."
docker compose up -d

echo ""
echo "=== 服务状态 ==="
docker compose ps

echo ""
echo "=== Home Assistant 配置 ==="
echo ""
echo "1. 添加 Wyoming Piper 集成:"
echo "   - 地址: ws://YOUR_IP:10200"
echo "   - 或用本机: ws://host.docker.internal:10200"
echo ""
echo "2. 添加 Wyoming Whisper 集成:"
echo "   - 地址: ws://YOUR_IP:10300"
echo ""
echo "3. 添加 Wyoming OpenWakeWord 集成:"
echo "   - 地址: ws://YOUR_IP:10400"
echo ""
echo "=== 完成 ==="