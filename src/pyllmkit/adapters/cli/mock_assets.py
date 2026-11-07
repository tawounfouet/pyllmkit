"""Deterministic valid standalone media generators for CLI offline simulation.

Generates structurally valid, standards-compliant PNG, WAV, and MP4 media payloads
playable and viewable in macOS native applications (Preview, QuickTime, Music, Finder).
Zero third-party dependencies: strictly uses Python standard library modules.
"""

from __future__ import annotations

import base64
import io
import math
import struct
import wave
import zlib

# Structurally valid minimal 2-second H.264/AAC MP4 container (320x240 @ 10fps).
# Formatted with faststart (moov atom at beginning) for immediate streaming playback.
_MINIMAL_VALID_H264_MP4_BASE64 = (
    "AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAQcbW9vdgAAAGxtdmhkAAAAAAAAAAAAAAAAAAAD6AAAB9AAAQAAAQAAAAAA"
    "AAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAA0Z0cmFrAA"
    "AAXHRraGQAAAADAAAAAAAAAAAAAAABAAAAAAAAB9AAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAA"
    "AAAUAAAADwAAAAAAAkZWR0cwAAABxlbHN0AAAAAAAAAAEAAAfQAAAIAAABAAAAAAK+bWRpYQAAACBtZGhkAAAAAAAAAAAAAAAAAAAoAAAA"
    "UABVxAAAAAAALWhkbHIAAAAAAAAAAHZpZGUAAAAAAAAAAAAAAABWaWRlb0hhbmRsZXIAAAACaW1pbmYAAAAUdm1oZAAAAAEAAAAAAAAAAA"
    "AAACRkaW5mAAAAHGRyZWYAAAAAAAAAAQAAAAx1cmwgAAAAAQAAAilzdGJsAAAAwXN0c2QAAAAAAAAAAQAAALFhdmMxAAAAAAAAAAEAAAAA"
    "AAAAAAAAAAAAAAAAAUAA8ABIAAAASAAAAAAAAAABFUxhdmM2Mi4yOC4xMDEgbGlieDI2NAAAAAAAAAAAAAAAGP//AAAAN2F2Y0MBZAAM"
    "/+EAGWdkAAys2UFB+wEQAAADABAAAAMBQPFCmWABAAdo6+CUTITA/fj4AAAAABBwYXNwAAAAAQAAAAEAAAAUYnRydAAAAAAAAF5kAAAAAA"
    "AAABhzdHRzAAAAAAAAAAEAAAAUAAAEAAAAABRzdHNzAAAAAAAAAAEAAAABAAAAoGN0dHMAAAAAAAAAEgAAAAEAAAgAAAAAAQAAFAAAAAAB"
    "AAAIAAAAAAEAAAAAAAAAAQAABAAAAAABAAAUAAAAAAEAAAgAAAAAAQAAAAAAAAABAAAEAAAAAAMAAAgAAAAAAQAAFAAAAAABAAAIAAAAAA"
    "EAAAAAAAAAAQAABAAAAAABAAAUAAAAAAEAAAgAAAAAAQAAAAAAAAABAAAEAAAAABxzdHNjAAAAAAAAAAEAAAABAAAAFAAAAAEAAABkc3Rz"
    "egAAAAAAAAAAAAAAFAAACyYAAAHgAAAAaQAAADIAAAAxAAABtwAAAGAAAAA6AAAANAAAALkAAAFLAAAA7AAAAbYAAABHAAAAKwAAACUAAAF"
    "MAAAAVAAAADYAAAAvAAAAFHN0Y28AAAAAAAAAAQAABEwAAABidWR0YQAAAFptZXRhAAAAAAAAACFoZGxyAAAAAAAAAABtZGlyYXBwbAAA"
    "AAAAAAAAAAAAAC1pbHN0AAAAJal0b28AAAAdZGF0YQAAAAEAAAAATGF2ZjYyLjEyLjEwMQAAAAhmcmVlAAAXoW1kYXQAAAKwBgX//6zcRem"
    "95tlIt5Ys2CDZI+7veDI2NCAtIGNvcmUgMTY1IHIzMjIyIGIzNTYwNWEgLSBILjI2NC9NUEVHLTQgQVZDIGNvZGVjIC0gQ29weWxlZnQg"
    "MjAwMy0yMDI1IC0gaHR0cDovL3d3dy52aWRlb2xhbi5vcmcveDI2NC5odG1sIC0gb3B0aW9uczogY2FiYWM9MSByZWY9MyBkZWJsb2Nr"
    "PTE6LTM6LTMgYW5hbHlzZT0weDM6MHgxMTMgbWU9aGV4IHN1Ym1lPTcgcHN5PTEgcHN5X3JkPTIuMDA6MC43MCBtaXhlZF9yZWY9MSBt"
    "ZV9yYW5nZT0xNiBjaHJvbWFfbWU9MSB0cmVsbGlzPTEgOHg4ZGN0PTEgY3FtPTAgZGVhZHpvbmU9MjEsMTEgZmFzdF9wc2tpcD0xIGNoc"
    "m9tYV9xcF9vZmZzZXQ9LTQgdGhyZWFkcz03IGxvb2thaGVhZF90aHJlYWRzPTEgc2xpY2VkX3RocmVhZHM9MCBucj0wIGRlY2ltYXRl"
    "PTEgaW50ZXJsYWNlZD0wIGJsdXJheV9jb21wYXQ9MCBjb25zdHJhaW5lZF9pbnRyYT0wIGJmcmFtZXM9MyBiX3B5cmFtaWQ9MiBiX2Fk"
    "YXB0PTEgYl9iaWFzPTAgZGlyZWN0PTEgd2VpZ2h0Yj0xIG9wZW5fZ29wPTAgd2VpZ2h0cD0yIGtleWludD0yNTAga2V5aW50X21pbj0x"
    "MCBzY2VuZWN1dD00MCBpbnRyYV9yZWZyZXNoPTAgcmNfbG9va2FoZWFkPTQwIHJjPWNyZiBtYnRyZWU9MSBjcmY9MzUuMCBxY29tcD0w"
    "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"
    "r+S7707jt4QWTvKO7ljeNA=="
)


