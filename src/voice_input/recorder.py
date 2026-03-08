"""Audio recording module."""

import tempfile
import threading
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd


class AudioRecorder:
    """Audio recorder using sounddevice."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        max_duration: float = 60.0,
        on_start: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
    ):
        """Initialize audio recorder.

        Args:
            sample_rate: Audio sample rate in Hz.
            channels: Number of audio channels.
            max_duration: Maximum recording duration in seconds.
            on_start: Callback when recording starts.
            on_stop: Callback when recording stops.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.max_duration = max_duration
        self.on_start = on_start
        self.on_stop = on_stop

        self._is_recording = False
        self._audio_data: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._stop_event = threading.Event()

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags) -> None:
        """Callback for audio stream."""
        if self._is_recording and not self._stop_event.is_set():
            self._audio_data.append(indata.copy())
        else:
            raise sd.CallbackStop()

    def start_recording(self) -> None:
        """Start recording audio."""
        if self._is_recording:
            return

        self._audio_data = []
        self._stop_event.clear()
        self._is_recording = True

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()

        if self.on_start:
            self.on_start()

        # Start max duration timer
        if self.max_duration > 0:
            threading.Timer(self.max_duration, self.stop_recording).start()

    def stop_recording(self) -> np.ndarray | None:
        """Stop recording and return audio data.

        Returns:
            Recorded audio data as numpy array, or None if not recording.
        """
        if not self._is_recording:
            return None

        self._is_recording = False
        self._stop_event.set()

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self.on_stop:
            self.on_stop()

        if not self._audio_data:
            return None

        # Concatenate all audio chunks
        audio = np.concatenate(self._audio_data, axis=0)
        return audio

    def save_to_file(self, audio: np.ndarray, filepath: Path | None = None) -> Path:
        """Save audio data to a WAV file.

        Args:
            audio: Audio data as numpy array.
            filepath: Output file path. If None, creates a temp file.

        Returns:
            Path to the saved file.
        """
        import wave

        if filepath is None:
            filepath = Path(tempfile.mktemp(suffix=".wav"))

        # Convert float32 to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        with wave.open(str(filepath), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        return filepath

    def get_audio_bytes(self, audio: np.ndarray) -> bytes:
        """Convert audio data to WAV bytes.

        Args:
            audio: Audio data as numpy array.

        Returns:
            Audio data as WAV-formatted bytes.
        """
        import io
        import wave

        buffer = io.BytesIO()
        audio_int16 = (audio * 32767).astype(np.int16)

        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        return buffer.getvalue()

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices.

        Returns:
            List of device info dictionaries.
        """
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