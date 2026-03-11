"""Text input module for simulating keyboard input."""

import logging
import os
import pwd
import subprocess
import time

import pyperclip

logger = logging.getLogger(__name__)


class TextInput:
    """Text input handler supporting multiple input methods."""

    def __init__(self, method: str = "type", type_delay: float = 0.01):
        """Initialize text input handler.

        Args:
            method: Input method - "type", "clipboard", "ydotool", "xdotool".
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

        logger.info(f"准备输入文字: '{text[:20]}{'...' if len(text) > 20 else ''}'")

        # 根据配置的方法或自动检测选择输入方式
        methods = []

        if self.method == "clipboard":
            # 剪贴板模式：wl-copy + ydotool Ctrl+V（推荐，支持中文）
            if self._check_wl_copy() and self._check_ydotool():
                methods.append(("wl-clipboard+ydotool", self._input_via_clipboard_paste))
            if self._check_wl_copy():
                methods.append(("wl-clipboard", self._input_via_wl_clipboard))
            methods.append(("clipboard-pynput", self._input_via_clipboard))
        elif self.method == "xdotool" and self._check_xdotool():
            methods.append(("xdotool", self._input_via_xdotool))
        elif self.method == "ydotool" and self._check_ydotool():
            methods.append(("ydotool", self._input_via_ydotool))
        elif self.method == "wtype" and self._check_wtype():
            methods.append(("wtype", self._input_via_wtype))
        else:
            # 自动检测可用方式（按优先级）
            # 1. 剪贴板粘贴（wl-copy + ydotool Ctrl+V，GNOME Wayland 最可靠）
            if self._check_wl_copy() and self._check_ydotool():
                methods.append(("wl-clipboard+ydotool", self._input_via_clipboard_paste))
            # 2. xdotool（XWayland 环境，非 GNOME Wayland）
            if self._check_xdotool():
                methods.append(("xdotool", self._input_via_xdotool))
            # 3. wtype（部分 Wayland 合成器支持）
            if self._check_wtype():
                methods.append(("wtype", self._input_via_wtype))
            # 4. ydotool（仅支持 ASCII）
            if self._check_ydotool():
                methods.append(("ydotool", self._input_via_ydotool))
            # 5. pynput（X11 后备）
            methods.append(("pynput", self._input_via_keyboard))

        # 尝试每种方法，直到成功
        for method_name, method_func in methods:
            logger.debug(f"尝试使用 {method_name} 输入文字...")
            try:
                if method_func(text):
                    logger.info(f"使用 {method_name} 成功输入文字")
                    return True
            except Exception as e:
                logger.warning(f"{method_name} 输入失败: {e}")

        logger.error("所有输入方式都失败了")
        return False

    def _user_cmd_prefix(self, wayland: bool = False) -> list[str]:
        """When running as root (via sudo), use runuser to delegate commands to the actual user."""
        if os.geteuid() == 0:
            sudo_user = os.environ.get('SUDO_USER')
            if sudo_user:
                pw = pwd.getpwnam(sudo_user)
                uid = pw.pw_uid
                home_dir = pw.pw_dir
                xauthority = os.environ.get('XAUTHORITY', f'{home_dir}/.Xauthority')
                env_vars = [
                    f'DISPLAY={os.environ.get("DISPLAY", ":0")}',
                    f'XAUTHORITY={xauthority}',
                ]
                if wayland:
                    env_vars += [
                        f'WAYLAND_DISPLAY={os.environ.get("WAYLAND_DISPLAY", "wayland-0")}',
                        f'XDG_RUNTIME_DIR=/run/user/{uid}',
                    ]
                return ['runuser', '-u', sudo_user, '--', 'env'] + env_vars
        return []

    # --- Check methods ---

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

    def _check_xdotool(self) -> bool:
        """Check if xdotool is available."""
        try:
            result = subprocess.run(
                ["which", "xdotool"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    # --- Input methods ---

    def _input_via_clipboard_paste(self, text: str) -> bool:
        """Input text using wl-copy + ydotool Ctrl+V.

        Most reliable method for Chinese text on GNOME Wayland:
        - wl-copy handles any Unicode text
        - ydotool sends Ctrl+V via uinput (no need to type characters)
        """
        try:
            logger.debug("使用 wl-copy 复制到剪贴板...")
            result = subprocess.run(
                self._user_cmd_prefix(wayland=True) + ["wl-copy", "--", text],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                logger.warning(f"wl-copy 失败: {result.stderr}")
                return False

            # 等待剪贴板更新
            time.sleep(0.15)

            logger.debug("使用 ydotool 模拟 Ctrl+V...")
            result = subprocess.run(
                ["ydotool", "key", "ctrl+v"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                return True
            else:
                logger.warning(f"ydotool Ctrl+V 失败: {result.stderr}")
                print(f"已复制到剪贴板，请按 Ctrl+V 粘贴")
                return True
        except subprocess.TimeoutExpired:
            logger.error("剪贴板输入超时")
            return False
        except Exception as e:
            logger.error(f"剪贴板输入失败: {e}")
            return False

    def _input_via_xdotool(self, text: str) -> bool:
        """Input text using xdotool (X11/XWayland, supports Unicode/Chinese)."""
        try:
            logger.debug("使用 xdotool 输入文字...")
            cmd = self._user_cmd_prefix(wayland=False) + [
                "xdotool", "type", "--clearmodifiers", "--delay", "12", text,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True
            else:
                logger.warning(f"xdotool 失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"xdotool 输入失败: {e}")
            return False

    def _input_via_wl_clipboard(self, text: str) -> bool:
        """Input text using wl-copy + wtype Ctrl+V (Wayland native)."""
        try:
            logger.debug("使用 wl-copy 复制到剪贴板...")
            result = subprocess.run(
                self._user_cmd_prefix(wayland=True) + ["wl-copy", "--", text],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                logger.warning(f"wl-copy 失败: {result.stderr}")
                return False

            time.sleep(0.1)

            logger.debug("使用 wtype 模拟 Ctrl+V...")
            result = subprocess.run(
                self._user_cmd_prefix(wayland=True) + ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                return True
            else:
                logger.warning(f"wtype 粘贴失败: {result.stderr}")
                print(f"已复制到剪贴板，请按 Ctrl+V 粘贴")
                return True
        except Exception as e:
            logger.error(f"剪贴板输入失败: {e}")
            return False

    def _input_via_wtype(self, text: str) -> bool:
        """Input text using wtype (Wayland native, needs compositor support)."""
        try:
            logger.debug("使用 wtype 直接输入文字...")
            result = subprocess.run(
                self._user_cmd_prefix(wayland=True) + ["wtype", text],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True
            else:
                logger.warning(f"wtype 失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"wtype 输入失败: {e}")
            return False

    def _input_via_ydotool(self, text: str) -> bool:
        """Input text using ydotool (uinput, ASCII only)."""
        try:
            logger.debug("使用 ydotool 输入文字...")
            result = subprocess.run(
                ["sudo", "ydotool", "type", "--key-delay", "12", text],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True
            else:
                logger.warning(f"ydotool 失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"ydotool 输入失败: {e}")
            return False

    def _input_via_keyboard(self, text: str) -> bool:
        """Input text by simulating keyboard keystrokes via pynput."""
        try:
            from pynput.keyboard import Controller, Key

            logger.debug("使用 pynput 模拟键盘输入...")
            keyboard = Controller()

            time.sleep(0.1)

            for char in text:
                keyboard.type(char)
                if self.type_delay > 0:
                    time.sleep(self.type_delay)

            return True
        except Exception as e:
            logger.error(f"pynput 键盘输入失败: {e}")
            return False

    def _input_via_clipboard(self, text: str) -> bool:
        """Input text by copying to clipboard and simulating paste via pynput."""
        try:
            from pynput.keyboard import Controller, Key

            logger.debug("使用剪贴板方式输入文字...")
            pyperclip.copy(text)

            time.sleep(0.1)

            keyboard = Controller()
            keyboard.press(Key.ctrl)
            keyboard.press("v")
            keyboard.release("v")
            keyboard.release(Key.ctrl)

            return True
        except Exception as e:
            logger.error(f"剪贴板输入失败: {e}")
            return False

    @staticmethod
    def check_dependencies() -> dict[str, bool]:
        """Check if required dependencies are available."""
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

        for tool in ["wtype", "ydotool", "xdotool", "wl-copy"]:
            try:
                result = subprocess.run(
                    ["which", tool],
                    capture_output=True,
                    text=True,
                )
                deps[tool] = result.returncode == 0
            except Exception:
                deps[tool] = False

        return deps