def create_mock_png(width: int = 256, height: int = 256) -> str:
    """Generate a valid, fully viewable 24-bit RGB PNG image with a colorful grid pattern."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # Filter byte: None
        for x in range(width):
            # Gradient: Deep indigo to bright magenta with luminous grid
            r = int((x / width) * 200 + 40)
            g = int((y / height) * 120 + 30)
            b = int((1.0 - (x / width)) * 220 + 35)

            # Elegant contrast border & grid lines
            if x < 4 or x >= width - 4 or y < 4 or y >= height - 4:
                r, g, b = 255, 255, 255
            elif x % 32 == 0 or y % 32 == 0:
                r = min(255, r + 60)
                g = min(255, g + 60)
                b = min(255, b + 60)
            raw.extend((r, g, b))

    def make_chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png.extend(make_chunk(b"IHDR", ihdr))
    png.extend(make_chunk(b"IDAT", zlib.compress(bytes(raw), 6)))
    png.extend(make_chunk(b"IEND", b""))
    b64_payload = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64_payload}"


def create_mock_wav(duration: float = 2.0, sample_rate: int = 22050) -> str:
    """Generate a valid, audible 16-bit PCM WAVE audio file with a harmonious chord."""
    num_samples = int(sample_rate * duration)
    samples = bytearray()
    for i in range(num_samples):
        t = float(i) / sample_rate
        # Smooth envelope (fade-in and fade-out to prevent clicks)
        env = min(t * 8.0, 1.0) * min((duration - t) * 4.0, 1.0)
        # Gentle harmonious chord: A4 (440 Hz) + C#5 (554.37 Hz)
        s1 = math.sin(2.0 * math.pi * 440.0 * t)
        s2 = 0.5 * math.sin(2.0 * math.pi * 554.37 * t)
        val = int(env * 0.35 * 32767.0 * (s1 + s2))
        val = max(-32768, min(32767, val))
        samples.extend(struct.pack("<h", val))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples)

    b64_payload = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:audio/wav;base64,{b64_payload}"


def create_mock_mp4() -> str:
    """Return a structurally valid 2-second 320x240 H.264 MP4 video container."""
    return f"data:video/mp4;base64,{_MINIMAL_VALID_H264_MP4_BASE64}"

