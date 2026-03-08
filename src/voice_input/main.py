#!/usr/bin/env python3
"""Voice Input - Main entry point."""

import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Any

from voice_input.config import Config, get_config
from voice_input.hotkey import HotkeyListener
from voice_input.notify import Notifier
from voice_input.recorder import AudioRecorder
from voice_input.recognizer import WhisperRecognizer
from voice_input.typer import TextInput

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class VoiceInput:
    """Main voice input application."""

    def __init__(self, config: Config):
        """Initialize voice input application.

        Args:
            config: Configuration instance.
        """
        self.config = config

        # Initialize components
        self.notifier = Notifier(enabled=config.notification["enabled"])
        self.recorder = AudioRecorder(
            sample_rate=config.recording["sample_rate"],
            channels=config.recording["channels"],
            max_duration=config.recording["max_duration"],
            on_start=self._on_recording_start,
            on_stop=self._on_recording_stop,
        )
        self.recognizer = self._create_recognizer()
        self.text_input = TextInput(
            method=config.input_config["method"],
            type_delay=config.input_config["type_delay"],
        )
        self.hotkey_listener: HotkeyListener | None = None

        # State
        self._running = False

    def _create_recognizer(self) -> Any:
        """Create speech recognizer based on configuration."""
        backend = self.config.backend

        if backend == "whisper":
            return WhisperRecognizer(
                model=self.config.whisper["model"],
                language=self.config.whisper["language"],
                device=self.config.whisper["device"],
            )
        elif backend == "baidu":
            raise NotImplementedError("Baidu backend not yet implemented")
        elif backend == "xunfei":
            raise NotImplementedError("Xunfei backend not yet implemented")
        elif backend == "tencent":
            raise NotImplementedError("Tencent backend not yet implemented")
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def _on_recording_start(self) -> None:
        """Handle recording start event."""
        logger.info("Recording started")
        if self.config.notification["show_status"]:
            self.notifier.notify_recording_start()

    def _on_recording_stop(self) -> None:
        """Handle recording stop event."""
        logger.info("Recording stopped")
        if self.config.notification["show_status"]:
            self.notifier.notify_recording_stop()

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press - start recording."""
        if not self.recorder.is_recording:
            self.recorder.start_recording()

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release - stop recording and process."""
        audio = self.recorder.stop_recording()
        if audio is not None:
            self._process_audio(audio)

    def _process_audio(self, audio: Any) -> None:
        """Process recorded audio and input text.

        Args:
            audio: Recorded audio data.
        """
        try:
            # Transcribe audio
            logger.info("Transcribing audio...")
            text = self.recognizer.transcribe(audio)

            if text:
                logger.info(f"Recognized: {text}")

                # Show notification
                if self.config.notification["show_result"]:
                    self.notifier.notify_result(text)

                # Input text
                success = self.text_input.input_text(text)
                if not success:
                    logger.error("Failed to input text")
                    self.notifier.notify_error("Failed to input text")
            else:
                logger.warning("No speech detected")
                self.notifier.notify_error("No speech detected")

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            self.notifier.notify_error(str(e))

    def start(self) -> None:
        """Start the voice input application."""
        if self._running:
            return

        logger.info("Starting Voice Input...")

        # Check recognizer availability
        if not self.recognizer.is_available():
            logger.error(f"Recognizer '{self.config.backend}' is not available")
            self.notifier.notify_error(f"Recognizer '{self.config.backend}' not available")
            return

        # Setup hotkey listener
        self.hotkey_listener = HotkeyListener(
            hotkey=self.config.hotkey["trigger"],
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
            mode=self.config.hotkey["mode"],
        )

        self._running = True
        self.hotkey_listener.start()

        logger.info(f"Voice Input ready! Press {self.config.hotkey['trigger']} to start recording")
        self.notifier.notify("🎤 Voice Input", f"Ready! Press {self.config.hotkey['trigger']}")

    def stop(self) -> None:
        """Stop the voice input application."""
        if not self._running:
            return

        logger.info("Stopping Voice Input...")

        # Stop recording if in progress
        if self.recorder.is_recording:
            self.recorder.stop_recording()

        # Stop hotkey listener
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener = None

        self._running = False
        logger.info("Voice Input stopped")

    def run(self) -> None:
        """Run the application (blocking)."""
        self.start()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Keep running
        try:
            while self._running:
                import time
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle termination signals."""
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Voice Input - Voice-to-text input tool for Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  voice-input                    # Start with default config
  voice-input --config my.yaml   # Use custom config file
  voice-input --list-devices     # List audio input devices
  voice-input --backend whisper --model small  # Override settings
        """,
    )

    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--backend",
        choices=["whisper", "baidu", "xunfei", "tencent"],
        help="Speech recognition backend",
    )
    parser.add_argument(
        "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (whisper backend only)",
    )
    parser.add_argument(
        "--hotkey",
        help="Hotkey combination (e.g., 'ctrl+alt+v')",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # List devices and exit
    if args.list_devices:
        print("Available audio input devices:")
        print("-" * 60)
        devices = AudioRecorder.list_devices()
        for dev in devices:
            print(f"  [{dev['index']}] {dev['name']}")
            print(f"      Channels: {dev['channels']}, Sample Rate: {dev['sample_rate']}")
        return

    # Load configuration
    config = get_config(args.config)

    # Override with command line arguments
    if args.backend:
        config._config["backend"] = args.backend
    if args.model:
        config._config["whisper"]["model"] = args.model
    if args.hotkey:
        config._config["hotkey"]["trigger"] = args.hotkey

    # Run application
    app = VoiceInput(config)
    app.run()


if __name__ == "__main__":
    main()