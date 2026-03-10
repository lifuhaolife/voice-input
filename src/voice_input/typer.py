"""Text input module for simulating keyboard input."""

import subprocess
import time

import pyperclip


class TextInput:
    """Text input handler supporting multiple input methods."""

    def __init__(self, method: str = "type", type_delay: float = 0.01):
        """Initialize text input handler.

        Args:
            method: Input method - "type", "clipboard", or "ydotool".
            type_delay: Delay between keystrokes in seconds.
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

        # 优先使用ydotool (Wayland)
        if self._check_ydotool():
            return self._input_via_ydotool(text)

        # Wayland: 使用剪贴板方式
        if self._check_wl_copy():
            return self._input_via_wl_clipboard(text)

        # 使用wtype (Wayland原生)
        if self._check_wtype():
            return self._input_via_wtype(text)

        if self.method == "clipboard":
            return self._input_via_clipboard(text)
        else:
            return self._input_via_keyboard(text)

    def _check_wl_copy(self) -> bool:
        """Check if wl-copy is available (Wayland clipboard)."""
        try:
            result = subprocess.run(
                ["which", "wl-copy"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _input_via_wl_clipboard(self, text: str) -> bool:
        """Input text using wl-copy + wtype (Wayland clipboard + Ctrl+V).

        Args:
            text: Text to input.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # 复制到剪贴板
            subprocess.run(
                ["wl-copy", text],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            # 等待剪贴板更新
            time.sleep(0.1)
            
            # 使用wtype模拟Ctrl+V
            result = subprocess.run(
                ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode == 0:
                return True
            else:
                # wtype失败，文字已在剪贴板，提示用户粘贴
                print(f"已复制到剪贴板，请按 Ctrl+V 粘贴")
                return True
        except Exception as e:
            print(f"剪贴板输入失败: {e}")
            return False

    def _check_wtype(self) -> bool:
        """Check if wtype is available (Wayland native)."""
        try:
            result = subprocess.run(
                ["which", "wtype"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _input_via_wtype(self, text: str) -> bool:
        """Input text using wtype (Wayland native).

        Args:
            text: Text to input.

        Returns:
            True if successful, False otherwise.
        """
        try:
            result = subprocess.run(
                ["wtype", text],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True
            else:
                print(f"wtype failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"wtype input failed: {e}")
            return False

    def _check_ydotool(self) -> bool:
        """Check if ydotool is available."""
        try:
            result = subprocess.run(
                ["which", "ydotool"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _input_via_ydotool(self, text: str) -> bool:
        """Input text using ydotool (Wayland compatible).

        Args:
            text: Text to input.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # 使用sudo ydotool (需要uinput权限)
            result = subprocess.run(
                ["sudo", "ydotool", "type", "--key-delay", "0", text],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True
            else:
                print(f"ydotool failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"ydotool input failed: {e}")
            return False

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

        # Check for wtype (Wayland native)
        try:
            result = subprocess.run(
                ["which", "wtype"],
                capture_output=True,
                text=True,
            )
            deps["wtype"] = result.returncode == 0
        except Exception:
            deps["wtype"] = False

        # Check for ydotool (Wayland)
        try:
            result = subprocess.run(
                ["which", "ydotool"],
                capture_output=True,
                text=True,
            )
            deps["ydotool"] = result.returncode == 0
        except Exception:
            deps["ydotool"] = False

        return deps