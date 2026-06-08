"""
CV Tailor — Voice Input Module (Deepgram Integration)
======================================================
Record audio from microphone or load audio files, transcribe with Deepgram,
then structure the transcript into resume sections using Claude.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VoiceInput:
    """Handle voice-to-resume pipeline.

    Workflow:
        1. Record audio from microphone (or accept a file path).
        2. Transcribe with Deepgram.
        3. Structure the raw transcript into resume data with Claude.
    """

    def __init__(self) -> None:
        self._deepgram = None
        self._claude = None

    def _get_deepgram(self):
        if self._deepgram is None:
            from utils.api_clients import get_deepgram_client
            self._deepgram = get_deepgram_client()
        return self._deepgram

    def _get_claude(self):
        if self._claude is None:
            from utils.api_clients import get_claude_client
            self._claude = get_claude_client()
        return self._claude

    # ── Record from microphone ────────────────────────────────

    def record_audio(
        self,
        duration_seconds: int = 60,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> str:
        """Record audio from the default microphone.

        Args:
            duration_seconds: Maximum recording duration in seconds.
            sample_rate: Audio sample rate in Hz.
            channels: Number of audio channels (1 = mono).

        Returns:
            Path to the saved .wav file.
        """
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np
        except ImportError:
            raise ImportError(
                "Audio recording requires 'sounddevice' and 'soundfile'. "
                "Install them with: pip install sounddevice soundfile"
            )

        logger.info(
            "Recording audio for up to %d seconds (press Ctrl+C to stop early)…",
            duration_seconds,
        )
        print(f"\n🎤 Recording… Speak now! (up to {duration_seconds}s)")
        print("   Press Ctrl+C to stop recording early.\n")

        audio_data = None
        try:
            audio_data = sd.rec(
                int(duration_seconds * sample_rate),
                samplerate=sample_rate,
                channels=channels,
                dtype="float32",
            )
            sd.wait()
        except KeyboardInterrupt:
            try:
                sd.stop()
            except Exception:
                pass
            logger.info("Recording stopped early by user.")
            print("\n⏹️  Recording stopped.")
            # Trim silence / unrecorded portion if we have any data
            if audio_data is not None:
                try:
                    stream = sd.get_stream()
                    if stream is not None and hasattr(stream, "time"):
                        cutoff = max(1, int(stream.time * sample_rate))
                        audio_data = audio_data[:cutoff]
                except Exception:
                    # Keep whatever was captured
                    pass

        if audio_data is None:
            raise RuntimeError("No audio captured. Please try again.")

        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, audio_data, sample_rate)
        logger.info("Audio saved: %s", tmp.name)
        print(f"💾 Audio saved: {tmp.name}")
        return tmp.name

    # ── Transcribe audio ──────────────────────────────────────

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file using Deepgram.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Raw transcript text.
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        deepgram = self._get_deepgram()
        transcript = deepgram.transcribe_file(audio_path)
        logger.info("Transcription: %d characters", len(transcript))
        return transcript

    def transcribe_url(self, audio_url: str) -> str:
        """Transcribe audio from a URL using Deepgram.

        Args:
            audio_url: Public URL of the audio file.

        Returns:
            Raw transcript text.
        """
        deepgram = self._get_deepgram()
        return deepgram.transcribe_url(audio_url)

    # ── Structure transcript ──────────────────────────────────

    def structure_transcript(self, raw_transcript: str) -> str:
        """Use Claude to convert a raw transcript into structured resume text.

        Args:
            raw_transcript: Unstructured text from speech-to-text.

        Returns:
            Structured resume text with proper sections.
        """
        claude = self._get_claude()
        structured = claude.structure_voice_input(raw_transcript)
        logger.info("Transcript structured into resume format.")
        return structured

    # ── Full pipeline ─────────────────────────────────────────

    def voice_to_resume(self, audio_path: str | None = None) -> str:
        """Full pipeline: record/load → transcribe → structure.

        Args:
            audio_path: Path to an audio file. If None, records from microphone.

        Returns:
            Structured resume text ready for the ResumeBuilder.
        """
        # Step 1: Get audio
        recorded_locally = audio_path is None
        if audio_path is None:
            audio_path = self.record_audio()
        elif not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            # Step 2: Transcribe
            print("📝 Transcribing audio…")
            raw_transcript = self.transcribe(audio_path)
            print(f"✅ Transcription complete ({len(raw_transcript)} chars)")

            if not raw_transcript.strip():
                raise ValueError("Transcription returned empty text. Please try again.")

            # Step 3: Structure
            print("🧠 Structuring into resume format…")
            structured = self.structure_transcript(raw_transcript)
            print("✅ Resume structure generated!")

            return structured
        finally:
            # Always delete the temp recording we created ourselves so that
            # raw voice (PII) does not linger on disk after processing.
            if recorded_locally:
                try:
                    Path(audio_path).unlink(missing_ok=True)
                except OSError:
                    pass

    # ── Utility ───────────────────────────────────────────────

    @staticmethod
    def list_audio_devices() -> list[dict[str, Any]]:
        """List available audio input devices.

        Returns:
            List of device info dicts.
        """
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = []
            for i, dev in enumerate(devices):
                if dev["max_input_channels"] > 0:
                    input_devices.append({
                        "index": i,
                        "name": dev["name"],
                        "channels": dev["max_input_channels"],
                        "sample_rate": dev["default_samplerate"],
                    })
            return input_devices
        except ImportError:
            return [{"error": "sounddevice not installed"}]
