"""RemoteDesktop Portal D-Bus integration for direct text input on GNOME Wayland.

Uses org.freedesktop.portal.RemoteDesktop to send Unicode keysyms
via NotifyKeyboardKeysym, enabling direct character input at cursor position.
"""

import logging
import os
import pwd
import threading
import time

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

logger = logging.getLogger(__name__)

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
PORTAL_IFACE = "org.freedesktop.portal.RemoteDesktop"
REQUEST_IFACE = "org.freedesktop.portal.Request"

# Special keysyms (XKB)
_SPECIAL_KEYSYMS = {
    "\n": 0xFF0D,  # Return
    "\r": 0xFF0D,  # Return
    "\t": 0xFF09,  # Tab
    "\b": 0xFF08,  # BackSpace
}


def _char_to_keysym(char: str) -> int:
    """Convert a character to an X11 keysym."""
    cp = ord(char)

    if char in _SPECIAL_KEYSYMS:
        return _SPECIAL_KEYSYMS[char]

    # ASCII printable and Latin-1 supplement: keysym == codepoint
    if 0x20 <= cp <= 0x7E or 0xA0 <= cp <= 0xFF:
        return cp

    # Unicode keysym convention: 0x01000000 + codepoint
    return 0x01000000 + cp


class RemoteDesktopPortal:
    """Send text input via GNOME RemoteDesktop Portal D-Bus interface."""

    def __init__(self, type_delay: float = 0.002):
        self._type_delay = type_delay
        self._session_path = None
        self._lock = threading.Lock()

        # Set up D-Bus with GLib main loop
        DBusGMainLoop(set_as_default=True)
        self._bus = self._connect_bus()
        self._portal = self._bus.get_object(PORTAL_BUS, PORTAL_PATH)
        self._portal_iface = dbus.Interface(self._portal, PORTAL_IFACE)

        # Start GLib main loop in background thread for signal handling
        self._loop = GLib.MainLoop()
        self._loop_thread = threading.Thread(target=self._loop.run, daemon=True)
        self._loop_thread.start()

        self._request_counter = 0

    def _connect_bus(self) -> dbus.Bus:
        """Connect to the session D-Bus, handling root/sudo scenarios."""
        if os.geteuid() == 0:
            sudo_user = os.environ.get("SUDO_USER")
            if sudo_user:
                pw = pwd.getpwnam(sudo_user)
                bus_addr = f"unix:path=/run/user/{pw.pw_uid}/bus"
                return dbus.bus.BusConnection(bus_addr)
        return dbus.SessionBus()

    def _wait_for_response(self, request_path: str, timeout: float = 10.0) -> dict | None:
        """Wait for a Portal Request Response signal."""
        result = {"response": None}
        event = threading.Event()

        def on_response(response_code, results):
            result["response"] = (response_code, results)
            event.set()

        request_obj = self._bus.get_object(PORTAL_BUS, request_path)
        request_iface = dbus.Interface(request_obj, REQUEST_IFACE)
        request_iface.connect_to_signal("Response", on_response)

        if not event.wait(timeout):
            logger.error(f"Portal request timed out: {request_path}")
            return None

        code, results = result["response"]
        if code != 0:
            logger.error(f"Portal request failed with code {code}")
            return None

        return dict(results)

    def _next_token(self) -> str:
        """Generate a unique request token."""
        self._request_counter += 1
        return f"voice_input_{os.getpid()}_{self._request_counter}"

    def _request_path_for_token(self, token: str) -> str:
        """Compute the expected request object path for a given token."""
        sender = self._bus.get_unique_name().replace(".", "_").lstrip(":")
        return f"/org/freedesktop/portal/desktop/request/{sender}/{token}"

    def _ensure_session(self) -> bool:
        """Create or reuse a RemoteDesktop Portal session."""
        if self._session_path:
            return True

        with self._lock:
            if self._session_path:
                return True

            try:
                # Step 1: CreateSession
                token = self._next_token()
                request_path = self._request_path_for_token(token)
                options = dbus.Dictionary({
                    "handle_token": dbus.String(token),
                    "session_handle_token": dbus.String(f"session_{token}"),
                }, signature="sv")

                self._portal_iface.CreateSession(options)
                result = self._wait_for_response(request_path)
                if result is None:
                    return False

                session_handle = str(result.get("session_handle", ""))
                if not session_handle:
                    logger.error("No session_handle in CreateSession response")
                    return False

                logger.info(f"Portal session created: {session_handle}")

                # Step 2: SelectDevices (keyboard only, type=1)
                token = self._next_token()
                request_path = self._request_path_for_token(token)
                options = dbus.Dictionary({
                    "handle_token": dbus.String(token),
                    "types": dbus.UInt32(1),  # KEYBOARD
                }, signature="sv")

                session_obj = dbus.ObjectPath(session_handle)
                self._portal_iface.SelectDevices(session_obj, options)
                result = self._wait_for_response(request_path)
                if result is None:
                    return False

                logger.info("Portal devices selected (keyboard)")

                # Step 3: Start (may show authorization dialog)
                token = self._next_token()
                request_path = self._request_path_for_token(token)
                options = dbus.Dictionary({
                    "handle_token": dbus.String(token),
                }, signature="sv")

                self._portal_iface.Start(session_obj, "", options)
                result = self._wait_for_response(request_path, timeout=30.0)
                if result is None:
                    return False

                self._session_path = session_handle
                logger.info("Portal session started successfully")
                return True

            except dbus.DBusException as e:
                logger.error(f"Portal session setup failed: {e}")
                return False

    def type_text(self, text: str) -> bool:
        """Type text by sending Unicode keysyms via the Portal.

        Args:
            text: Text to type at the current cursor position.

        Returns:
            True if successful, False otherwise.
        """
        if not self._ensure_session():
            return False

        try:
            session_obj = dbus.ObjectPath(self._session_path)
            empty_opts = dbus.Dictionary({}, signature="sv")

            for char in text:
                keysym = dbus.UInt32(_char_to_keysym(char))
                # Key press
                self._portal_iface.NotifyKeyboardKeysym(
                    session_obj, empty_opts, keysym, dbus.UInt32(1)
                )
                # Key release
                self._portal_iface.NotifyKeyboardKeysym(
                    session_obj, empty_opts, keysym, dbus.UInt32(0)
                )
                if self._type_delay > 0:
                    time.sleep(self._type_delay)

            return True

        except dbus.DBusException as e:
            logger.warning(f"Portal keysym input failed: {e}, 尝试重建会话...")
            # Session invalidated — rebuild and retry once
            self._session_path = None
            if self._ensure_session():
                return self.type_text(text)
            return False

    def close(self):
        """Close the Portal session."""
        if self._session_path:
            try:
                session_obj = self._bus.get_object(PORTAL_BUS, self._session_path)
                session_iface = dbus.Interface(session_obj, "org.freedesktop.portal.Session")
                session_iface.Close()
            except Exception:
                pass
            self._session_path = None

        if self._loop and self._loop.is_running():
            self._loop.quit()

    @classmethod
    def is_available(cls) -> bool:
        """Check if RemoteDesktop Portal is available on this system."""
        try:
            DBusGMainLoop(set_as_default=True)

            if os.geteuid() == 0:
                sudo_user = os.environ.get("SUDO_USER")
                if sudo_user:
                    pw = pwd.getpwnam(sudo_user)
                    bus_addr = f"unix:path=/run/user/{pw.pw_uid}/bus"
                    bus = dbus.bus.BusConnection(bus_addr)
                else:
                    return False
            else:
                bus = dbus.SessionBus()

            portal = bus.get_object(PORTAL_BUS, PORTAL_PATH)
            props = dbus.Interface(portal, "org.freedesktop.DBus.Properties")
            version = props.Get(PORTAL_IFACE, "version")
            available = int(version) >= 1
            if available:
                logger.debug(f"RemoteDesktop Portal v{version} detected")
            return available
        except Exception as e:
            logger.debug(f"RemoteDesktop Portal not available: {e}")
            return False
