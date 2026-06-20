"""Voice activity detection for barge-in.

Energy-based by default (no extra deps). If webrtcvad is installed it is used for more
accurate detection; otherwise we fall back to an RMS-energy threshold over PCM16 frames.
"""

from __future__ import annotations

from voice_agent.streaming.stt_adapter import _energy

_DEFAULT_THRESHOLD = 50.0


class EnergyVAD:
    """RMS-energy VAD over PCM16 LE frames."""

    def __init__(self, threshold: float = _DEFAULT_THRESHOLD) -> None:
        self.threshold = threshold

    def is_speech(self, pcm: bytes) -> bool:
        return _energy(pcm) >= self.threshold


def build_vad(threshold: float = _DEFAULT_THRESHOLD):
    """Return a VAD with an ``is_speech(pcm) -> bool`` method (webrtcvad if available)."""
    try:
        import webrtcvad  # noqa: F401  (presence check only)

        class _WebRtcVAD:
            def __init__(self) -> None:
                import webrtcvad as _w

                self._vad = _w.Vad(2)

            def is_speech(self, pcm: bytes) -> bool:
                try:
                    # webrtcvad expects 10/20/30ms frames; fall back to energy on size mismatch.
                    return self._vad.is_speech(pcm, 24000)
                except Exception:
                    return _energy(pcm) >= _DEFAULT_THRESHOLD

        return _WebRtcVAD()
    except Exception:
        return EnergyVAD(threshold)
