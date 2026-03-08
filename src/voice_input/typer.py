"""Text input module for simulating keyboard input."""

import subprocess
import time

import pyperclip


class TextInput:
    """Text input handler supporting multiple input methods."""

    def __init__(self, method: str = "type", type_delay: float = 0.01):
        """Initialize text input handler.

        Args:
            method: Input method - "type" (simulate keystrokes) or "clipboard" (paste).
            type_delay: Delay between keystrokes in seconds (for "type" method).
        """
        self.method = method
        self.type_delay = type_delay

    def input_text(self, text: str) -> bool:
        """Input text at current cursor position.

        Args:
            text: Text to input.

        Returns:
            True if successful, False otherwise.
        """
        if not text:
            return False

        if self.method == "clipboard":
            return self._input_via_clipboard(text)
        else:
            return self._input_via_keyboard(text)

    def _input_via_keyboard(self, text: str) -> bool:
        """Input text by simulating keyboard keystrokes.

        Args:
            text: Text to input.

        Returns:
            True if successful, False otherwise.
        """
        try:
            from pynput.keyboard import Controller, Key

            keyboard = Controller()

            # Small delay before typing
            time.sleep(0.1)

            for char in text:
                keyboard.type(char)
                if self.type_delay > 0:
                    time.sleep(self.type_delay)

            return True
        except Exception as e:
            print(f"Keyboard input failed: {e}")
            return False

    def _input_via_clipboard(self, text: str) -> bool:
        """Input text by copying to clipboard and simulating paste.

        Args:
            text: Text to input.

        Returns:
            True if successful, False otherwise.
        """
        try:
            from pynput.keyboard import Controller, Key

            # Copy text to clipboard
            pyperclip.copy(text)

            # Small delay
            time.sleep(0.1)

            # Simulate Ctrl+V (or Super+V on some systems)
            keyboard = Controller()
            keyboard.press(Key.ctrl)
            keyboard.press("v")
            keyboard.release("v")
            keyboard.release(Key.ctrl)

            return True
        except Exception as e:
            print(f"Clipboard input failed: {e}")
            return False

    @staticmethod
    def check_dependencies() -> dict[str, bool]:
        """Check if required dependencies are available.

        Returns:
            Dictionary with dependency status.
        """
        deps = {}

        try:
            from pynput.keyboard import Controller  # noqa: F401
            deps["pynput"] = True
        except ImportError:
            deps["pynput"] = False

        try:
            import pyperclip  # noqa: F401
            deps["pyperclip"] = True
        except ImportError:
            deps["pyperclip"] = False

        # Check for xdotool (alternative method)
        try:
            result = subprocess.run(
                ["which", "xdotool"],
                capture_output=True,
                text=True,
            )
            deps["xdotool"] = result.returncode == 0
        except Exception:
            deps["xdotool"] = False

        return deps