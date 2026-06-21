"""Unit-test defaults for the voice-agent service.

These tests should be deterministic even when a developer has a real local
`.env` configured for Claude, Cartesia, Gemini, or HTTP tool calls.
Individual tests can still patch settings when they need to exercise a real
provider mode.
"""

from __future__ import annotations

import os

os.environ["VOICE_AGENT_ANSWER_MODE"] = "mock"
os.environ["TOOL_MODE"] = "mock"
os.environ["VOICE_AGENT_TTS_PROVIDER"] = "browser"
os.environ["CLAIMVOICE_VOICE_RUNTIME"] = "browser"
