#!/bin/bash
# VoxCPM2 TTS + Wyoming 适配器 - Mac 本地安装脚本
# 支持 Apple Silicon (M1/M2/M3/M4)

set -e

echo "=== VoxCPM2 Mac 安装脚本 ==="
echo ""

# 检查系统
if [[ "$(uname)" != "Darwin" ]]; then
    echo "此脚本仅用于 Mac 系统"
    exit 1
fi

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "请先安装 Python 3.10+:"
    echo "  brew install python@3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python 版本: $PYTHON_VERSION"

# 创建目录
INSTALL_DIR="$HOME/voxcpm-tts"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo ""
echo "=== 安装依赖 ==="

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装 VoxCPM
echo "安装 VoxCPM2..."
pip install --upgrade pip
pip install voxcpm

# 安装 Wyoming 协议
echo "安装 Wyoming..."
pip install wyoming aiohttp soundfile numpy

# 下载模型（可选，首次运行时会自动下载）
echo ""
echo "=== 模型下载 ==="
echo "首次运行时会自动下载模型 (~4GB)，或手动下载："
echo "  pip install modelscope"
echo "  python -c \"from modelscope import snapshot_download; snapshot_download('OpenBMB/VoxCPM2', local_dir='./models')\""
echo ""

# 复制 Wyoming 适配器
cat > wyoming_voxcpm_mac.py << 'PYTHON_EOF'
#!/usr/bin/env python3
"""Wyoming protocol adapter for VoxCPM2 TTS on Mac.

Uses MPS (Metal) for acceleration on Apple Silicon.
"""

import asyncio
import logging
import os
import sys

# Add voxcpm to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import aiohttp
    from wyoming.server import AsyncServer
    from wyoming.tts import Synthesize, SynthesizedAudioStart, SynthesizedAudioStop
    from wyoming.audio import AudioChunk
    from wyoming.info import Describe, Info, TtsInfo, VoiceInfo
    from wyoming.event import Event
    from voxcpm import VoxCPM
    import soundfile as sf
    import numpy as np
    import tempfile
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install voxcpm wyoming aiohttp soundfile numpy")
    sys.exit(1)

_LOGGER = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", "10200"))
MODEL_PATH = os.environ.get("MODEL_PATH", "openbmb/VoxCPM2")

# VoxCPM2: 48kHz output
SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2
CHANNELS = 1

VOICES = [
    VoiceInfo(name="default", language="zh-CN", description="默认中文女声"),
    VoiceInfo(name="male", language="zh-CN", description="中文男声"),
    VoiceInfo(name="gentle", language="zh-CN", description="温柔女声"),
    VoiceInfo(name="sichuan", language="zh-CN-sichuan", description="四川话"),
    VoiceInfo(name="cantonese", language="zh-CN-cantonese", description="粤语"),
]


class VoxCPMMacHandler:
    """Wyoming handler using local VoxCPM2 model on Mac."""

    def __init__(self, model):
        self.model = model
        self._voices = VOICES

    async def handle_event(self, event: Event):
        """Handle Wyoming events."""
        from wyoming.event import EventAsyncGenerator

        if Describe.is_type(event.type):
            yield Info(
                tts=TtsInfo(
                    voices=self._voices,
                    sample_rate=SAMPLE_RATE,
                    sample_width=SAMPLE_WIDTH,
                    channels=CHANNELS,
                )
            )

        elif Synthesize.is_type(event.type):
            synthesize = Synthesize.from_event(event)
            text = synthesize.text
            voice = synthesize.voice or "default"

            _LOGGER.info(f"Synthesizing: '{text}' with voice '{voice}'")

            # Apply voice style
            styled_text = self._apply_style(text, voice)

            # Generate audio (run in thread to avoid blocking)
            audio = await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_audio,
                styled_text
            )

            if audio is None:
                _LOGGER.error("Generation failed")
                return

            yield SynthesizedAudioStart(
                sample_rate=SAMPLE_RATE,
                sample_width=SAMPLE_WIDTH,
                channels=CHANNELS
            )

            # Send audio chunks
            chunk_size = 4096
            audio_bytes = (audio * 32767).astype(np.int16).tobytes()

            offset = 0
            while offset < len(audio_bytes):
                chunk = audio_bytes[offset:offset + chunk_size]
                yield AudioChunk(
                    audio=chunk,
                    sample_rate=SAMPLE_RATE,
                    sample_width=SAMPLE_WIDTH,
                    channels=CHANNELS
                )
                offset += chunk_size

            yield SynthesizedAudioStop()

    def _apply_style(self, text: str, voice: str) -> str:
        """Add voice description prefix."""
        styles = {
            "male": "(中年男性，声音深沉稳重)",
            "gentle": "(年轻女性，温柔甜美的声音)",
            "sichuan": "(四川方言，地道四川话)",
            "cantonese": "(粤语，地道广东话)",
            "default": "(年轻女性，清晰自然的声音)",
        }
        prefix = styles.get(voice, styles["default"])
        return f"{prefix}{text}"

    def _generate_audio(self, text: str) -> np.ndarray | None:
        """Generate audio using VoxCPM2."""
        try:
            _LOGGER.info(f"Generating audio for: {text[:50]}...")
            wav = self.model.generate(
                text=text,
                cfg_value=2.0,
                inference_timesteps=10,
            )
            return wav
        except Exception as e:
            _LOGGER.error(f"Generation error: {e}")
            return None


async def main():
    """Start Wyoming server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    _LOGGER.info("Loading VoxCPM2 model...")
    _LOGGER.info(f"Model path: {MODEL_PATH}")
    _LOGGER.info("This may take a few minutes on first run...")

    # Load model
    model = VoxCPM.from_pretrained(
        MODEL_PATH,
        load_denoiser=False,
    )

    _LOGGER.info("Model loaded successfully!")
    _LOGGER.info(f"Starting Wyoming server on port {PORT}")

    server = AsyncServer(PORT)
    handler = VoxCPMMacHandler(model)

    await server.start(lambda *args, **kwargs: handler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOGGER.info("Server stopped")
PYTHON_EOF

chmod +x wyoming_voxcpm_mac.py

# 创建启动脚本
cat > start.sh << 'BASH_EOF'
#!/bin/bash
cd "$HOME/voxcpm-tts"
source venv/bin/activate

echo "=== 启动 VoxCPM2 Wyoming 服务 ==="
echo "端口: 10200"
echo ""
echo "Home Assistant 配置:"
echo "  - 添加 Wyoming 集成"
echo "  - 地址: ws://本机IP:10200"
echo ""

python wyoming_voxcpm_mac.py
BASH_EOF

chmod +x start.sh

echo ""
echo "=== 安装完成 ==="
echo ""
echo "目录: $INSTALL_DIR"
echo ""
echo "启动服务:"
echo "  cd ~/voxcpm-tts && ./start.sh"
echo ""
echo "Home Assistant 配置:"
echo "  1. 设置 → 设备与服务 → 添加集成 → Wyoming"
echo "  2. 地址: ws://YOUR_MAC_IP:10200"
echo ""
echo "=== 注意 ==="
echo "首次启动会下载模型 (~4GB)，请耐心等待"