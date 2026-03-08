"""Hotkey listener module."""

import logging
import threading
from typing import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Global hotkey listener supporting hold and toggle modes."""

    def __init__(
        self,
        hotkey: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None] | None = None,
        mode: str = "hold",
    ):
        """Initialize hotkey listener.

        Args:
            hotkey: Hotkey combination string (e.g., "ctrl+alt+v").
            on_press: Callback when hotkey is pressed (or toggled on).
            on_release: Callback when hotkey is released (hold mode only).
            mode: "hold" (press-hold-release) or "toggle" (press to start/stop).
        """
        self.hotkey_str = hotkey
        self.on_press = on_press
        self.on_release = on_release
        self.mode = mode

        self._is_active = False
        self._listener: keyboard.Listener | None = None
        self._pressed_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        self._hotkey_keys: list[keyboard.Key | keyboard.KeyCode] = []
        self._toggle_state = False

        self._parse_hotkey()

    def _parse_hotkey(self) -> None:
        """Parse hotkey string into key codes."""
        from pynput.keyboard import Key, KeyCode

        key_map = {
            "ctrl": Key.ctrl,
            "ctrl_l": Key.ctrl_l,
            "ctrl_r": Key.ctrl_r,
            "alt": Key.alt,
            "alt_l": Key.alt_l,
            "alt_r": Key.alt_r,
            "shift": Key.shift,
            "shift_l": Key.shift_l,
            "shift_r": Key.shift_r,
            "super": Key.cmd,
            "cmd": Key.cmd,
            "win": Key.cmd,
            "meta": Key.cmd,
        }

        parts = self.hotkey_str.lower().split("+")
        for part in parts:
            part = part.strip()
            if part in key_map:
                self._hotkey_keys.append(key_map[part])
            elif len(part) == 1:
                self._hotkey_keys.append(KeyCode.from_char(part))
            else:
                # Try to parse as special key
                try:
                    key_attr = getattr(Key, part, None)
                    if key_attr:
                        self._hotkey_keys.append(key_attr)
                except Exception:
                    logger.warning(f"Unknown key: {part}")

        logger.debug(f"Parsed hotkey: {self._hotkey_keys}")

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        """Handle key press event."""
        if key is None:
            return

        self._pressed_keys.add(key)

        # Check if all hotkey keys are pressed
        if self._check_hotkey_pressed():
            if self.mode == "hold":
                if not self._is_active:
                    self._is_active = True
                    logger.debug("Hotkey pressed (hold mode)")
                    if self.on_press:
                        self.on_press()
            elif self.mode == "toggle":
                if not self._is_active:
                    self._is_active = True
                    self._toggle_state = not self._toggle_state
                    logger.debug(f"Hotkey toggled: {self._toggle_state}")
                    if self._toggle_state and self.on_press:
                        self.on_press()
                    elif not self._toggle_state and self.on_release:
                        self.on_release()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        """Handle key release event."""
        if key is None:
            return

        # Remove from pressed keys
        self._pressed_keys.discard(key)

        # In hold mode, trigger release when any hotkey key is released
        if self.mode == "hold" and self._is_active:
            if key in self._hotkey_keys:
                self._is_active = False
                logger.debug("Hotkey released (hold mode)")
                if self.on_release:
                    self.on_release()

    def _check_hotkey_pressed(self) -> bool:
        """Check if all hotkey keys are currently pressed."""
        return all(k in self._pressed_keys for k in self._hotkey_keys)

    def start(self) -> None:
        """Start listening for hotkey."""
        if self._listener is not None:
            return

        logger.info(f"Starting hotkey listener: {self.hotkey_str} (mode: {self.mode})")
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        """Stop listening for hotkey."""
        if self._listener:
            logger.info("Stopping hotkey listener")
            self._listener.stop()
            self._listener = None

    def is_active(self) -> bool:
        """Check if hotkey is currently active (pressed or toggled on)."""
        return self._is_active or self._toggle_state

    def __enter__(self) -> "HotkeyListener":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()