"""System tray icon for voice input (Ubuntu/GNOME, AyatanaAppIndicator3)."""

import logging
import threading

logger = logging.getLogger(__name__)


class TrayIcon:
    """System tray icon using AyatanaAppIndicator3 + GTK3."""

    def __init__(self, app):
        """Initialize tray icon.

        Args:
            app: StreamingVoiceInput instance with start()/stop()/_running attribute.
        """
        self.app = app
        self._indicator = None
        self._menu_item_status = None
        self._menu_item_toggle = None
        self._gtk = None
        self._glib = None

    def _build_menu(self):
        Gtk = self._gtk
        menu = Gtk.Menu()

        self._menu_item_status = Gtk.MenuItem(label=self._status_label())
        self._menu_item_status.set_sensitive(False)
        menu.append(self._menu_item_status)

        menu.append(Gtk.SeparatorMenuItem())

        self._menu_item_toggle = Gtk.MenuItem(label=self._toggle_label())
        self._menu_item_toggle.connect("activate", self._on_toggle)
        menu.append(self._menu_item_toggle)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="退出")
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _status_label(self) -> str:
        return "● 运行中" if self.app._running else "○ 已停止"

    def _toggle_label(self) -> str:
        return "停止服务" if self.app._running else "启动服务"

    def _update_menu(self):
        if self._menu_item_status:
            self._menu_item_status.set_label(self._status_label())
        if self._menu_item_toggle:
            self._menu_item_toggle.set_label(self._toggle_label())
        if self._indicator:
            icon = "audio-input-microphone" if self.app._running else "audio-input-microphone-symbolic"
            self._indicator.set_icon_full(icon, "voice input")

    def _on_toggle(self, _widget):
        if self.app._running:
            self._glib.idle_add(self._do_stop)
        else:
            self._glib.idle_add(self._do_start)

    def _do_start(self):
        self.app.start()
        self._update_menu()
        return False

    def _do_stop(self):
        self.app.stop()
        self._update_menu()
        return False

    def _on_quit(self, _widget):
        self.app.stop()
        self._gtk.main_quit()

    def run(self):
        """Start the GTK main loop (blocking). Call from dedicated thread."""
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import Gtk, AyatanaAppIndicator3, GLib
        except Exception as e:
            logger.error(f"托盘图标不可用（缺少依赖）: {e}")
            return

        self._gtk = Gtk
        self._glib = GLib

        self._indicator = AyatanaAppIndicator3.Indicator.new(
            "voice-input",
            "audio-input-microphone",
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_menu(self._build_menu())

        Gtk.main()

    def start_in_thread(self):
        """Start the tray icon in a background thread."""
        t = threading.Thread(target=self.run, daemon=True, name="tray-gtk")
        t.start()
        return t
