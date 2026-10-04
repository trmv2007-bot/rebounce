from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VoicePhase(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


@dataclass(slots=True)
class VoiceSession:
    phase: VoicePhase = VoicePhase.IDLE
    turns: int = 0
    partial_transcript: str = ""

    def start_listening(self) -> None:
        self.phase = VoicePhase.LISTENING
        self.partial_transcript = ""

    def receive_transcript(self, text: str, *, final: bool = False) -> None:
        self.partial_transcript = text.strip()
        if final:
            self.turns += 1
            self.phase = VoicePhase.THINKING

    def start_speaking(self) -> None:
        self.phase = VoicePhase.SPEAKING

    def interrupt(self) -> None:
        self.phase = VoicePhase.INTERRUPTED

    def stop(self) -> None:
        self.phase = VoicePhase.IDLE
        self.partial_transcript = ""


class VoiceProvider:
    """Provider-independent voice contract.

    The web client currently implements this contract with the browser Web
    Speech API. A native/local STT/TTS adapter can replace it without changing
    companion identity, memory, or conversation state.
    """

    name = "abstract"

    def supports_local_recognition(self) -> bool:
        return False


class BrowserVoiceProvider(VoiceProvider):
    name = "browser"

    def supports_local_recognition(self) -> bool:
        return True
