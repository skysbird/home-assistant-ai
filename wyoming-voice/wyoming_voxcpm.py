#!/usr/bin/env python3
"""Wyoming protocol adapter for VoxCPM2 TTS.

Connects VoxCPM2's OpenAI-compatible API to Home Assistant via Wyoming protocol.
"""

import asyncio
import json
import io
import wave
import logging
import os
from typing import AsyncGenerator

import aiohttp
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import Synthesize, SynthesizedAudioStart, SynthesizedAudioStop
from wyoming.info import Describe, Info, TtsInfo, VoiceInfo, AsrInfo

_LOGGER = logging.getLogger(__name__)

VOXCPM_URL = os.environ.get("VOXCPM_URL", "http://voxcpm:8000")
VOXCPM_MODEL = os.environ.get("VOXCPM_MODEL", "openbmb/VoxCPM2")
PORT = int(os.environ.get("PORT", "10200"))

# VoxCPM2 supports 48kHz output
SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2  # 16-bit
CHANNELS = 1

# Supported voices
VOICES = [
    VoiceInfo(name="default", language="zh-CN", description="默认中文女声"),
    VoiceInfo(name="male", language="zh-CN", description="中文男声"),
    VoiceInfo(name="female_gentle", language="zh-CN", description="温柔女声"),
    VoiceInfo(name="english", language="en-US", description="英文"),
]


class VoxCPMEventHandler(AsyncEventHandler):
    """Handle Wyoming events and forward to VoxCPM2."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session: aiohttp.ClientSession | None = None

    async def handle_event(self, event: Event) -> AsyncGenerator[Event, None]:
        """Handle a Wyoming event."""
        if Describe.is_type(event.type):
            _LOGGER.debug("Describe request")
            yield Info(
                tts=TtsInfo(
                    voices=VOICES,
                    sample_rate=SAMPLE_RATE,
                    sample_width=SAMPLE_WIDTH,
                    channels=CHANNELS,
                ),
                asr=AsrInfo(),  # Empty, we only do TTS
            )

        elif Synthesize.is_type(event.type):
            _LOGGER.debug("Synthesize request: %s", event.data)
            yield from self._handle_synthesize(event)

        else:
            _LOGGER.warning("Unhandled event type: %s", event.type)

    async def _handle_synthesize(self, event: Event) -> AsyncGenerator[Event, None]:
        """Handle TTS synthesis request."""
        synthesize = Synthesize.from_event(event)

        text = synthesize.text
        if not text:
            _LOGGER.warning("No text to synthesize")
            return

        # Get voice selection
        voice = synthesize.voice or "default"

        # Add voice style prefix for VoxCPM2
        styled_text = self._apply_voice_style(text, voice)

        # Call VoxCPM2 API
        audio_data = await self._call_voxcpm(styled_text)

        if audio_data is None:
            _LOGGER.error("Failed to get audio from VoxCPM2")
            return

        # Send audio events
        yield SynthesizedAudioStart(sample_rate=SAMPLE_RATE, sample_width=SAMPLE_WIDTH, channels=CHANNELS)

        # Send audio in chunks
        chunk_size = 4096
        offset = 0
        while offset < len(audio_data):
            chunk = audio_data[offset:offset + chunk_size]
            yield AudioChunk(audio=chunk, sample_rate=SAMPLE_RATE, sample_width=SAMPLE_WIDTH, channels=CHANNELS)
            offset += chunk_size

        yield SynthesizedAudioStop()

    def _apply_voice_style(self, text: str, voice: str) -> str:
        """Apply voice style prefix for VoxCPM2."""
        # VoxCPM2 uses description prefix for voice design
        style_prefixes = {
            "male": "(中年男性，声音低沉稳重)",
            "female_gentle": "(年轻女性，温柔甜美的声音)",
            "english": "(English native speaker, neutral tone)",
            "default": "(年轻女性，清晰自然的声音)",
            "sichuan": "(四川方言，地道四川话)",
            "cantonese": "(粤语，地道广东话)",
            "shanghai": "(吴语，上海话)",
        }
        prefix = style_prefixes.get(voice, style_prefixes["default"])
        return f"{prefix}{text}"

    async def _call_voxcpm(self, text: str) -> bytes | None:
        """Call VoxCPM2 OpenAI-compatible API."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

        try:
            # OpenAI-compatible endpoint
            url = f"{VOXCPM_URL}/v1/audio/speech"
            payload = {
                "model": VOXCPM_MODEL,
                "input": text,
                "voice": "default",
            }

            _LOGGER.debug("Calling VoxCPM2: %s", url)
            async with self._session.post(url, json=payload) as response:
                if response.status != 200:
                    error = await response.text()
                    _LOGGER.error("VoxCPM2 error: %s - %s", response.status, error)
                    return None

                # Get raw audio bytes
                audio_bytes = await response.read()
                _LOGGER.debug("Got %d bytes of audio", len(audio_bytes))
                return audio_bytes

        except Exception as err:
            _LOGGER.error("Failed to call VoxCPM2: %s", err)
            return None

    async def stop(self) -> None:
        """Cleanup."""
        if self._session:
            await self._session.close()
            self._session = None


async def main() -> None:
    """Run the Wyoming VoxCPM2 adapter."""
    logging.basicConfig(level=logging.INFO)
    _LOGGER.info("Starting Wyoming VoxCPM2 adapter on port %d", PORT)
    _LOGGER.info("VoxCPM2 URL: %s", VOXCPM_URL)

    server = AsyncServer(PORT)
    await server.start(VoxCPMEventHandler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass