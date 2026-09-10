#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "3.0")
try:
    gi.require_version("GtkLayerShell", "0.1")
except ValueError:
    pass

from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
try:
    from gi.repository import GtkLayerShell
except (ImportError, ValueError):
    GtkLayerShell = None

try:
    import evdev
    from evdev import ecodes
except ImportError:
    evdev = None
    ecodes = None
import cairo
import subprocess
import os
import datetime
import math
import re
import signal
import json
import time
import configparser
import shlex
import hashlib
from html import escape as xml_escape


USER_HOME = os.path.expanduser("~")
NORDVPN_APP = os.path.join(USER_HOME, "nordvpn-app.py")
SHIELD_TASKS_HELPER = os.path.join(USER_HOME, "shield-tasks", "shield-tasks")
DEFAULT_XDG_RUNTIME_DIR = f"/run/user/{os.getuid()}"


APPS = [
    {
        "name": "VLC",
        "subtitle": "Media Player",
        "command": [
            "/usr/bin/env",
            "QT_QPA_PLATFORM=xcb",
            "/usr/bin/vlc"
        ],
        "class": "vlc",
        "match": ["vlc"],
        "icon": "vlc"
    },
    {
        "name": "FreeTube",
        "subtitle": "",
        "command": [
            "/usr/bin/freetube",
            "--ozone-platform=wayland",
            "--disable-gpu"
        ],
        "class": "freetube",
        "match": [
            "FreeTube",
            "freetube",
            "io.freetubeapp.FreeTube"
        ],
        "special_icon": "freetube"
    },
    {
        "name": "KODI",
        "subtitle": "",
        "command": ["/usr/bin/kodi"],
        "class": "kodi",
        "match": ["kodi"],
        "icon": "kodi"
    },
    {
        "name": "NordVPN",
        "subtitle": "",
        "command": [
            "/usr/bin/python3",
            NORDVPN_APP
        ],
        "class": "nordvpn",
        "match": ["nordvpn", "nordvpn-app.py"],
        "icon_file": os.path.expanduser(
            "~/.local/share/icons/NordVPN.png"
        ),
        "icon": "nordvpn"
    },
]


SYSTEM_APPS = [
    {
        "name": "Dateien",
        "command": ["pcmanfm"],
        "icon": "folder"
    },
    {
        "name": "Bilder",
        "command": [
            "pcmanfm",
            os.path.expanduser("~/Pictures")
        ],
        "icon": "image-x-generic"
    },
    {
        "name": "Systeminfo",
        "command": None,
        "action": "systeminfo",
        "icon": "dialog-information"
    },
    {
        "name": "Launcher beenden",
        "command": None,
        "action": "quit_launcher",
        "icon": "application-exit"
    },
    {
        "name": "Neustart",
        "command": [
            "systemctl",
            "reboot"
        ],
        "special_icon": "restart"
    },
    {
        "name": "Ausschalten",
        "command": [
            "systemctl",
            "poweroff"
        ],
        "special_icon": "power"
    },
]


SCREEN_WIDTH = 720
SCREEN_HEIGHT = 576

LEFT_MARGIN = 20
RIGHT_MARGIN = 20

APPS_PER_ROW = 4

APP_SPACING = 8
APP_HEIGHT = 102

SYSTEM_SPACING = 8
SYSTEM_HEIGHT = 84

APP_ICON_SIZE = 58
SYSTEM_ICON_SIZE = 38
APP_CARD_WIDTH = (SCREEN_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - (APP_SPACING * 3)) // 4
TASKS_VISIBLE = 4

LABWC_RC = os.path.expanduser("~/.config/labwc/rc.xml")
WORKSPACE_AUTO_BEGIN = "<!-- SHIELD-AUTO-WORKSPACES-BEGIN -->"
WORKSPACE_AUTO_END = "<!-- SHIELD-AUTO-WORKSPACES-END -->"
LAUNCHER_APP_ID = "shield-launcher-test.py"
KNOWN_APP_IDS = {
    "vlc": "vlc",
    "freetube": "FreeTube",
    "kodi": "kodi",
    "nordvpn": "nordvpn-app.py",
}


class ShieldBackground(Gtk.DrawingArea):


    def __init__(self):
        super().__init__()
        self.connect("draw", self.draw_background)


    def draw_background(self, widget, cr):
        allocation = self.get_allocation()
        width = allocation.width
        height = allocation.height

        # Pure black background (requested)
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cr.move_to(185, 0)
        cr.line_to(440, 0)
        cr.line_to(180, height)
        cr.line_to(0, height)
        cr.close_path()
        cr.set_source_rgba(0.07, 0.11, 0.15, 0.42)
        cr.fill()

        cr.move_to(450, 0)
        cr.line_to(615, 0)
        cr.line_to(390, height)
        cr.line_to(255, height)
        cr.close_path()
        cr.set_source_rgba(0.06, 0.10, 0.14, 0.34)
        cr.fill()

        radius = 10
        horizontal = radius * 1.73
        vertical = radius * 1.50
        start_x = int(width * 0.58)

        row = 0
        y = 8

        while y < height:
            offset = horizontal / 2 if row % 2 else 0
            x = start_x + offset

            while x < width + 20:
                self.hexagon(cr, x, y, radius)
                cr.set_line_width(0.55)
                cr.set_source_rgba(0.35, 0.85, 0.08, 0.075)
                cr.stroke()
                x += horizontal

            y += vertical
            row += 1

        light_x1 = width * 0.89
        light_y1 = -25
        light_x2 = width * 0.56
        light_y2 = height + 35

        cr.set_line_width(24)
        cr.set_source_rgba(0.42, 1.0, 0.0, 0.025)
        cr.move_to(light_x1, light_y1)
        cr.line_to(light_x2, light_y2)
        cr.stroke()

        cr.set_line_width(10)
        cr.set_source_rgba(0.42, 1.0, 0.0, 0.07)
        cr.move_to(light_x1, light_y1)
        cr.line_to(light_x2, light_y2)
        cr.stroke()

        cr.set_line_width(2)
        cr.set_source_rgba(0.55, 1.0, 0.0, 0.82)
        cr.move_to(light_x1, light_y1)
        cr.line_to(light_x2, light_y2)
        cr.stroke()

        cr.set_line_width(1.2)
        cr.set_source_rgba(0.45, 1.0, 0.0, 0.32)
        cr.move_to(width * 0.64, height * 0.78)
        cr.line_to(width, height * 0.98)
        cr.stroke()

        return False

    def hexagon(self, cr, cx, cy, radius):
        for i in range(6):
            angle = (math.pi / 3) * i
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)

            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)

        cr.close_path()


class YouTubeLogo(Gtk.DrawingArea):

    def __init__(self):
        super().__init__()
        self.set_size_request(57, 46)
        self.connect("draw", self.draw_logo)

    def draw_logo(self, widget, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        box_width = min(width, 56)
        box_height = min(height, 38)

        x = (width - box_width) / 2
        y = (height - box_height) / 2
        radius = 9

        cr.new_sub_path()

        cr.arc(
            x + box_width - radius,
            y + radius,
            radius,
            -math.pi / 2,
            0
        )
        cr.arc(
            x + box_width - radius,
            y + box_height - radius,
            radius,
            0,
            math.pi / 2
        )
        cr.arc(
            x + radius,
            y + box_height - radius,
            radius,
            math.pi / 2,
            math.pi
        )
        cr.arc(
            x + radius,
            y + radius,
            radius,
            math.pi,
            3 * math.pi / 2
        )

        cr.close_path()
        cr.set_source_rgb(1.0, 0.0, 0.0)
        cr.fill()

        cx = width / 2 + 2
        cy = height / 2

        cr.move_to(cx - 7, cy - 10)
        cr.line_to(cx + 10, cy)
        cr.line_to(cx - 7, cy + 10)
        cr.close_path()

        cr.set_source_rgb(1, 1, 1)
        cr.fill()

        return False


class SystemSymbol(Gtk.DrawingArea):

    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
        self.set_size_request(SYSTEM_ICON_SIZE, SYSTEM_ICON_SIZE)
        self.connect("draw", self.draw_symbol)

    def draw_symbol(self, widget, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        cx = width / 2
        cy = height / 2

        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(4)
        cr.set_source_rgb(0.55, 0.95, 0.08)

        if self.symbol == "power":
            cr.arc(
                cx,
                cy + 2,
                13,
                -0.70,
                math.pi + 0.70
            )
            cr.stroke()

            cr.move_to(cx, cy - 15)
            cr.line_to(cx, cy + 1)
            cr.stroke()

        elif self.symbol == "restart":
            cr.arc(
                cx,
                cy,
                13,
                0.35,
                math.pi * 1.85
            )
            cr.stroke()

            cr.move_to(cx + 13, cy - 9)
            cr.line_to(cx + 14, cy + 2)
            cr.line_to(cx + 4, cy)
            cr.stroke()

        return False


class ShieldLauncher(Gtk.Window):

    def __init__(self):
        super().__init__()
        self.set_title("Shield Pi Launcher")
        self.set_default_size(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.fullscreen()
        self.set_decorated(False)
        self.set_name("launcher")
        # Force opaque black so no desktop shows through
        self.override_background_color(
            Gtk.StateFlags.NORMAL,
            Gdk.RGBA(0, 0, 0, 1)
        )
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.on_key)
        self.connect("key-release-event", self.on_key_release)

        self.rows = []
        self.current_row = 0
        self.current_col = 0

        # Launcher carousel
        self.app_index = 0
        self.app_view_start = 0
        self.app_row_box = None
        self.launcher_foreground = True

        # Black workspace (hides desktop when apps are in front)
        self._workspace_window = None

        # Task carousel
        self.task_window = None
        self.task_buttons = []
        self.task_items = []
        self.task_index = 0
        self.task_view_start = 0
        self.task_delete_mode = False
        self.task_delete_label = None
        self.task_cards_box = None

        # Installed-app chooser
        self.app_picker_window = None
        self.app_picker_buttons = []
        self.app_picker_items = []
        self.app_picker_index = 0

        # Long-OK app removal (custom launcher apps only)
        self.ok_hold_threshold = 0.85
        self._ok_press_started = None
        self._ok_press_class = None
        self.remove_confirm_window = None
        self.remove_confirm_buttons = []
        self.remove_confirm_choice = 0
        self.remove_confirm_item = None

        # Remote-driven universal on-screen keyboard. It is a non-focusable
        # layer-shell surface so the application's text field keeps focus.
        self.osk_window = None
        self.osk_root = None
        self.osk_buttons = []
        self.osk_row = 0
        self.osk_col = 0
        self.osk_symbols = False
        self.osk_shift = False
        self.osk_visible = False
        self.osk_device = None
        self.osk_watch_id = 0
        self.osk_device_grabbed = False

        self.icon_theme = Gtk.IconTheme.get_default()

        self.state_dir = os.path.expanduser("~/.config/shield-launcher")
        self.thumb_dir = os.path.join(self.state_dir, "thumbnails")
        self.state_file = os.path.join(self.state_dir, "recent-tasks.json")
        self.launcher_apps_file = os.path.join(self.state_dir, "launcher-apps.json")
        self.workspace_file = os.path.join(self.state_dir, "workspaces.json")
        os.makedirs(self.thumb_dir, exist_ok=True)

        self.custom_apps = self.load_launcher_apps()
        self.workspace_map = self.load_workspace_map()
        self.reconcile_workspace_map()
        self.write_workspace_rules()

        self.last_home_press = 0.0
        self.home_double_window = 0.38
        self.foreground_task_class = None
        self.recent_tasks = self.load_recent_tasks()
        self.mark_restored_tasks_inactive()

        # Shield mode: stop Raspberry Pi desktop/panel and their respawners.
        self._hide_desktop_chrome()

        self.build_ui()
        self.load_css()
        GLib.timeout_add_seconds(1, self.update_clock)
        GLib.timeout_add_seconds(2, self.sync_task_states)
        GLib.unix_signal_add(
            GLib.PRIORITY_DEFAULT,
            signal.SIGUSR1,
            self.on_taskmanager_signal
        )

        self.show_all()
        self.launcher_foreground = True
        self.focus_current()

        # The input-remapper virtual keyboard is stable across reboots even if
        # the /dev/input/event number changes. Menu/Super toggles the OSK.
        GLib.timeout_add_seconds(1, self._ensure_osk_remote_device)


    def on_taskmanager_signal(self):
        now = time.monotonic()

        # Home while task manager is visible -> launcher.
        if self.task_window is not None:
            try:
                self.task_window.destroy()
            except Exception:
                pass
            self.last_home_press = 0.0
            self.show_launcher()
            return True

        # Second quick Home press -> task manager.
        if (now - self.last_home_press) <= self.home_double_window:
            self.last_home_press = 0.0
            self.show_launcher()
            GLib.idle_add(self.show_task_manager)
            return True

        # IMPORTANT:
        # Only capture when an application is actually in front.
        # Never capture the launcher itself.
        if not self.launcher_foreground:
            self.capture_foreground_thumbnail()

        self.last_home_press = now
        self.show_launcher()
        return True

    def build_ui(self):
        overlay = Gtk.Overlay()
        self.add(overlay)

        background = ShieldBackground()
        background.set_hexpand(True)
        background.set_vexpand(True)
        overlay.add(background)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=3
        )
        root.set_hexpand(True)
        root.set_vexpand(True)

        root.set_margin_top(9)
        root.set_margin_bottom(8)
        root.set_margin_start(LEFT_MARGIN)
        root.set_margin_end(RIGHT_MARGIN)

        overlay.add_overlay(root)

        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10
        )

        title = Gtk.Label(label="Shield Pi")
        title.set_name("main-title")
        title.set_halign(Gtk.Align.START)

        self.clock = Gtk.Label()
        self.clock.set_name("clock")
        self.clock.set_halign(Gtk.Align.END)

        header.pack_start(title, True, True, 0)
        header.pack_end(self.clock, False, False, 0)

        root.pack_start(header, False, False, 0)

        self.add_section_title(root, "Apps")
        self.create_app_rows(root)

        self.add_section_title(root, "System")
        self.create_system_row(root)

        footer = Gtk.Label(
            label="← → Navigieren   OK Auswählen   OK halten App entfernen   Menü Tastatur"
        )
        footer.set_name("footer")
        footer.set_halign(Gtk.Align.START)

        separator = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL
        )
        separator.set_name("footer-separator")

        root.pack_end(footer, False, False, 3)
        root.pack_end(separator, False, False, 2)

    def add_section_title(self, root, text):
        label = Gtk.Label(label=text)
        label.set_name("section-title")
        label.set_halign(Gtk.Align.START)

        root.pack_start(label, False, False, 3)


    def create_app_content(self, item):
        if item.get("action") == "add_app":
            box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=0
            )
            box.set_halign(Gtk.Align.CENTER)
            box.set_valign(Gtk.Align.CENTER)

            plus = Gtk.Label(label="+")
            plus.set_name("plus-symbol")
            box.pack_start(plus, False, False, 0)

            caption = Gtk.Label(label="App hinzufügen")
            caption.set_name("plus-caption")
            box.pack_start(caption, False, False, 0)
            return box

        content = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=7
        )

        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)

        if item.get("special_icon") == "youtube":
            icon_widget = YouTubeLogo()
        else:
            icon_widget = self.load_app_icon(item)

        if icon_widget:
            content.pack_start(icon_widget, False, False, 0)

        text_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0
        )
        text_box.set_valign(Gtk.Align.CENTER)

        name = Gtk.Label(label=item["name"])
        name.set_name("app-text")
        name.set_halign(Gtk.Align.START)
        name.set_ellipsize(3)
        name.set_max_width_chars(11)

        text_box.pack_start(name, False, False, 0)

        subtitle_text = item.get("subtitle", "")
        if subtitle_text:
            subtitle = Gtk.Label(label=subtitle_text)
            subtitle.set_name("app-subtitle")
            subtitle.set_halign(Gtk.Align.START)
            subtitle.set_ellipsize(3)
            subtitle.set_max_width_chars(12)
            text_box.pack_start(subtitle, False, False, 0)

        content.pack_start(text_box, False, False, 0)
        return content

    def load_app_icon(self, item):
        icon_file = item.get("icon_file")

        if icon_file and os.path.isfile(icon_file):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_file,
                    APP_ICON_SIZE,
                    APP_ICON_SIZE,
                    True
                )
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                pass

        icon_name = item.get("icon")

        if icon_name:
            try:
                pixbuf = self.icon_theme.load_icon(
                    icon_name,
                    APP_ICON_SIZE,
                    0
                )
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                pass

        try:
            pixbuf = self.icon_theme.load_icon(
                "application-x-executable",
                APP_ICON_SIZE,
                0
            )
            return Gtk.Image.new_from_pixbuf(pixbuf)
        except Exception:
            return None


    def create_app_rows(self, root):
        self.app_row_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=APP_SPACING
        )
        self.app_row_box.set_halign(Gtk.Align.CENTER)

        self.rows.append([])
        root.pack_start(self.app_row_box, False, False, 0)
        self.render_app_carousel()

    def launcher_items(self):
        plus_item = {
            "name": "App hinzufügen",
            "subtitle": "",
            "command": None,
            "class": "add-app",
            "action": "add_app"
        }
        return list(APPS) + list(self.custom_apps) + [plus_item]

    def render_app_carousel(self):
        if self.app_row_box is None:
            return

        items = self.launcher_items()
        if not items:
            return

        self.app_index = max(0, min(self.app_index, len(items) - 1))

        if self.app_index < self.app_view_start:
            self.app_view_start = self.app_index
        elif self.app_index >= self.app_view_start + APPS_PER_ROW:
            self.app_view_start = self.app_index - APPS_PER_ROW + 1

        max_start = max(0, len(items) - APPS_PER_ROW)
        self.app_view_start = max(0, min(self.app_view_start, max_start))

        for child in self.app_row_box.get_children():
            self.app_row_box.remove(child)

        visible = items[
            self.app_view_start:
            self.app_view_start + APPS_PER_ROW
        ]

        buttons = []
        for item in visible:
            button = Gtk.Button()
            if item.get("action") == "add_app":
                button.set_name("add-app")
            else:
                button.set_name(item.get("class", "app"))
            button.set_size_request(APP_CARD_WIDTH, APP_HEIGHT)
            button.add(self.create_app_content(item))
            button.connect("clicked", self.activate_item, item)
            self.app_row_box.pack_start(button, False, False, 0)
            buttons.append(button)

        self.rows[0] = buttons
        self.current_col = self.app_index - self.app_view_start

        self.app_row_box.show_all()

    def load_launcher_apps(self):
        if not os.path.isfile(self.launcher_apps_file):
            return []
        try:
            with open(self.launcher_apps_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            clean = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                if not item.get("name") or not item.get("command"):
                    continue
                clean.append(item)
            return clean
        except Exception:
            return []

    def save_launcher_apps(self):
        try:
            tmp = self.launcher_apps_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    self.custom_apps,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            os.replace(tmp, self.launcher_apps_file)
        except Exception:
            pass

    def desktop_exec_to_command(self, exec_line):
        try:
            raw = shlex.split(exec_line)
        except Exception:
            return None

        result = []
        for token in raw:
            if re.fullmatch(r"%[fFuUdDnNickvm]", token):
                continue
            token = re.sub(r"%[fFuUdDnNickvm]", "", token)
            if token:
                result.append(token)

        return result or None

    def discover_installed_apps(self):
        paths = [
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications")
        ]

        existing_names = {
            x.get("name", "").strip().lower()
            for x in (list(APPS) + list(self.custom_apps))
        }
        existing_desktops = {
            x.get("desktop_id", "")
            for x in self.custom_apps
            if x.get("desktop_id")
        }

        found = {}
        for directory in paths:
            if not os.path.isdir(directory):
                continue

            for filename in sorted(os.listdir(directory)):
                if not filename.endswith(".desktop"):
                    continue

                full = os.path.join(directory, filename)
                parser = configparser.ConfigParser(
                    interpolation=None,
                    strict=False
                )

                try:
                    parser.read(full, encoding="utf-8")
                    if "Desktop Entry" not in parser:
                        continue
                    sec = parser["Desktop Entry"]

                    if sec.get("Type", "Application") != "Application":
                        continue
                    if sec.getboolean("Hidden", fallback=False):
                        continue
                    if sec.getboolean("NoDisplay", fallback=False):
                        continue
                    if sec.getboolean("Terminal", fallback=False):
                        continue

                    name = sec.get("Name", "").strip()
                    exec_line = sec.get("Exec", "").strip()
                    if not name or not exec_line:
                        continue
                    if name.lower() in existing_names:
                        continue
                    if filename in existing_desktops:
                        continue

                    command = self.desktop_exec_to_command(exec_line)
                    if not command:
                        continue

                    stem = os.path.splitext(filename)[0]
                    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", stem).strip("-").lower()
                    if not safe:
                        safe = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:12]

                    icon_value = sec.get("Icon", "").strip()
                    startup_class = sec.get("StartupWMClass", "").strip()
                    executable = os.path.basename(command[0])

                    item = {
                        "name": name,
                        "subtitle": "",
                        "command": command,
                        "class": "desktop-" + safe,
                        "match": list(dict.fromkeys(
                            x for x in [
                                startup_class,
                                stem,
                                filename,
                                executable
                            ] if x
                        )),
                        "desktop_id": filename
                    }

                    if icon_value:
                        if os.path.isabs(icon_value):
                            item["icon_file"] = icon_value
                        else:
                            item["icon"] = icon_value
                    else:
                        item["icon"] = "application-x-executable"

                    found[filename] = item
                except Exception:
                    continue

        return sorted(
            found.values(),
            key=lambda x: x.get("name", "").lower()
        )

    def show_app_picker(self):
        if self.app_picker_window is not None:
            self.app_picker_window.present()
            return

        items = self.discover_installed_apps()
        if not items:
            self.message("Keine weiteren Anwendungen gefunden.")
            return

        self.app_picker_items = items
        self.app_picker_buttons = []
        self.app_picker_index = 0

        w = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.app_picker_window = w
        w.set_title("App hinzufügen")
        w.set_transient_for(self)
        w.set_modal(True)
        w.set_decorated(False)
        w.fullscreen()
        w.set_name("app-picker")
        w.connect("destroy", self.on_app_picker_destroy)
        w.connect("key-press-event", self.on_app_picker_key)

        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8
        )
        outer.set_margin_top(20)
        outer.set_margin_bottom(16)
        outer.set_margin_start(24)
        outer.set_margin_end(24)
        w.add(outer)

        title = Gtk.Label(label="App hinzufügen")
        title.set_name("task-title")
        title.set_halign(Gtk.Align.START)
        outer.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(
            label="Installierte Anwendung auswählen"
        )
        subtitle.set_name("picker-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        outer.pack_start(subtitle, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )
        outer.pack_start(scroll, True, True, 0)

        list_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=5
        )
        scroll.add(list_box)

        for i, item in enumerate(items):
            b = Gtk.Button()
            b.set_name("picker-item")
            b.set_size_request(-1, 54)

            row = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=12
            )

            icon = self.load_app_icon(item)
            if icon:
                row.pack_start(icon, False, False, 6)

            label = Gtk.Label(label=item["name"])
            label.set_name("picker-name")
            label.set_halign(Gtk.Align.START)
            row.pack_start(label, True, True, 0)

            b.add(row)
            b.connect("clicked", self.add_installed_app, i)
            list_box.pack_start(b, False, False, 0)
            self.app_picker_buttons.append(b)

        footer = Gtk.Label(
            label="↑ ↓ Auswählen    OK Hinzufügen    ↩ Abbrechen"
        )
        footer.set_name("footer")
        footer.set_halign(Gtk.Align.START)
        outer.pack_end(footer, False, False, 0)

        w.show_all()
        self.app_picker_buttons[0].grab_focus()

    def on_app_picker_destroy(self, widget):
        self.app_picker_window = None
        self.app_picker_buttons = []
        self.app_picker_items = []
        self.app_picker_index = 0
        self.focus_current()

    def focus_app_picker(self):
        if not self.app_picker_buttons:
            return
        self.app_picker_index = max(
            0,
            min(self.app_picker_index, len(self.app_picker_buttons) - 1)
        )
        self.app_picker_buttons[self.app_picker_index].grab_focus()

    def on_app_picker_key(self, widget, event):
        key = Gdk.keyval_name(event.keyval)

        if key in ("Down", "Right"):
            if self.app_picker_index < len(self.app_picker_buttons) - 1:
                self.app_picker_index += 1
            self.focus_app_picker()

        elif key in ("Up", "Left"):
            if self.app_picker_index > 0:
                self.app_picker_index -= 1
            self.focus_app_picker()

        elif key in ("Return", "KP_Enter"):
            if self.app_picker_buttons:
                self.app_picker_buttons[self.app_picker_index].clicked()

        elif key in ("Escape", "BackSpace"):
            widget.destroy()

        return True

    def add_installed_app(self, button, index):
        if index < 0 or index >= len(self.app_picker_items):
            return

        item = dict(self.app_picker_items[index])
        self.custom_apps.append(item)
        self.save_launcher_apps()
        self.reconcile_workspace_map()
        self.write_workspace_rules()

        if self.app_picker_window is not None:
            self.app_picker_window.destroy()

        # Select the newly added app.  The + tile remains last.
        self.app_index = len(APPS) + len(self.custom_apps) - 1
        self.current_row = 0
        self.render_app_carousel()
        self.focus_current()

    def create_system_icon(self, item):
        special = item.get("special_icon")

        if special:
            return SystemSymbol(special)

        icon_name = item.get("icon")

        if icon_name:
            try:
                pixbuf = self.icon_theme.load_icon(
                    icon_name,
                    SYSTEM_ICON_SIZE,
                    0
                )
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                pass

        return None

    def create_system_row(self, root):
        row_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=SYSTEM_SPACING
        )

        row_buttons = []

        for item in SYSTEM_APPS:
            button = Gtk.Button()
            button.set_name("system")
            button.set_size_request(0, SYSTEM_HEIGHT)

            content = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=3
            )

            content.set_halign(Gtk.Align.CENTER)
            content.set_valign(Gtk.Align.CENTER)

            icon = self.create_system_icon(item)

            if icon:
                content.pack_start(icon, False, False, 0)

            label = Gtk.Label(label=item["name"])
            label.set_name("system-text")

            content.pack_start(label, False, False, 0)
            button.add(content)

            button.connect(
                "clicked",
                self.activate_item,
                item
            )

            row_box.pack_start(
                button,
                True,
                True,
                0
            )

            row_buttons.append(button)

        self.rows.append(row_buttons)
        root.pack_start(row_box, False, False, 0)

    def load_css(self):
        css = b"""
        #launcher {
            background-color: #000000;
        }

        #main-title {
            color: white;
            font-size: 25px;
            font-weight: bold;
        }

        #clock {
            color: white;
            font-size: 19px;
            font-weight: bold;
        }

        #section-title {
            color: white;
            font-size: 18px;
            font-weight: bold;
            margin-top: 4px;
        }

        button {
            border-radius: 10px;
            border: 2px solid rgba(90,120,145,0.75);
            box-shadow: none;
        }

        button:focus {
            border: 4px solid #9cff1a;
            box-shadow: 0px 0px 8px rgba(130,255,0,0.90);
        }

        #vlc {
            background: linear-gradient(to bottom, #ee7900, #a84200);
        }

        #vlc:focus {
            background: linear-gradient(to bottom, #ff8a00, #b94b00);
        }

        #youtube {
            background: linear-gradient(to bottom, #ffffff, #e3e3e3);
            color: #050505;
        }

        #youtube:focus {
            background: #ffffff;
        }

        #kodi {
            background: linear-gradient(to bottom, #087cce, #074d93);
        }

        #kodi:focus {
            background: linear-gradient(to bottom, #1598ec, #0862af);
        }

        #nordvpn {
            background: linear-gradient(to bottom, #123f8c, #071c50);
        }

        #nordvpn:focus {
            background: linear-gradient(to bottom, #1956b9, #09296d);
        }

        #app {
            background: rgba(26, 43, 58, 0.95);
        }

        #add-app {
            background: linear-gradient(to bottom, rgba(27,53,42,0.98), rgba(8,24,19,0.98));
            border: 2px solid rgba(106,150,123,0.85);
        }

        #add-app:focus {
            background: linear-gradient(to bottom, rgba(42,82,61,0.98), rgba(12,39,27,0.98));
            border: 4px solid #9cff1a;
            box-shadow: 0px 0px 8px rgba(130,255,0,0.90);
        }

        #plus-symbol {
            color: #9cff1a;
            font-size: 42px;
            font-weight: bold;
        }

        #plus-caption {
            color: white;
            font-size: 11px;
            font-weight: bold;
        }

        #app:focus {
            background: rgba(48, 82, 105, 0.98);
        }

        #app-text {
            color: white;
            font-size: 17px;
            font-weight: bold;
        }

        #app-subtitle {
            color: rgba(255, 255, 255, 0.90);
            font-size: 11px;
        }

        #youtube #app-text {
            color: #050505;
        }

        #youtube #app-subtitle {
            color: #333333;
        }


        #task-window {
            background-color: #000000;
        }

        #task-title {
            color: white;
            font-size: 26px;
            font-weight: bold;
        }

        #task-card {
            background-color: rgba(12, 24, 34, 0.96);
            border: 2px solid rgba(90,120,145,0.75);
            border-radius: 12px;
        }

        #task-card:focus {
            border: 4px solid #9cff1a;
            box-shadow: 0px 0px 10px rgba(130,255,0,0.90);
        }

        #task-name {
            color: white;
            font-size: 13px;
            font-weight: bold;
        }

        #task-appid {
            color: #9db0bd;
            font-size: 12px;
        }

        #task-active {
            color: #9cff1a;
            font-size: 9px;
            font-weight: bold;
        }

        #task-inactive {
            color: #8b9aa5;
            font-size: 9px;
            font-weight: bold;
        }

        #app-picker {
            background-color: #000000;
        }

        #picker-subtitle {
            color: #9db0bd;
            font-size: 13px;
        }

        #picker-item {
            background: rgba(18, 32, 44, 0.96);
            border: 2px solid rgba(84, 110, 132, 0.75);
            border-radius: 9px;
        }

        #picker-item:focus {
            background: rgba(42, 68, 85, 0.98);
            border: 4px solid #9cff1a;
        }

        #picker-name {
            color: white;
            font-size: 15px;
            font-weight: bold;
        }

        #task-delete {
            color: #ff3b30;
            font-size: 20px;
            font-weight: bold;
        }

        #system {
            background: rgba(18, 32, 44, 0.93);
            border: 2px solid rgba(84, 110, 132, 0.75);
        }

        #system:focus {
            background: rgba(42, 68, 85, 0.98);
            border: 4px solid #9cff1a;
        }

        #system-text {
            color: white;
            font-size: 13px;
            font-weight: bold;
        }

        #footer {
            color: #dddddd;
            font-size: 12px;
        }

        #remove-confirm {
            background-color: #061018;
            border: 3px solid #607787;
        }

        #remove-title {
            color: white;
            font-size: 21px;
            font-weight: bold;
        }

        #remove-note {
            color: #b8c6cf;
            font-size: 12px;
        }

        #remove-choice {
            background: #162836;
            color: white;
            border: 2px solid #607787;
            border-radius: 8px;
            font-size: 15px;
            font-weight: bold;
        }

        #remove-choice:focus {
            border: 4px solid #9cff1a;
            box-shadow: 0px 0px 8px rgba(130,255,0,0.90);
        }

        #osk-root {
            background-color: rgba(2, 8, 12, 0.98);
            border-top: 2px solid #7ea0b4;
        }

        #osk-title {
            color: #dce8ee;
            font-size: 11px;
            font-weight: bold;
        }

        #osk-key {
            background: rgba(25, 43, 56, 0.98);
            color: white;
            border: 2px solid #587080;
            border-radius: 6px;
            font-size: 13px;
            font-weight: bold;
            padding: 1px;
        }

        #osk-key.osk-selected {
            background: rgba(52, 83, 101, 1.0);
            border: 4px solid #9cff1a;
            box-shadow: 0px 0px 8px rgba(130,255,0,0.90);
        }

        #footer-separator {
            background-color: rgba(160, 180, 190, 0.25);
            min-height: 1px;
        }
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def update_clock(self):
        self.clock.set_text(
            datetime.datetime.now().strftime("%H:%M")
        )
        return True


    def focus_current(self):
        if not self.rows:
            return

        self.current_row = max(0, min(self.current_row, len(self.rows) - 1))

        if self.current_row == 0:
            self.render_app_carousel()
            if self.rows[0]:
                self.current_col = max(
                    0,
                    min(self.current_col, len(self.rows[0]) - 1)
                )
                self.rows[0][self.current_col].grab_focus()
            return

        row = self.rows[self.current_row]
        if not row:
            return

        self.current_col = max(0, min(self.current_col, len(row) - 1))
        row[self.current_col].grab_focus()


    def move_vertical(self, direction):
        if direction > 0 and self.current_row == 0 and len(self.rows) > 1:
            visible_count = max(1, len(self.rows[0]))
            local = self.app_index - self.app_view_start
            position = local / max(1, visible_count - 1)

            self.current_row = 1
            new_row = self.rows[1]
            self.current_col = round(position * max(0, len(new_row) - 1))
            return

        if direction < 0 and self.current_row == 1:
            old_row = self.rows[1]
            position = self.current_col / max(1, len(old_row) - 1)

            self.current_row = 0
            visible_count = min(
                APPS_PER_ROW,
                len(self.launcher_items()) - self.app_view_start
            )
            local = round(position * max(0, visible_count - 1))
            self.app_index = min(
                len(self.launcher_items()) - 1,
                self.app_view_start + local
            )
            self.current_col = self.app_index - self.app_view_start



    def _is_custom_launcher_class(self, app_class):
        return any(x.get("class") == app_class for x in self.custom_apps)

    def on_key(self, widget, event):
        key = Gdk.keyval_name(event.keyval)

        if self.current_row == 0:
            items = self.launcher_items()

            if key == "Right":
                if self.app_index < len(items) - 1:
                    self.app_index += 1
                self.render_app_carousel()
                self.focus_current()

            elif key == "Left":
                if self.app_index > 0:
                    self.app_index -= 1
                self.render_app_carousel()
                self.focus_current()

            elif key == "Down":
                if len(self.rows) > 1:
                    self.move_vertical(1)
                self.focus_current()

            elif key in ("Return", "KP_Enter"):
                if not items or not self.rows[0]:
                    return True
                item = items[self.app_index]
                app_class = item.get("class")

                # Only user-added applications are removable.  For those apps
                # the action happens on key release so a long press can be
                # distinguished without ever launching the app first.
                if self._is_custom_launcher_class(app_class):
                    if self._ok_press_started is None:
                        self._ok_press_started = time.monotonic()
                        self._ok_press_class = app_class
                    return True

                self.rows[0][self.current_col].clicked()

            elif key in ("Escape", "BackSpace"):
                self._show_black_workspace()
                self.iconify()
                self.launcher_foreground = False

            return True

        row = self.rows[self.current_row]

        if key == "Right":
            if self.current_col < len(row) - 1:
                self.current_col += 1
            self.focus_current()

        elif key == "Left":
            if self.current_col > 0:
                self.current_col -= 1
            self.focus_current()

        elif key == "Up":
            if self.current_row > 0:
                self.move_vertical(-1)
            self.focus_current()

        elif key == "Down":
            if self.current_row < len(self.rows) - 1:
                self.current_row += 1
            self.focus_current()

        elif key in ("Return", "KP_Enter"):
            row[self.current_col].clicked()

        elif key in ("Escape", "BackSpace"):
            self.show_launcher()

        return True

    def on_key_release(self, widget, event):
        key = Gdk.keyval_name(event.keyval)
        if key not in ("Return", "KP_Enter"):
            return False
        if self._ok_press_started is None:
            return False

        started = self._ok_press_started
        app_class = self._ok_press_class
        self._ok_press_started = None
        self._ok_press_class = None
        held = time.monotonic() - started

        item = next(
            (x for x in self.custom_apps if x.get("class") == app_class),
            None
        )
        if item is None:
            return True

        if held >= self.ok_hold_threshold:
            self.show_remove_confirmation(item)
            return True

        # Short OK: normal app start/activation.
        items = self.launcher_items()
        if 0 <= self.app_index < len(items) and items[self.app_index].get("class") == app_class:
            local = self.app_index - self.app_view_start
            if 0 <= local < len(self.rows[0]):
                self.rows[0][local].clicked()
        return True

    def show_remove_confirmation(self, item):
        if self.remove_confirm_window is not None:
            return

        self.remove_confirm_item = dict(item)
        self.remove_confirm_choice = 0  # Nein is deliberately the default.

        w = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.remove_confirm_window = w
        w.set_title("App entfernen")
        w.set_transient_for(self)
        w.set_modal(True)
        w.set_decorated(False)
        w.set_default_size(470, 190)
        w.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        w.set_name("remove-confirm")
        w.connect("destroy", self._on_remove_confirm_destroy)
        w.connect("key-press-event", self._on_remove_confirm_key)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_border_width(22)
        w.add(box)

        title = Gtk.Label(label=(item.get("name") or "Anwendung") + " entfernen?")
        title.set_name("remove-title")
        box.pack_start(title, False, False, 0)

        note = Gtk.Label(label="Nur aus dem Shield Launcher entfernen – nicht deinstallieren.")
        note.set_name("remove-note")
        box.pack_start(note, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        row.set_halign(Gtk.Align.CENTER)
        no_btn = Gtk.Button(label="Nein")
        yes_btn = Gtk.Button(label="Ja, entfernen")
        no_btn.set_name("remove-choice")
        yes_btn.set_name("remove-choice")
        no_btn.set_size_request(150, 54)
        yes_btn.set_size_request(190, 54)
        no_btn.connect("clicked", lambda _b: self._remove_confirm_select(False))
        yes_btn.connect("clicked", lambda _b: self._remove_confirm_select(True))
        row.pack_start(no_btn, False, False, 0)
        row.pack_start(yes_btn, False, False, 0)
        box.pack_end(row, False, False, 0)

        self.remove_confirm_buttons = [no_btn, yes_btn]
        w.show_all()
        self._focus_remove_confirm()

    def _focus_remove_confirm(self):
        if not self.remove_confirm_buttons:
            return
        self.remove_confirm_choice = max(0, min(self.remove_confirm_choice, 1))
        self.remove_confirm_buttons[self.remove_confirm_choice].grab_focus()

    def _on_remove_confirm_key(self, widget, event):
        key = Gdk.keyval_name(event.keyval)
        if key in ("Left", "Right"):
            self.remove_confirm_choice = 1 - self.remove_confirm_choice
            self._focus_remove_confirm()
        elif key in ("Return", "KP_Enter"):
            self._remove_confirm_select(self.remove_confirm_choice == 1)
        elif key in ("Escape", "BackSpace"):
            widget.destroy()
        return True

    def _remove_confirm_select(self, remove):
        item = self.remove_confirm_item
        if self.remove_confirm_window is not None:
            self.remove_confirm_window.destroy()
        if remove and item:
            self.remove_custom_launcher_app(item)

    def _on_remove_confirm_destroy(self, widget):
        self.remove_confirm_window = None
        self.remove_confirm_buttons = []
        self.remove_confirm_item = None
        self.remove_confirm_choice = 0
        self.focus_current()

    def remove_custom_launcher_app(self, item):
        app_class = item.get("class")
        if not app_class or not self._is_custom_launcher_class(app_class):
            return

        # If it is running, close its toplevel first and then its process tree.
        active = self.find_running_for_class(app_class)
        if active:
            try:
                subprocess.run(
                    [
                        SHIELD_TASKS_HELPER,
                        "close",
                        active.get("app_id")
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
            except Exception:
                pass
            self.kill_app_processes(app_class)

        old_index = self.app_index
        self.custom_apps = [
            x for x in self.custom_apps if x.get("class") != app_class
        ]
        self.save_launcher_apps()
        self.remove_recent_entry(app_class)

        self.workspace_map.pop(app_class, None)
        self.save_workspace_map()
        self.reconcile_workspace_map()
        self.write_workspace_rules()

        items = self.launcher_items()
        self.app_index = max(0, min(old_index, len(items) - 1))
        self.app_view_start = max(0, min(self.app_view_start, max(0, len(items) - APPS_PER_ROW)))
        self.current_row = 0
        self.render_app_carousel()
        self.focus_current()

    def activate_item(self, button, item):
        action = item.get("action")
        command = item.get("command")

        if action == "add_app":
            self.show_app_picker()
            return

        if action == "systeminfo":
            self.show_system_info()
            return

        if action == "quit_launcher":
            if self.task_window is not None:
                try:
                    self.task_window.destroy()
                except Exception:
                    pass

            opens = self.get_open_tasks(silent=True)
            for e in list(self.recent_tasks):
                t = self.find_active_task(e, opens)
                if t:
                    try:
                        subprocess.run(
                            [
                                SHIELD_TASKS_HELPER,
                                "close",
                                t.get("app_id")
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=2
                        )
                    except Exception:
                        pass
                self.kill_app_processes(e.get("class"))

            self.recent_tasks = []
            self.save_recent_tasks()
            self.foreground_task_class = None

            # Only explicit "Launcher beenden" restores the Raspberry Pi desktop.
            self.hide_osk()
            self._release_osk_remote_device()
            self._restore_desktop_chrome()
            Gtk.main_quit()
            return

        if command is None:
            self.message(item["name"] + " ist noch nicht eingerichtet.")
            return

        if command and command[0] == "systemctl":
            self.sync_task_states()
            try:
                subprocess.Popen(command)
            except Exception as e:
                self.message("Startfehler:\n" + str(e))
            return

        try:
            app_class = item.get("class")
            self.launcher_foreground = False
            self._hide_desktop_chrome()
            self._show_black_workspace()
            self.iconify()
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)

            ok = self.launch_or_activate(app_class, command=command)
            if not ok:
                self.show_launcher()
                self.message("Startfehler: Anwendung konnte nicht gestartet werden.")
        except Exception as e:
            self.show_launcher()
            self.message("Startfehler:\n" + str(e))



    def load_workspace_map(self):
        if not os.path.isfile(self.workspace_file):
            return {}
        try:
            with open(self.workspace_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return {}

        out = {}
        if isinstance(raw, dict):
            for cls, value in raw.items():
                if not cls:
                    continue
                if isinstance(value, int):
                    out[cls] = {"workspace": value, "app_id": ""}
                elif isinstance(value, dict):
                    try:
                        ws = int(value.get("workspace", 0))
                    except Exception:
                        ws = 0
                    if ws >= 2:
                        out[cls] = {
                            "workspace": ws,
                            "app_id": str(value.get("app_id") or "")
                        }
        return out

    def save_workspace_map(self):
        try:
            tmp = self.workspace_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.workspace_map, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.workspace_file)
        except Exception:
            pass

    def managed_app_configs(self):
        return [
            x for x in (list(APPS) + list(self.custom_apps))
            if x.get("class") and x.get("command") is not None
        ]

    def reconcile_workspace_map(self):
        valid = {x.get("class") for x in self.managed_app_configs()}
        cleaned = {}
        used = set()

        for cls, entry in list(self.workspace_map.items()):
            if cls not in valid or not isinstance(entry, dict):
                continue
            try:
                ws = int(entry.get("workspace", 0))
            except Exception:
                ws = 0
            if ws < 2 or ws in used:
                continue
            cleaned[cls] = {
                "workspace": ws,
                "app_id": str(entry.get("app_id") or "")
            }
            used.add(ws)

        self.workspace_map = cleaned

        for cfg in self.managed_app_configs():
            cls = cfg.get("class")
            if cls not in self.workspace_map:
                ws = 2
                while ws in used:
                    ws += 1
                self.workspace_map[cls] = {
                    "workspace": ws,
                    "app_id": KNOWN_APP_IDS.get(cls, "")
                }
                used.add(ws)
            elif not self.workspace_map[cls].get("app_id"):
                known = KNOWN_APP_IDS.get(cls)
                if known:
                    self.workspace_map[cls]["app_id"] = known

        self.save_workspace_map()

    def ensure_workspace(self, app_class):
        if not app_class:
            return 1

        entry = self.workspace_map.get(app_class)
        if isinstance(entry, dict):
            try:
                ws = int(entry.get("workspace", 0))
                if ws >= 2:
                    return ws
            except Exception:
                pass

        used = set()
        for value in self.workspace_map.values():
            if not isinstance(value, dict):
                continue
            try:
                ws = int(value.get("workspace", 0))
            except Exception:
                continue
            if ws >= 2:
                used.add(ws)

        ws = 2
        while ws in used:
            ws += 1

        self.workspace_map[app_class] = {
            "workspace": ws,
            "app_id": KNOWN_APP_IDS.get(app_class, "")
        }
        self.save_workspace_map()
        return ws

    def _rule_identifiers_for_class(self, app_class):
        ids = []
        entry = self.workspace_map.get(app_class) or {}
        learned = str(entry.get("app_id") or "").strip()
        if learned:
            ids.append(learned)

        cfg = self.app_config(app_class) or {}
        for token in cfg.get("match", []) or []:
            token = str(token).strip()
            if token:
                ids.append(token)

        return list(dict.fromkeys(ids))

    def _reload_labwc(self):
        try:
            pid = subprocess.check_output(
                ["pidof", "labwc"],
                text=True,
                timeout=2
            ).strip().split()[0]
        except Exception:
            return False

        env = os.environ.copy()
        env["LABWC_PID"] = pid
        try:
            r = subprocess.run(
                ["labwc", "-r"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3
            )
            return r.returncode == 0
        except Exception:
            return False

    def write_workspace_rules(self):
        try:
            with open(LABWC_RC, "r", encoding="utf-8") as f:
                rc = f.read()
        except Exception:
            return False

        rc = re.sub(
            r"\s*<!-- SHIELD-AUTO-WORKSPACES-BEGIN -->.*?"
            r"<!-- SHIELD-AUTO-WORKSPACES-END -->\s*",
            "\n",
            rc,
            flags=re.S
        )

        # Remove the earlier manual Shield test block, but leave unrelated rules intact.
        rc = re.sub(
            r"\s*<!--\s*Shield App Workspaces\s*-->\s*"
            r"<windowRules>.*?</windowRules>\s*",
            "\n",
            rc,
            flags=re.S | re.I
        )

        rules = [
            "    " + WORKSPACE_AUTO_BEGIN,
            '    <windowRule identifier="%s">' % xml_escape(LAUNCHER_APP_ID, quote=True),
            '      <action name="SendToDesktop" to="1" follow="yes" />',
            "    </windowRule>",
        ]

        for cfg in self.managed_app_configs():
            cls = cfg.get("class")
            ws = self.ensure_workspace(cls)
            for ident in self._rule_identifiers_for_class(cls):
                if not ident or ident == LAUNCHER_APP_ID:
                    continue
                rules.extend([
                    '    <windowRule identifier="%s">' % xml_escape(ident, quote=True),
                    '      <action name="SendToDesktop" to="%d" follow="yes" />' % ws,
                    "    </windowRule>",
                ])

        rules.append("    " + WORKSPACE_AUTO_END)
        block = "\n".join(rules) + "\n"

        m = re.search(r"</windowRules>", rc, flags=re.I)
        if m:
            rc = rc[:m.start()] + block + rc[m.start():]
        else:
            wrapper = "  <windowRules>\n" + block + "  </windowRules>\n"
            close = re.search(r"</openbox_config>", rc, flags=re.I)
            if not close:
                return False
            rc = rc[:close.start()] + wrapper + rc[close.start():]

        try:
            tmp = LABWC_RC + ".shield.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(rc)
            os.replace(tmp, LABWC_RC)
        except Exception:
            return False

        self._reload_labwc()
        return True

    def learn_app_id(self, app_class, app_id):
        app_id = (app_id or "").strip()
        if not app_class or not app_id or app_id == LAUNCHER_APP_ID:
            return

        self.ensure_workspace(app_class)
        entry = self.workspace_map.setdefault(
            app_class,
            {"workspace": self.ensure_workspace(app_class), "app_id": ""}
        )

        if entry.get("app_id") != app_id:
            entry["app_id"] = app_id
            self.save_workspace_map()
            self.write_workspace_rules()

    def discover_new_window(self, app_class, before_ids, attempts=0, command=None):
        opens = self.get_open_tasks(silent=True)
        e = self.ensure_recent_entry(app_class)
        t = self.find_active_task(e, opens)
        learned_by_fallback = False

        if t is None:
            candidates = [
                x for x in opens
                if (x.get("app_id") or "") not in before_ids
                and (x.get("app_id") or "") != LAUNCHER_APP_ID
            ]
            if len(candidates) == 1:
                t = candidates[0]
                learned_by_fallback = True

        if t is not None:
            aid = t.get("app_id", "")
            e["window_app_id"] = aid
            e["title"] = t.get("title") or e.get("name")
            e["was_active"] = True
            self.save_recent_tasks()
            self.learn_app_id(app_class, aid)

            if learned_by_fallback and command:
                try:
                    subprocess.run(
                        [
                            SHIELD_TASKS_HELPER,
                            "close",
                            aid
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2
                    )
                except Exception:
                    pass

                self.kill_app_processes(app_class)
                GLib.timeout_add(
                    450,
                    self._restart_after_learning,
                    app_class,
                    list(command)
                )
            return False

        if attempts < 12:
            GLib.timeout_add(
                250,
                self.discover_new_window,
                app_class,
                before_ids,
                attempts + 1,
                command
            )
        return False

    def _restart_after_learning(self, app_class, command):
        try:
            subprocess.Popen(command)
            self.foreground_task_class = app_class
        except Exception:
            self.show_launcher()
        return False

    def _ensure_black_workspace(self):
        # No artificial black overlay window. Empty labwc workspaces are black
        # once PCManFM desktop and wf-panel-pi are stopped.
        return

    def _show_black_workspace(self):
        self._hide_desktop_chrome()

    def _hide_black_workspace(self):
        return

    def show_launcher(self):
        # The normal Raspberry Pi desktop stays suppressed for the whole
        # Shield session. Presenting this window also returns labwc to workspace 1.
        self._hide_desktop_chrome()
        self.deiconify()
        self.present()
        self.fullscreen()
        self.launcher_foreground = True
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        self.focus_current()

    def app_config(self, app_class):
        return next(
            (
                x for x in (list(APPS) + list(self.custom_apps))
                if x.get("class") == app_class
            ),
            None
        )

    def ensure_recent_entry(self, app_class):
        if not app_class:
            return {"class": "", "name": "", "window_app_id": "", "title": "", "thumbnail": "", "was_active": False}
        for e in self.recent_tasks:
            if e.get("class") == app_class:
                return e
        # Defensive: remove any accidental duplicates of this class
        self.recent_tasks = [e for e in self.recent_tasks if e.get("class") != app_class]
        cfg = self.app_config(app_class) or {}
        e = {
            "class": app_class,
            "name": cfg.get("name", app_class),
            "window_app_id": "",
            "title": cfg.get("name", app_class),
            "thumbnail": os.path.join(self.thumb_dir, app_class + ".png"),
            "was_active": False
        }
        self.recent_tasks.append(e)
        return e

    def load_recent_tasks(self):
        if not os.path.isfile(self.state_file):
            return []
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            out = []
            seen = set()
            for x in data:
                if not isinstance(x, dict) or not x.get("was_active"):
                    continue
                cls = x.get("class")
                if not cls or cls in seen:
                    continue
                seen.add(cls)
                out.append(x)
            return out
        except Exception:
            return []

    def mark_restored_tasks_inactive(self):
        for e in self.recent_tasks: e["was_active"]=False
        self.save_recent_tasks()

    def save_recent_tasks(self):
        try:
            tmp=self.state_file+".tmp"
            with open(tmp,"w",encoding="utf-8") as f: json.dump(self.recent_tasks,f,ensure_ascii=False,indent=2)
            os.replace(tmp,self.state_file)
        except Exception: pass

    def remove_recent_entry(self, app_class):
        removed=next((e for e in self.recent_tasks if e.get("class")==app_class),None)
        self.recent_tasks=[e for e in self.recent_tasks if e.get("class")!=app_class]
        if removed:
            p=removed.get("thumbnail")
            if p and os.path.isfile(p):
                try: os.remove(p)
                except Exception: pass
        self.save_recent_tasks()


    def capture_foreground_thumbnail(self):
        if self.launcher_foreground:
            return
        if not self.foreground_task_class:
            return

        e = self.ensure_recent_entry(self.foreground_task_class)

        # Do not overwrite a good application preview with the launcher
        # if the remembered task is no longer actually open.
        active = self.find_active_task(e)
        if active is None:
            return

        p = e.get("thumbnail") or os.path.join(
            self.thumb_dir,
            self.foreground_task_class + ".png"
        )
        e["thumbnail"] = p

        tmp = p + ".new"
        env = os.environ.copy()
        env.setdefault("XDG_RUNTIME_DIR", DEFAULT_XDG_RUNTIME_DIR)
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")

        try:
            if os.path.isfile(tmp):
                os.remove(tmp)

            r = subprocess.run(
                ["/usr/bin/grim", tmp],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )

            if r.returncode == 0 and os.path.isfile(tmp):
                os.replace(tmp, p)
                e["window_app_id"] = active.get("app_id", "")
                e["title"] = active.get("title") or e.get("name")
                e["was_active"] = True
                self.save_recent_tasks()
            elif os.path.isfile(tmp):
                os.remove(tmp)
        except Exception:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    def task_matches_entry(self, task, e):
        aid = (task.get("app_id") or "").lower().strip()
        if not aid:
            return False
        saved = (e.get("window_app_id") or "").lower().strip()
        # Strongest: exact saved app_id
        if saved and aid == saved:
            return True
        cfg = self.app_config(e.get("class")) or {}
        tokens = [t.lower().strip() for t in cfg.get("match", []) if t]
        if not tokens:
            return False
        # Prefer exact or whole-token match to avoid "chrome" matching "chromium-browser" for wrong entry
        for tok in tokens:
            if not tok:
                continue
            if aid == tok:
                return True
            # app_id often looks like "vlc" or "VLC" or "org.videolan.vlc"
            if aid.endswith("." + tok) or aid.startswith(tok + ".") or ("." + tok + ".") in ("." + aid + "."):
                return True
            # last resort: token as whole word-ish substring only if token is reasonably long
            if len(tok) >= 4 and tok in aid:
                return True
        return False

    def find_active_task(self, e, open_tasks=None, used_ids=None):
        """Find an open window for this entry. used_ids prevents one window matching two tasks."""
        if used_ids is None:
            used_ids = set()
        for t in (open_tasks if open_tasks is not None else self.get_open_tasks(silent=True)):
            aid = (t.get("app_id") or "").strip()
            if aid and aid in used_ids:
                continue
            if self.task_matches_entry(t, e):
                if aid:
                    used_ids.add(aid)
                return t
        return None

    def discover_window_for_class(self,app_class):
        e=self.ensure_recent_entry(app_class); t=self.find_active_task(e)
        if t:
            e["window_app_id"]=t.get("app_id",""); e["title"]=t.get("title") or e.get("name"); e["was_active"]=True
            self.save_recent_tasks()
        return False

    def sync_task_states(self):
        opens = self.get_open_tasks(silent=True)
        changed = False
        used_ids = set()
        for e in self.recent_tasks:
            t = self.find_active_task(e, opens, used_ids=used_ids)
            active = t is not None
            if e.get("was_active") != active:
                e["was_active"] = active
                changed = True
            if t:
                if e.get("window_app_id") != t.get("app_id", ""):
                    e["window_app_id"] = t.get("app_id", "")
                    changed = True
                title = t.get("title") or e.get("name")
                if e.get("title") != title:
                    e["title"] = title
                    changed = True
        if changed:
            self.save_recent_tasks()
        return True

    def get_open_tasks(self,silent=False):
        helper=SHIELD_TASKS_HELPER
        try:
            r=subprocess.run([helper,"list"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=3)
        except Exception as e:
            if not silent: self.message("Taskmanager-Fehler:\n"+str(e))
            return []
        if r.returncode!=0:
            if not silent: self.message("Taskmanager-Fehler:\n"+(r.stderr.strip() or "shield-tasks list fehlgeschlagen"))
            return []
        out=[]; current=None
        for line in r.stdout.splitlines():
            m=re.match(r"\s*\[\d+\]\s+app_id\s+(.+?)\s+title\s+(.+)$",line)
            if m:
                aid=m.group(1).strip(); title=m.group(2).strip()
                if aid and aid not in ("(leer)","shield-launcher.py"): out.append({"app_id":aid,"title":title or aid})
                continue
            m=re.match(r"\s*app_id\s*:\s*(.*)$",line)
            if m: current=m.group(1).strip(); continue
            m=re.match(r"\s*title\s*:\s*(.*)$",line)
            if m and current:
                title=m.group(1).strip()
                if current not in ("(leer)","shield-launcher.py"): out.append({"app_id":current,"title":title if title!="(leer)" else current})
                current=None
        return out


    def show_task_manager(self):
        if self.task_window is not None:
            self.task_window.present()
            self.focus_task()
            return False

        opens = self.get_open_tasks(silent=True)
        tasks = []
        used_ids = set()
        seen_classes = set()

        for e in self.recent_tasks:
            cls = e.get("class")
            if not cls or cls in seen_classes:
                continue
            seen_classes.add(cls)
            t = self.find_active_task(e, opens, used_ids=used_ids)
            item = dict(e)
            item["active"] = t is not None
            if t:
                item["window_app_id"] = t.get("app_id", "")
                item["title"] = t.get("title") or item.get("name")
            tasks.append(item)

        if not tasks:
            self.message("Keine gespeicherten Anwendungen.")
            return False

        self.task_items = tasks
        self.task_index = max(
            0,
            min(self.task_index, len(self.task_items) - 1)
        )
        self.task_view_start = 0
        self.task_delete_mode = False
        self.task_buttons = []
        self.launcher_foreground = False

        w = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.task_window = w
        w.set_title("Shield Tasks")
        w.set_transient_for(self)
        w.set_modal(True)
        w.set_decorated(False)
        w.fullscreen()
        w.set_name("task-window")
        w.connect("key-press-event", self.on_task_key)
        w.connect("destroy", self.on_task_window_destroy)

        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )
        outer.set_margin_top(24)
        outer.set_margin_bottom(18)
        outer.set_margin_start(LEFT_MARGIN)
        outer.set_margin_end(RIGHT_MARGIN)
        w.add(outer)

        title = Gtk.Label(label="Letzte Anwendungen")
        title.set_name("task-title")
        title.set_halign(Gtk.Align.START)
        outer.pack_start(title, False, False, 0)

        self.task_cards_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=APP_SPACING
        )
        self.task_cards_box.set_halign(Gtk.Align.CENTER)
        self.task_cards_box.set_valign(Gtk.Align.CENTER)
        outer.pack_start(self.task_cards_box, True, True, 0)

        self.task_delete_label = Gtk.Label(
            label="✕  Beenden / entfernen"
        )
        self.task_delete_label.set_name("task-delete")
        self.task_delete_label.set_no_show_all(True)
        self.task_delete_label.hide()
        outer.pack_end(self.task_delete_label, False, False, 0)

        hint = Gtk.Label(
            label="← → Auswählen    OK Öffnen    ↓ Löschen    ↑ Abbrechen    Home Launcher"
        )
        hint.set_name("footer")
        outer.pack_end(hint, False, False, 0)

        w.show_all()
        self.task_delete_label.hide()
        self.render_task_cards()
        self.focus_task()
        return False

    def render_task_cards(self):
        if self.task_cards_box is None or not self.task_items:
            return

        self.task_index = max(
            0,
            min(self.task_index, len(self.task_items) - 1)
        )

        if self.task_index < self.task_view_start:
            self.task_view_start = self.task_index
        elif self.task_index >= self.task_view_start + TASKS_VISIBLE:
            self.task_view_start = self.task_index - TASKS_VISIBLE + 1

        max_start = max(0, len(self.task_items) - TASKS_VISIBLE)
        self.task_view_start = max(
            0,
            min(self.task_view_start, max_start)
        )

        for child in self.task_cards_box.get_children():
            self.task_cards_box.remove(child)

        self.task_buttons = []
        visible = self.task_items[
            self.task_view_start:
            self.task_view_start + TASKS_VISIBLE
        ]

        thumb_width = APP_CARD_WIDTH - 18
        thumb_height = 56

        for offset, t in enumerate(visible):
            global_index = self.task_view_start + offset

            b = Gtk.Button()
            b.set_name("task-card")
            b.set_size_request(APP_CARD_WIDTH, APP_HEIGHT)
            b.connect(
                "clicked",
                self.activate_task_index,
                global_index
            )

            box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=1
            )
            box.set_halign(Gtk.Align.FILL)
            box.set_valign(Gtk.Align.CENTER)

            added = False
            p = t.get("thumbnail")

            if p and os.path.isfile(p):
                try:
                    pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        p,
                        thumb_width,
                        thumb_height,
                        True
                    )
                    image = Gtk.Image.new_from_pixbuf(pix)
                    box.pack_start(image, False, False, 0)
                    added = True
                except Exception:
                    pass

            if not added:
                cfg = self.app_config(t.get("class")) or {}
                icon = self.load_app_icon(cfg) if cfg else None
                if icon:
                    box.pack_start(icon, False, False, 0)

            name = Gtk.Label(
                label=t.get("name") or t.get("title") or t.get("class")
            )
            name.set_name("task-name")
            name.set_ellipsize(3)
            name.set_max_width_chars(16)
            name.set_justify(Gtk.Justification.CENTER)
            box.pack_start(name, False, False, 0)

            st = Gtk.Label(
                label="AKTIV" if t.get("active") else "BEREIT"
            )
            st.set_name(
                "task-active" if t.get("active") else "task-inactive"
            )
            box.pack_start(st, False, False, 0)

            b.add(box)
            self.task_cards_box.pack_start(b, False, False, 0)
            self.task_buttons.append(b)

        self.task_cards_box.show_all()


    def on_task_window_destroy(self, widget):
        self.task_window = None
        self.task_buttons = []
        self.task_items = []
        self.task_delete_mode = False
        self.task_delete_label = None
        self.task_cards_box = None


    def focus_task(self):
        if not self.task_buttons or not self.task_items:
            return

        self.task_index = max(
            0,
            min(self.task_index, len(self.task_items) - 1)
        )

        if (
            self.task_index < self.task_view_start or
            self.task_index >= self.task_view_start + len(self.task_buttons)
        ):
            self.render_task_cards()

        local = self.task_index - self.task_view_start
        if 0 <= local < len(self.task_buttons):
            self.task_buttons[local].grab_focus()


    def on_task_key(self, widget, event):
        key = Gdk.keyval_name(event.keyval)

        if key == "Right" and not self.task_delete_mode:
            if self.task_index < len(self.task_items) - 1:
                self.task_index += 1
                self.render_task_cards()
                self.focus_task()

        elif key == "Left" and not self.task_delete_mode:
            if self.task_index > 0:
                self.task_index -= 1
                self.render_task_cards()
                self.focus_task()

        elif key == "Down" and self.task_items:
            self.task_delete_mode = True
            if self.task_delete_label:
                self.task_delete_label.show()

        elif key == "Up" and self.task_delete_mode:
            self.task_delete_mode = False
            if self.task_delete_label:
                self.task_delete_label.hide()
            self.focus_task()

        elif key in ("Return", "KP_Enter"):
            if self.task_delete_mode:
                self.close_selected_task()
            else:
                self.activate_task_index(None, self.task_index)

        elif key in ("Escape", "BackSpace"):
            widget.destroy()
            self.show_launcher()

        return True


    def activate_task_index(self, button, index):
        if index < 0 or index >= len(self.task_items):
            return

        item = self.task_items[index]
        app_class = item.get("class")

        if self.task_window:
            try:
                self.task_window.destroy()
            except Exception:
                pass

        cfg = self.app_config(app_class)
        # If not running and no command, cannot start
        running = self.find_running_for_class(app_class)
        if not running and (not cfg or cfg.get("command") is None):
            self.show_launcher()
            self.message(
                (item.get("name") or app_class) +
                " ist noch nicht eingerichtet."
            )
            return

        self.launcher_foreground = False
        self._hide_desktop_chrome()
        self._show_black_workspace()
        self.iconify()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

        # launch_or_activate: raises existing window OR starts once — never doubles
        ok = self.launch_or_activate(
            app_class,
            command=(cfg.get("command") if cfg else None)
        )
        if not ok:
            self.show_launcher()
            self.message("Aktivieren/Start fehlgeschlagen.")

    def kill_app_processes(self, app_class):
        """Force-kill processes belonging to this app (by match tokens / command)."""
        cfg = self.app_config(app_class) or {}
        tokens = list(cfg.get("match") or [])
        cmd = cfg.get("command")
        if cmd:
            for part in reversed(cmd):
                base = os.path.basename(str(part))
                if base and base not in ("env", "python3", "python", "bash", "sh"):
                    tokens.append(base)
                    break
        tokens = [t for t in dict.fromkeys(tokens) if t and len(t) > 1]
        for tok in tokens:
            try:
                subprocess.run(
                    ["pkill", "-9", "-f", tok],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
            except Exception:
                pass
        # Give processes a moment to die
        time.sleep(0.25)

    def _hide_desktop_chrome(self):
        """Stop the exact Raspberry Pi desktop/panel processes and their respawners."""
        commands = [
            ["pkill", "-f", "^/bin/sh /usr/bin/lwrespawn /usr/bin/pcmanfm --desktop --profile LXDE-pi$"],
            ["pkill", "-f", "^/bin/sh /usr/bin/lwrespawn /usr/bin/wf-panel-pi$"],
            ["pkill", "-f", "^/usr/bin/pcmanfm --desktop --profile LXDE-pi$"],
            ["pkill", "-x", "wf-panel-pi"],
        ]
        for cmd in commands:
            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=1
                )
            except Exception:
                pass

    def _desktop_process_running(self, pattern):
        try:
            r = subprocess.run(
                ["pgrep", "-af", pattern],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2
            )
            return bool(r.stdout.strip())
        except Exception:
            return False

    def _restore_desktop_chrome(self):
        """Restore the normal Pi desktop only when the launcher is explicitly exited."""
        if not self._desktop_process_running(
            "/usr/bin/lwrespawn /usr/bin/pcmanfm --desktop --profile LXDE-pi"
        ):
            try:
                subprocess.Popen(
                    [
                        "/usr/bin/lwrespawn",
                        "/usr/bin/pcmanfm",
                        "--desktop",
                        "--profile",
                        "LXDE-pi"
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            except Exception:
                pass

        if not self._desktop_process_running(
            "/usr/bin/lwrespawn /usr/bin/wf-panel-pi"
        ):
            try:
                subprocess.Popen(
                    ["/usr/bin/lwrespawn", "/usr/bin/wf-panel-pi"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            except Exception:
                pass

    def find_running_for_class(self, app_class):
        """Return open task dict if this app is already running, else None."""
        e = {"class": app_class, "window_app_id": ""}
        # Prefer saved window_app_id from recent entry
        for r in self.recent_tasks:
            if r.get("class") == app_class and r.get("window_app_id"):
                e["window_app_id"] = r.get("window_app_id")
                break
        return self.find_active_task(e)

    def launch_or_activate(self, app_class, command=None):
        """Activate an existing app or start it once on its persistent labwc workspace."""
        if not app_class:
            return False

        self.ensure_workspace(app_class)
        self.write_workspace_rules()

        active = self.find_running_for_class(app_class)
        if active:
            aid = active.get("app_id")
            self.foreground_task_class = app_class
            try:
                r = subprocess.run(
                    [
                        SHIELD_TASKS_HELPER,
                        "activate",
                        aid
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3
                )
                if r.returncode == 0:
                    e = self.ensure_recent_entry(app_class)
                    e["window_app_id"] = aid
                    e["was_active"] = True
                    e["title"] = active.get("title") or e.get("name")
                    self.save_recent_tasks()
                    self.learn_app_id(app_class, aid)
                    return True
            except Exception:
                pass
            return False

        cfg = self.app_config(app_class) or {}
        cmd = command or cfg.get("command")
        if not cmd:
            return False

        before_ids = {
            x.get("app_id")
            for x in self.get_open_tasks(silent=True)
            if x.get("app_id")
        }

        try:
            subprocess.Popen(cmd)
            e = self.ensure_recent_entry(app_class)
            e["was_active"] = True
            self.foreground_task_class = app_class
            self.save_recent_tasks()
            GLib.timeout_add(
                250,
                self.discover_new_window,
                app_class,
                before_ids,
                0,
                list(cmd)
            )
            return True
        except Exception:
            return False

    def close_selected_task(self):
        if not self.task_items:
            return
        item = self.task_items[self.task_index]
        app_class = item.get("class")
        active = self.find_active_task(item)

        if active:
            try:
                subprocess.run(
                    [
                        SHIELD_TASKS_HELPER,
                        "close",
                        active.get("app_id")
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3
                )
            except Exception as e:
                if self.task_window:
                    self.task_window.destroy()
                self.show_launcher()
                self.message("Schließen fehlgeschlagen:\n" + str(e))
                return

        # Always force-kill remaining processes so next start is not double
        self.kill_app_processes(app_class)

        # Verify it is gone; if still listed, kill again
        still = self.find_running_for_class(app_class)
        if still:
            self.kill_app_processes(app_class)
            try:
                subprocess.run(
                    [
                        SHIELD_TASKS_HELPER,
                        "close",
                        still.get("app_id")
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
            except Exception:
                pass

        self.remove_recent_entry(app_class)
        if self.foreground_task_class == app_class:
            self.foreground_task_class = None
        GLib.timeout_add(400, self.refresh_task_manager_after_close)


    def refresh_task_manager_after_close(self):
        old = self.task_index

        if self.task_window:
            self.task_window.destroy()

        opens = self.get_open_tasks(silent=True)

        if not any(
            self.find_active_task(e, opens)
            for e in self.recent_tasks
        ):
            self.show_launcher()
            return False

        if not self.recent_tasks:
            self.show_launcher()
            return False

        self.task_index = max(0, min(old, len(self.recent_tasks) - 1))
        self.show_task_manager()
        self.focus_task()
        return False


    # ------------------------------------------------------------------
    # Universal Shield on-screen keyboard
    # ------------------------------------------------------------------
    def _ensure_osk_remote_device(self):
        if evdev is None or ecodes is None:
            return False
        if self.osk_device is not None:
            return False

        try:
            paths = evdev.list_devices()
        except Exception:
            return True

        for path in paths:
            dev = None
            try:
                dev = evdev.InputDevice(path)
                name = (dev.name or "").strip().lower()
                if name != "input-remapper keyboard":
                    dev.close()
                    continue

                self.osk_device = dev
                self.osk_watch_id = GLib.io_add_watch(
                    dev.fd,
                    GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR,
                    self._on_osk_remote_fd
                )
                return False
            except Exception:
                try:
                    if dev is not None:
                        dev.close()
                except Exception:
                    pass
        return True

    def _on_osk_remote_fd(self, source, condition):
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            self._release_osk_remote_device()
            GLib.timeout_add_seconds(1, self._ensure_osk_remote_device)
            return False

        dev = self.osk_device
        if dev is None:
            return False

        try:
            events = dev.read()
        except BlockingIOError:
            return True
        except OSError:
            self._release_osk_remote_device()
            GLib.timeout_add_seconds(1, self._ensure_osk_remote_device)
            return False

        for event in events:
            if event.type != ecodes.EV_KEY:
                continue
            code = event.code
            value = event.value

            # When hidden, Menu (mapped by input-remapper to Left Meta) is the
            # global keyboard toggle. We only observe it; normal input continues.
            if not self.osk_visible:
                if code == ecodes.KEY_LEFTMETA and value == 1:
                    GLib.idle_add(self.show_osk)
                continue

            # While visible this device is exclusively grabbed, so the app keeps
            # its text-field focus but navigation keys only control the OSK.
            if value not in (1, 2):
                continue

            if code == ecodes.KEY_LEFT:
                self._osk_move(0, -1)
            elif code == ecodes.KEY_RIGHT:
                self._osk_move(0, 1)
            elif code == ecodes.KEY_UP:
                self._osk_move(-1, 0)
            elif code == ecodes.KEY_DOWN:
                self._osk_move(1, 0)
            elif code == ecodes.KEY_ENTER and value == 1:
                self._osk_activate_selected()
            elif code in (ecodes.KEY_ESC, ecodes.KEY_LEFTMETA) and value == 1:
                self.hide_osk()
            elif code == ecodes.KEY_F10 and value == 1:
                # Home keeps its established launcher/task-manager behaviour.
                self.hide_osk()
                GLib.idle_add(self.on_taskmanager_signal)

        return True

    def _release_osk_remote_device(self):
        if self.osk_device is not None and self.osk_device_grabbed:
            try:
                self.osk_device.ungrab()
            except Exception:
                pass
        self.osk_device_grabbed = False

        if self.osk_watch_id:
            try:
                GLib.source_remove(self.osk_watch_id)
            except Exception:
                pass
            self.osk_watch_id = 0

        if self.osk_device is not None:
            try:
                self.osk_device.close()
            except Exception:
                pass
            self.osk_device = None

    def _osk_layout(self):
        if self.osk_symbols:
            return [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
                ["!", '"', "§", "$", "%", "&", "/", "(", ")", "="],
                ["?", "+", "*", "#", "'", ":", ";", ",", ".", "_"],
                ["@", "-", "+", ":", "/", "\\", "[", "]", "{", "}"],
                ["ABC", "Leer", "⌫", "←", "→", "Enter", "Schließen"],
            ]
        return [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            ["Q", "W", "E", "R", "T", "Z", "U", "I", "O", "P"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L", "ß"],
            ["Y", "X", "C", "V", "B", "N", "M", "Ä", "Ö", "Ü"],
            ["123", "⇧", "Leer", "⌫", "←", "→", ".", "@", "Enter", "Schließen"],
        ]

    def _ensure_osk_window(self):
        if self.osk_window is not None:
            return True
        if GtkLayerShell is None:
            return False

        w = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        w.set_title("Shield Tastatur")
        w.set_decorated(False)
        w.set_resizable(False)
        w.set_accept_focus(False)
        w.set_focus_on_map(False)
        w.set_size_request(SCREEN_WIDTH, 218)
        w.set_name("osk-root")

        try:
            GtkLayerShell.init_for_window(w)
            GtkLayerShell.set_layer(w, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(w, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(w, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_anchor(w, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(w, GtkLayerShell.Edge.TOP, False)
            GtkLayerShell.set_keyboard_mode(w, GtkLayerShell.KeyboardMode.NONE)
            # Overlay only the lower CRT area; do not resize the application.
            GtkLayerShell.set_exclusive_zone(w, 0)
        except Exception:
            try:
                w.destroy()
            except Exception:
                pass
            return False

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        outer.set_border_width(3)
        outer.set_name("osk-root")
        w.add(outer)

        title = Gtk.Label(label="Shield Tastatur   •   Menü oder Zurück = schließen")
        title.set_name("osk-title")
        title.set_halign(Gtk.Align.START)
        outer.pack_start(title, False, False, 0)

        self.osk_root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        outer.pack_start(self.osk_root, True, True, 0)

        self.osk_window = w
        self._render_osk()
        return True

    def _render_osk(self):
        if self.osk_root is None:
            return
        for child in self.osk_root.get_children():
            self.osk_root.remove(child)

        layout = self._osk_layout()
        self.osk_buttons = []
        self.osk_row = max(0, min(self.osk_row, len(layout) - 1))

        for r, keys in enumerate(layout):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            buttons = []
            for token in keys:
                label = token
                if token == "⇧" and self.osk_shift:
                    label = "⇧ AN"
                b = Gtk.Button(label=label)
                b.set_name("osk-key")
                b.set_can_focus(False)
                b.set_size_request(0, 34)
                row.pack_start(b, True, True, 0)
                buttons.append((b, token))
            self.osk_root.pack_start(row, True, True, 0)
            self.osk_buttons.append(buttons)

        if self.osk_buttons:
            self.osk_col = max(0, min(self.osk_col, len(self.osk_buttons[self.osk_row]) - 1))
        self.osk_root.show_all()
        self._update_osk_selection()

    def _update_osk_selection(self):
        for r, row in enumerate(self.osk_buttons):
            for c, (button, _token) in enumerate(row):
                ctx = button.get_style_context()
                if r == self.osk_row and c == self.osk_col:
                    ctx.add_class("osk-selected")
                else:
                    ctx.remove_class("osk-selected")

    def _osk_move(self, dr, dc):
        if not self.osk_buttons:
            return
        if dr:
            old_len = max(1, len(self.osk_buttons[self.osk_row]))
            position = self.osk_col / max(1, old_len - 1)
            self.osk_row = (self.osk_row + dr) % len(self.osk_buttons)
            new_len = max(1, len(self.osk_buttons[self.osk_row]))
            self.osk_col = round(position * max(0, new_len - 1))
        elif dc:
            row_len = len(self.osk_buttons[self.osk_row])
            self.osk_col = (self.osk_col + dc) % row_len
        self._update_osk_selection()

    def _wtype_text(self, text):
        if not os.path.isfile("/usr/bin/wtype"):
            return False
        env = os.environ.copy()
        env.setdefault("XDG_RUNTIME_DIR", DEFAULT_XDG_RUNTIME_DIR)
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        try:
            r = subprocess.run(
                ["/usr/bin/wtype", text],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
            return r.returncode == 0
        except Exception:
            return False

    def _wtype_key(self, keyname):
        if not os.path.isfile("/usr/bin/wtype"):
            return False
        env = os.environ.copy()
        env.setdefault("XDG_RUNTIME_DIR", DEFAULT_XDG_RUNTIME_DIR)
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        try:
            r = subprocess.run(
                ["/usr/bin/wtype", "-P", keyname, "-p", keyname],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
            return r.returncode == 0
        except Exception:
            return False

    def _osk_activate_selected(self):
        if not self.osk_buttons:
            return
        try:
            token = self.osk_buttons[self.osk_row][self.osk_col][1]
        except Exception:
            return

        if token == "Schließen":
            self.hide_osk()
            return
        if token == "123":
            self.osk_symbols = True
            self.osk_row = 0
            self.osk_col = 0
            self._render_osk()
            return
        if token == "ABC":
            self.osk_symbols = False
            self.osk_row = 0
            self.osk_col = 0
            self._render_osk()
            return
        if token == "⇧":
            self.osk_shift = not self.osk_shift
            self._render_osk()
            return
        if token == "Leer":
            self._wtype_text(" ")
            return
        if token == "⌫":
            self._wtype_key("BackSpace")
            return
        if token == "←":
            self._wtype_key("Left")
            return
        if token == "→":
            self._wtype_key("Right")
            return
        if token == "Enter":
            self._wtype_key("Return")
            self.hide_osk()
            return

        out = token
        if not self.osk_symbols and len(token) == 1 and token.isalpha():
            out = token.upper() if self.osk_shift else token.lower()
        elif not self.osk_symbols and token in ("Ä", "Ö", "Ü"):
            out = token if self.osk_shift else token.lower()
        self._wtype_text(out)

    def show_osk(self):
        if self.osk_visible:
            return False
        if GtkLayerShell is None or evdev is None or ecodes is None:
            if self.launcher_foreground:
                self.message(
                    "Tastatur-Komponenten fehlen.\n\n"
                    "Installieren: sudo apt install wtype gir1.2-gtklayershell-0.1"
                )
            return False
        if not os.path.isfile("/usr/bin/wtype"):
            if self.launcher_foreground:
                self.message("wtype fehlt.\n\nInstallieren: sudo apt install wtype")
            return False
        if self.osk_device is None:
            self._ensure_osk_remote_device()
        if self.osk_device is None:
            if self.launcher_foreground:
                self.message("input-remapper keyboard wurde nicht gefunden.")
            return False
        if not self._ensure_osk_window():
            if self.launcher_foreground:
                self.message("GTK Layer Shell konnte nicht gestartet werden.")
            return False

        try:
            self.osk_device.grab()
            self.osk_device_grabbed = True
        except Exception:
            if self.launcher_foreground:
                self.message("Shield-Remote konnte für die Tastatur nicht übernommen werden.")
            return False

        self.osk_visible = True
        self.osk_row = 1
        self.osk_col = 0
        self._render_osk()
        self.osk_window.show_all()
        return False

    def hide_osk(self):
        if not self.osk_visible:
            return
        self.osk_visible = False
        if self.osk_window is not None:
            try:
                self.osk_window.hide()
            except Exception:
                pass
        if self.osk_device is not None and self.osk_device_grabbed:
            try:
                self.osk_device.ungrab()
            except Exception:
                pass
        self.osk_device_grabbed = False


    def show_system_info(self):
        try:
            hostname = subprocess.check_output(
                ["hostname"],
                text=True
            ).strip()

            architecture = subprocess.check_output(
                ["uname", "-m"],
                text=True
            ).strip()

            kernel = subprocess.check_output(
                ["uname", "-r"],
                text=True
            ).strip()

        except Exception:
            hostname = "unbekannt"
            architecture = "unbekannt"
            kernel = "unbekannt"

        self.message(
            "Shield Pi\n\n"
            "Host: " + hostname + "\n"
            "Architektur: " + architecture + "\n"
            "Kernel: " + kernel
        )

    def message(self, text):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=text
        )

        dialog.run()
        dialog.destroy()
        self.focus_current()


# ============================================================================
# SHIELD PI NEON UI
# Visual layer based on the supplied black / neon-green Shield PI mock-up.
# The launcher/task/workspace logic above stays intact; this subclass only
# replaces the main launcher presentation and its two carousels.
# ============================================================================

NEON_LEFT = 44
NEON_APP_TOP = 234
NEON_SYSTEM_TOP = 389
NEON_APP_WIDTH = 152
NEON_APP_HEIGHT = 140
NEON_SYSTEM_WIDTH = 120
NEON_SYSTEM_HEIGHT = 72
NEON_GAP = 8
NEON_SYSTEM_VISIBLE = 5


class NeonShieldBackground(Gtk.DrawingArea):
    """Dark mountain / neon horizon background drawn entirely with Cairo."""

    def __init__(self):
        super().__init__()
        self.connect("draw", self.draw_background)

    @staticmethod
    def _path(cr, points, close=False):
        if not points:
            return
        cr.move_to(*points[0])
        for point in points[1:]:
            cr.line_to(*point)
        if close:
            cr.close_path()

    @staticmethod
    def _glow_line(cr, x1, y1, x2, y2, strength=1.0):
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for width, alpha in ((18, 0.020), (9, 0.055), (4, 0.12)):
            cr.set_line_width(width)
            cr.set_source_rgba(0.50, 1.0, 0.0, alpha * strength)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()
        cr.set_line_width(1.25)
        cr.set_source_rgba(0.62, 1.0, 0.02, 0.93 * strength)
        cr.move_to(x1, y1)
        cr.line_to(x2, y2)
        cr.stroke()

    def _mountain(self, cr, points, rgba):
        self._path(cr, points, close=True)
        cr.set_source_rgba(*rgba)
        cr.fill()

    def _draw_circuit(self, cr, side, width, height):
        mirror = -1 if side == "right" else 1
        base = width - 11 if side == "right" else 11
        inward = -1 if side == "right" else 1

        cr.set_line_width(0.9)
        cr.set_source_rgba(0.58, 1.0, 0.0, 0.63)
        paths = [
            [(base, 0), (base, 39), (base + inward * 14, 53), (base + inward * 14, 94)],
            [(base + inward * 10, 0), (base + inward * 10, 28), (base + inward * 25, 43), (base + inward * 25, 76)],
            [(base, 116), (base, 139), (base + inward * 17, 156), (base + inward * 17, 211)],
        ]
        for pts in paths:
            self._path(cr, pts)
            cr.stroke()

        for y in (94, 211):
            x = base + inward * 14 if y == 94 else base + inward * 17
            cr.arc(x, y, 2.2, 0, math.tau)
            cr.stroke()

        # Small horizontal trace near the app area.
        cr.move_to(base, 224)
        cr.line_to(base + inward * 28, 224)
        cr.line_to(base + inward * 34, 230)
        cr.stroke()

    def draw_background(self, widget, cr):
        allocation = self.get_allocation()
        width = max(1, allocation.width)
        height = max(1, allocation.height)
        sx = width / 720.0
        sy = height / 576.0

        def P(x, y):
            return (x * sx, y * sy)

        # Base black with a very subtle green atmospheric bloom on the horizon.
        cr.set_source_rgb(0.002, 0.006, 0.004)
        cr.paint()

        glow = cairo.RadialGradient(360 * sx, 218 * sy, 2, 360 * sx, 218 * sy, 360 * sx)
        glow.add_color_stop_rgba(0.0, 0.18, 0.34, 0.02, 0.38)
        glow.add_color_stop_rgba(0.38, 0.03, 0.09, 0.015, 0.22)
        glow.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
        cr.set_source(glow)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        # Distant mountain ridge.
        ridge = [P(0, 190), P(34, 170), P(59, 159), P(79, 166), P(98, 151),
                 P(122, 166), P(148, 174), P(176, 163), P(204, 175), P(232, 168),
                 P(260, 178), P(294, 170), P(326, 181), P(355, 166), P(382, 158),
                 P(410, 168), P(438, 153), P(468, 145), P(493, 124), P(515, 143),
                 P(538, 171), P(560, 188), P(590, 207), P(720, 226), P(720, 250), P(0, 250)]
        self._mountain(cr, ridge, (0.015, 0.027, 0.020, 1.0))

        # Left foreground mountains.
        left = [P(0, 176), P(42, 165), P(66, 153), P(91, 161), P(112, 184),
                P(144, 174), P(166, 194), P(204, 201), P(228, 218), P(0, 222)]
        self._mountain(cr, left, (0.005, 0.010, 0.008, 1.0))
        left_hi = [P(0, 185), P(52, 172), P(83, 160), P(112, 185), P(142, 179), P(175, 199), P(0, 219)]
        self._mountain(cr, left_hi, (0.018, 0.035, 0.019, 0.72))

        # Right foreground mountains.
        right = [P(398, 226), P(432, 207), P(458, 183), P(484, 181), P(505, 160),
                 P(533, 185), P(553, 196), P(574, 217), P(720, 233), P(720, 290), P(393, 279)]
        self._mountain(cr, right, (0.004, 0.009, 0.006, 1.0))

        # Thin green mist on the horizon.
        for dy, alpha, lw in ((0, 0.94, 1.1), (2, 0.35, 2.0), (5, 0.14, 5.0), (9, 0.05, 11.0)):
            cr.set_source_rgba(0.52, 1.0, 0.0, alpha)
            cr.set_line_width(lw * sy)
            cr.move_to(0, (224 + dy) * sy)
            cr.curve_to(180 * sx, (226 + dy) * sy, 420 * sx, (214 + dy) * sy, width, (229 + dy) * sy)
            cr.stroke()

        # Perspective light trails converging on the horizon.
        van_x, van_y = P(360, 221)
        for bottom_x in range(-80, 801, 70):
            bx, by = P(bottom_x, 420)
            cr.set_line_width(0.7)
            cr.set_source_rgba(0.48, 1.0, 0.0, 0.20)
            cr.move_to(van_x, van_y)
            cr.line_to(bx, by)
            cr.stroke()

        for y in (232, 239, 249, 262, 280, 304, 336, 376, 428):
            alpha = 0.28 if y < 290 else 0.13
            cr.set_line_width(0.7)
            cr.set_source_rgba(0.47, 1.0, 0.0, alpha)
            cr.move_to(0, y * sy)
            cr.line_to(width, y * sy)
            cr.stroke()

        # Reflections below the control rows. Deterministic sine strokes avoid noise/flicker.
        for i in range(74):
            x = (7 + i * 9.8) * sx
            strength = (0.5 + 0.5 * math.sin(i * 1.71))
            top = (468 + (i % 5) * 2.0) * sy
            length = (28 + 65 * strength) * sy
            cr.set_line_width((0.7 + 1.2 * strength) * sx)
            cr.set_source_rgba(0.34, 0.92, 0.0, 0.035 + 0.11 * strength)
            cr.move_to(x, top)
            cr.line_to(x + math.sin(i) * 3 * sx, min(height, top + length))
            cr.stroke()

        # Large angular Shield shard in the upper-right.
        shard = [P(487, 97), P(616, -8), P(578, 157), P(546, 237)]
        self._path(cr, shard, close=True)
        shard_grad = cairo.LinearGradient(500 * sx, 90 * sy, 600 * sx, 220 * sy)
        shard_grad.add_color_stop_rgba(0, 0.015, 0.025, 0.018, 0.97)
        shard_grad.add_color_stop_rgba(1, 0.001, 0.004, 0.003, 0.98)
        cr.set_source(shard_grad)
        cr.fill_preserve()
        cr.set_line_width(0.7)
        cr.set_source_rgba(0.45, 0.88, 0.06, 0.18)
        cr.stroke()

        self._glow_line(cr, *P(487, 97), *P(616, -8), strength=0.95)
        self._glow_line(cr, *P(487, 97), *P(546, 237), strength=0.88)
        cr.set_line_width(0.7)
        cr.set_source_rgba(0.60, 1.0, 0.0, 0.48)
        cr.move_to(*P(578, 157))
        cr.line_to(*P(720, 254))
        cr.stroke()

        # Faint secondary planes.
        self._path(cr, [P(486, 97), P(552, 226), P(518, 137)], close=True)
        cr.set_source_rgba(0.08, 0.12, 0.08, 0.26)
        cr.fill()

        # Side circuit ornaments.
        cr.save()
        cr.scale(sx, sy)
        self._draw_circuit(cr, "left", 720, 576)
        self._draw_circuit(cr, "right", 720, 576)
        cr.restore()

        return False


class NeonButton(Gtk.Button):
    """Button with a chamfered black-glass / neon-green frame."""

    def __init__(self, kind="app"):
        super().__init__()
        self.kind = kind
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_name("neon-app-button" if kind == "app" else "neon-system-button")
        self.connect("focus-in-event", lambda *_: self.queue_draw())
        self.connect("focus-out-event", lambda *_: self.queue_draw())

    @staticmethod
    def _frame_path(cr, w, h, cut):
        cr.move_to(cut, 0.5)
        cr.line_to(w - 0.5, 0.5)
        cr.line_to(w - 0.5, h - cut)
        cr.line_to(w - cut, h - 0.5)
        cr.line_to(0.5, h - 0.5)
        cr.line_to(0.5, cut)
        cr.close_path()

    def do_draw(self, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        cut = 9 if self.kind == "app" else 7
        focus = self.has_focus()

        # Glow / selection halo, kept inside the widget clip.
        if focus:
            for lw, alpha in ((10, 0.08), (6, 0.13), (3, 0.26)):
                self._frame_path(cr, w, h, cut)
                cr.set_line_width(lw)
                cr.set_source_rgba(0.55, 1.0, 0.0, alpha)
                cr.stroke()

        # Black glass fill with green bias on focus.
        self._frame_path(cr, w, h, cut)
        grad = cairo.LinearGradient(0, 0, w, h)
        if focus:
            grad.add_color_stop_rgba(0.0, 0.065, 0.14, 0.025, 0.98)
            grad.add_color_stop_rgba(0.45, 0.015, 0.025, 0.016, 0.99)
            grad.add_color_stop_rgba(1.0, 0.020, 0.050, 0.008, 0.99)
        else:
            grad.add_color_stop_rgba(0.0, 0.030, 0.045, 0.034, 0.97)
            grad.add_color_stop_rgba(0.48, 0.010, 0.014, 0.012, 0.985)
            grad.add_color_stop_rgba(1.0, 0.018, 0.028, 0.016, 0.985)
        cr.set_source(grad)
        cr.fill_preserve()
        cr.set_line_width(1.1 if not focus else 1.7)
        cr.set_source_rgba(0.50, 0.78, 0.10, 0.48 if not focus else 0.98)
        cr.stroke()

        # Faceted corner planes and diagonal technical lines.
        cr.move_to(0, h * 0.67)
        cr.line_to(w * 0.32, 0)
        cr.line_to(w * 0.45, 0)
        cr.close_path()
        cr.set_source_rgba(0.12, 0.18, 0.12, 0.22)
        cr.fill()

        cr.move_to(w, h * 0.52)
        cr.line_to(w * 0.70, h)
        cr.line_to(w, h)
        cr.close_path()
        cr.set_source_rgba(0.18, 0.30, 0.08, 0.13 if not focus else 0.24)
        cr.fill()

        cr.set_line_width(0.55)
        cr.set_source_rgba(0.56, 1.0, 0.0, 0.42 if not focus else 0.78)
        cr.move_to(0.5, h * 0.67)
        cr.line_to(w * 0.32, 0.5)
        cr.stroke()
        cr.move_to(w * 0.69, h - 0.5)
        cr.line_to(w - 0.5, h * 0.52)
        cr.stroke()

        return Gtk.Button.do_draw(self, cr)


class NeonAppMark(Gtk.DrawingArea):
    def __init__(self, mark):
        super().__init__()
        self.mark = mark
        self.set_size_request(74, 66)
        self.connect("draw", self.draw_mark)

    @staticmethod
    def _diamond(cr, cx, cy, r):
        cr.move_to(cx, cy - r)
        cr.line_to(cx + r, cy)
        cr.line_to(cx, cy + r)
        cr.line_to(cx - r, cy)
        cr.close_path()

    def draw_mark(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        cx, cy = w / 2, h / 2
        cr.set_source_rgb(0.60, 1.0, 0.03)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        if self.mark == "vlc":
            # Stylised VLC cone in the monochrome neon palette.
            cr.move_to(cx, 7)
            cr.line_to(cx + 17, 50)
            cr.line_to(cx - 17, 50)
            cr.close_path()
            cr.fill()
            cr.rectangle(cx - 23, 49, 46, 8)
            cr.fill()
            cr.set_source_rgb(0.035, 0.060, 0.025)
            cr.move_to(cx - 7, 21)
            cr.line_to(cx + 7, 21)
            cr.line_to(cx + 10, 29)
            cr.line_to(cx - 10, 29)
            cr.close_path()
            cr.fill()
            cr.move_to(cx - 12, 35)
            cr.line_to(cx + 12, 35)
            cr.line_to(cx + 15, 43)
            cr.line_to(cx - 15, 43)
            cr.close_path()
            cr.fill()

        elif self.mark == "freetube":
            # Compact geometric F similar to the mock-up.
            cr.move_to(13, 15)
            cr.line_to(59, 15)
            cr.line_to(49, 27)
            cr.line_to(31, 27)
            cr.line_to(28, 34)
            cr.line_to(46, 34)
            cr.line_to(37, 45)
            cr.line_to(24, 45)
            cr.line_to(17, 56)
            cr.close_path()
            cr.fill()

        elif self.mark == "kodi":
            self._diamond(cr, cx, 15, 12)
            cr.fill()
            self._diamond(cr, cx, 48, 12)
            cr.fill()
            self._diamond(cr, cx - 18, 32, 10)
            cr.fill()
            self._diamond(cr, cx + 18, 32, 10)
            cr.fill()
            cr.set_source_rgb(0.02, 0.04, 0.018)
            cr.move_to(cx - 2, 21)
            cr.line_to(cx + 6, 29)
            cr.line_to(cx - 1, 36)
            cr.line_to(cx + 7, 44)
            cr.set_line_width(4)
            cr.stroke()

        elif self.mark == "nordvpn":
            cr.arc(cx, cy, 27, math.pi, 2 * math.pi)
            cr.line_to(cx + 27, cy + 2)
            cr.arc(cx, cy + 2, 27, 0, math.pi)
            cr.close_path()
            cr.fill()
            cr.set_source_rgb(0.02, 0.045, 0.025)
            cr.move_to(cx - 19, cy + 17)
            cr.line_to(cx - 6, cy - 5)
            cr.line_to(cx + 1, cy + 5)
            cr.line_to(cx + 8, cy - 10)
            cr.line_to(cx + 20, cy + 17)
            cr.close_path()
            cr.fill()

        return False


class NeonSystemSymbol(Gtk.DrawingArea):
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
        self.set_size_request(36, 32)
        self.connect("draw", self.draw_symbol)

    def draw_symbol(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        cx, cy = w / 2, h / 2
        cr.set_source_rgb(0.60, 1.0, 0.03)
        cr.set_line_width(2.8)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        if self.symbol == "folder":
            cr.move_to(4, 10)
            cr.line_to(12, 10)
            cr.line_to(15, 13)
            cr.line_to(31, 13)
            cr.line_to(31, 27)
            cr.line_to(4, 27)
            cr.close_path()
            cr.stroke()

        elif self.symbol == "image":
            cr.rectangle(4.5, 5.5, 27, 23)
            cr.stroke()
            cr.arc(23.5, 12.5, 2.2, 0, math.tau)
            cr.fill()
            cr.move_to(7, 25)
            cr.line_to(14, 17)
            cr.line_to(19, 22)
            cr.line_to(24, 16)
            cr.line_to(29, 25)
            cr.stroke()

        elif self.symbol == "info":
            cr.arc(cx, cy, 11.5, 0, math.tau)
            cr.stroke()
            cr.set_line_width(3.2)
            cr.move_to(cx, cy - 2)
            cr.line_to(cx, cy + 7)
            cr.stroke()
            cr.arc(cx, cy - 7, 1.5, 0, math.tau)
            cr.fill()

        elif self.symbol == "restart":
            cr.arc(cx, cy, 11, 0.35, math.pi * 1.84)
            cr.stroke()
            cr.move_to(cx + 10.5, cy - 8)
            cr.line_to(cx + 11.5, cy + 1)
            cr.line_to(cx + 3.5, cy - 0.5)
            cr.stroke()

        elif self.symbol == "power":
            cr.arc(cx, cy + 2, 11.5, -0.70, math.pi + 0.70)
            cr.stroke()
            cr.move_to(cx, cy - 13)
            cr.line_to(cx, cy + 1)
            cr.stroke()

        elif self.symbol == "quit":
            cr.rectangle(7, 5, 15, 23)
            cr.stroke()
            cr.move_to(15, 16)
            cr.line_to(31, 16)
            cr.stroke()
            cr.move_to(26, 11)
            cr.line_to(31, 16)
            cr.line_to(26, 21)
            cr.stroke()

        return False


class ShieldLauncherNeon(ShieldLauncher):
    """Main-screen skin matching the supplied Shield PI design."""

    def __init__(self):
        # These are needed before ShieldLauncher.__init__ dispatches build_ui().
        self.system_index = 0
        self.system_view_start = 0
        self.system_row_box = None
        self.clock_date = None

        # Restore the working universal Shield-remote layer. Kodi remains native;
        # FreeTube/VLC/browser-style apps are translated to keyboard navigation.
        self.remote_modes = {}
        self.remote_device_grabbed = False
        self.remote_ok_started = None
        self.remote_ok_class = None
        self.remote_ok_hold_threshold = 0.80
        self.remote_menu_started = None
        self.remote_menu_class = None
        self.remote_menu_hold_threshold = 0.55
        self.remote_modal_active = False
        self.remote_home_pressed = False
        self.remote_home_last_release = 0.0

        super().__init__()
        GLib.timeout_add(200, self._sync_remote_layer)

    def launcher_items(self):
        # Keep the original commands/classes, but use the mock-up's FreeTube label
        # and monochrome icon treatment for the four built-in tiles.
        builtins = []
        for original in APPS:
            item = dict(original)
            cls = item.get("class")
            if cls == "freetube":
                item["special_icon"] = "freetube"
            elif cls in ("vlc", "kodi", "nordvpn"):
                item["special_icon"] = cls
            builtins.append(item)

        plus_item = {
            "name": "App hinzufügen",
            "subtitle": "",
            "command": None,
            "class": "add-app",
            "action": "add_app"
        }
        return builtins + list(self.custom_apps) + [plus_item]

    def system_items(self):
        # Five visible cards like the reference. "Launcher beenden" remains
        # available as the sixth carousel item by moving one step further right.
        preferred = ["Dateien", "Bilder", "Systeminfo", "Neustart", "Ausschalten", "Launcher beenden"]
        by_name = {x.get("name"): dict(x) for x in SYSTEM_APPS}
        result = []
        symbols = {
            "Dateien": "folder",
            "Bilder": "image",
            "Systeminfo": "info",
            "Neustart": "restart",
            "Ausschalten": "power",
            "Launcher beenden": "quit",
        }
        for name in preferred:
            if name not in by_name:
                continue
            item = by_name[name]
            item["special_icon"] = symbols[name]
            result.append(item)
        return result

    def build_ui(self):
        overlay = Gtk.Overlay()
        self.add(overlay)

        background = NeonShieldBackground()
        background.set_hexpand(True)
        background.set_vexpand(True)
        overlay.add(background)

        fixed = Gtk.Fixed()
        fixed.set_size_request(SCREEN_WIDTH, SCREEN_HEIGHT)
        fixed.set_hexpand(True)
        fixed.set_vexpand(True)
        overlay.add_overlay(fixed)

        # Brand block.
        brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title = Gtk.Label()
        title.set_name("brand-title")
        title.set_halign(Gtk.Align.START)
        title.set_markup(
            '<span letter_spacing="4300">SHIELD</span>'
            '<span foreground="#9cff00" letter_spacing="2600"> PI</span>'
        )
        brand.pack_start(title, False, False, 0)

        subtitle = Gtk.Label()
        subtitle.set_name("brand-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_markup('<span letter_spacing="3800">MEDIA LAUNCHER</span>')
        brand.pack_start(subtitle, False, False, 0)
        fixed.put(brand, 62, 79)

        # Time/date block.
        time_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        time_box.set_size_request(118, 38)
        self.clock = Gtk.Label()
        self.clock.set_name("neon-clock")
        self.clock.set_halign(Gtk.Align.END)
        self.clock_date = Gtk.Label()
        self.clock_date.set_name("neon-date")
        self.clock_date.set_halign(Gtk.Align.END)
        time_box.pack_start(self.clock, False, False, 0)
        time_box.pack_start(self.clock_date, False, False, 0)
        fixed.put(time_box, 567, 79)

        # App carousel: 4 visible.
        self.app_row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=NEON_GAP)
        self.app_row_box.set_halign(Gtk.Align.START)
        self.rows.append([])
        fixed.put(self.app_row_box, NEON_LEFT, NEON_APP_TOP)
        self.render_app_carousel()

        # System carousel: 5 visible; sixth item preserves the desktop-exit action.
        self.system_row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=NEON_GAP)
        self.system_row_box.set_halign(Gtk.Align.START)
        self.rows.append([])
        fixed.put(self.system_row_box, NEON_LEFT, NEON_SYSTEM_TOP)
        self.render_system_carousel()

    def create_app_content(self, item):
        if item.get("action") == "add_app":
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            box.set_halign(Gtk.Align.CENTER)
            box.set_valign(Gtk.Align.CENTER)
            plus = Gtk.Label(label="+")
            plus.set_name("neon-plus")
            caption = Gtk.Label()
            caption.set_name("neon-app-text")
            caption.set_markup('<span letter_spacing="1200">APP HINZUFÜGEN</span>')
            box.pack_start(plus, False, False, 0)
            box.pack_start(caption, False, False, 0)
            return box

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        mark = item.get("special_icon")
        if mark in ("vlc", "freetube", "kodi", "nordvpn"):
            icon = NeonAppMark(mark)
        else:
            icon = self.load_app_icon(item)

        if icon:
            box.pack_start(icon, False, False, 0)

        name = Gtk.Label()
        name.set_name("neon-app-text")
        name.set_halign(Gtk.Align.CENTER)
        name.set_ellipsize(3)
        name.set_max_width_chars(14)
        label = xml_escape(str(item.get("name") or ""))
        name.set_markup('<span letter_spacing="2200">%s</span>' % label)
        box.pack_start(name, False, False, 0)
        return box

    def render_app_carousel(self):
        if self.app_row_box is None:
            return
        items = self.launcher_items()
        if not items:
            return

        self.app_index = max(0, min(self.app_index, len(items) - 1))
        if self.app_index < self.app_view_start:
            self.app_view_start = self.app_index
        elif self.app_index >= self.app_view_start + APPS_PER_ROW:
            self.app_view_start = self.app_index - APPS_PER_ROW + 1
        self.app_view_start = max(0, min(self.app_view_start, max(0, len(items) - APPS_PER_ROW)))

        for child in self.app_row_box.get_children():
            self.app_row_box.remove(child)

        visible = items[self.app_view_start:self.app_view_start + APPS_PER_ROW]
        buttons = []
        for item in visible:
            button = NeonButton("app")
            button.set_size_request(NEON_APP_WIDTH, NEON_APP_HEIGHT)
            button.add(self.create_app_content(item))
            button.connect("clicked", self.activate_item, item)
            self.app_row_box.pack_start(button, False, False, 0)
            buttons.append(button)

        self.rows[0] = buttons
        self.current_col = self.app_index - self.app_view_start
        self.app_row_box.show_all()

    def create_system_content(self, item):
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)

        icon = NeonSystemSymbol(item.get("special_icon") or "info")
        content.pack_start(icon, False, False, 0)

        label = Gtk.Label()
        label.set_name("neon-system-text")
        label.set_halign(Gtk.Align.CENTER)
        text = xml_escape(str(item.get("name") or ""))
        label.set_markup('<span letter_spacing="1200">%s</span>' % text)
        content.pack_start(label, False, False, 0)
        return content

    def render_system_carousel(self):
        if self.system_row_box is None:
            return
        items = self.system_items()
        if not items:
            return

        self.system_index = max(0, min(self.system_index, len(items) - 1))
        if self.system_index < self.system_view_start:
            self.system_view_start = self.system_index
        elif self.system_index >= self.system_view_start + NEON_SYSTEM_VISIBLE:
            self.system_view_start = self.system_index - NEON_SYSTEM_VISIBLE + 1
        self.system_view_start = max(
            0,
            min(self.system_view_start, max(0, len(items) - NEON_SYSTEM_VISIBLE))
        )

        for child in self.system_row_box.get_children():
            self.system_row_box.remove(child)

        visible = items[self.system_view_start:self.system_view_start + NEON_SYSTEM_VISIBLE]
        buttons = []
        for item in visible:
            button = NeonButton("system")
            button.set_size_request(NEON_SYSTEM_WIDTH, NEON_SYSTEM_HEIGHT)
            button.add(self.create_system_content(item))
            button.connect("clicked", self.activate_item, item)
            self.system_row_box.pack_start(button, False, False, 0)
            buttons.append(button)

        self.rows[1] = buttons
        self.current_col = self.system_index - self.system_view_start
        self.system_row_box.show_all()

    def load_css(self):
        # Keep all existing dialogs/task-manager/OSK styling, then override only
        # the new main-screen widgets.
        super().load_css()
        css = b"""
        #brand-title {
            color: #d8ddda;
            font-size: 16px;
            font-weight: 400;
        }
        #brand-subtitle {
            color: rgba(190, 199, 191, 0.55);
            font-size: 6px;
            font-weight: 400;
        }
        #neon-clock {
            color: rgba(215, 220, 216, 0.72);
            font-size: 14px;
            font-weight: 400;
        }
        #neon-date {
            color: rgba(185, 195, 186, 0.56);
            font-size: 6px;
            font-weight: 400;
        }
        #neon-app-button, #neon-system-button {
            background: transparent;
            background-image: none;
            border: none;
            border-radius: 0;
            box-shadow: none;
            padding: 0;
            margin: 0;
            outline: none;
        }
        #neon-app-button:focus, #neon-system-button:focus {
            background: transparent;
            background-image: none;
            border: none;
            box-shadow: none;
            outline: none;
        }
        #neon-app-text {
            color: rgba(242, 245, 241, 0.92);
            font-size: 12px;
            font-weight: 400;
        }
        #neon-system-text {
            color: rgba(236, 241, 235, 0.92);
            font-size: 8px;
            font-weight: 400;
        }
        #neon-plus {
            color: #9cff00;
            font-size: 38px;
            font-weight: 300;
        }

        /* Bring secondary screens into the same black/neon family. */
        #task-window, #app-picker {
            background-color: #020503;
        }
        #task-title {
            color: #eef2ed;
            font-weight: 500;
        }
        #task-card, #picker-item, #remove-choice {
            background: rgba(5, 11, 7, 0.98);
            border-color: rgba(126, 205, 35, 0.46);
        }
        #task-card:focus, #picker-item:focus, #remove-choice:focus {
            background: rgba(12, 26, 12, 0.98);
            border-color: #9cff00;
            box-shadow: 0 0 9px rgba(140, 255, 0, 0.72);
        }
        #task-active, #plus-symbol {
            color: #9cff00;
        }
        #osk-root {
            background-color: rgba(1, 5, 2, 0.985);
            border-top: 2px solid rgba(156, 255, 0, 0.62);
        }
        #osk-key.osk-selected {
            background: rgba(20, 42, 12, 1.0);
            border-color: #9cff00;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

    def update_clock(self):
        now = datetime.datetime.now()
        self.clock.set_text(now.strftime("%H:%M"))
        if self.clock_date is not None:
            weekdays = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]
            months = ["JAN", "FEB", "MAR", "APR", "MAI", "JUN", "JUL", "AUG", "SEP", "OKT", "NOV", "DEZ"]
            text = "%s  %02d. %s %04d" % (
                weekdays[now.weekday()],
                now.day,
                months[now.month - 1],
                now.year,
            )
            self.clock_date.set_markup('<span letter_spacing="1700">%s</span>' % text)
        return True

    def focus_current(self):
        if not self.rows:
            return
        self.current_row = max(0, min(self.current_row, len(self.rows) - 1))

        if self.current_row == 0:
            self.render_app_carousel()
            if self.rows[0]:
                self.current_col = self.app_index - self.app_view_start
                self.current_col = max(0, min(self.current_col, len(self.rows[0]) - 1))
                self.rows[0][self.current_col].grab_focus()
            return

        if self.current_row == 1:
            self.render_system_carousel()
            if self.rows[1]:
                self.current_col = self.system_index - self.system_view_start
                self.current_col = max(0, min(self.current_col, len(self.rows[1]) - 1))
                self.rows[1][self.current_col].grab_focus()
            return

    def move_vertical(self, direction):
        if direction > 0 and self.current_row == 0 and len(self.rows) > 1:
            visible = max(1, len(self.rows[0]))
            local = self.app_index - self.app_view_start
            position = local / max(1, visible - 1)
            self.current_row = 1

            sys_items = self.system_items()
            visible_sys = min(NEON_SYSTEM_VISIBLE, len(sys_items) - self.system_view_start)
            local_sys = round(position * max(0, visible_sys - 1))
            self.system_index = min(len(sys_items) - 1, self.system_view_start + local_sys)
            self.current_col = self.system_index - self.system_view_start
            return

        if direction < 0 and self.current_row == 1:
            sys_visible = max(1, len(self.rows[1]))
            local = self.system_index - self.system_view_start
            position = local / max(1, sys_visible - 1)
            self.current_row = 0

            app_visible = min(APPS_PER_ROW, len(self.launcher_items()) - self.app_view_start)
            local_app = round(position * max(0, app_visible - 1))
            self.app_index = min(len(self.launcher_items()) - 1, self.app_view_start + local_app)
            self.current_col = self.app_index - self.app_view_start

    def on_key(self, widget, event):
        key = Gdk.keyval_name(event.keyval)

        if self.current_row == 0:
            items = self.launcher_items()
            if key == "Right":
                if self.app_index < len(items) - 1:
                    self.app_index += 1
                self.render_app_carousel()
                self.focus_current()
            elif key == "Left":
                if self.app_index > 0:
                    self.app_index -= 1
                self.render_app_carousel()
                self.focus_current()
            elif key == "Down":
                if len(self.rows) > 1:
                    self.move_vertical(1)
                self.focus_current()
            elif key in ("Return", "KP_Enter"):
                if not items or not self.rows[0]:
                    return True
                item = items[self.app_index]
                app_class = item.get("class")
                if self._is_custom_launcher_class(app_class):
                    if self._ok_press_started is None:
                        self._ok_press_started = time.monotonic()
                        self._ok_press_class = app_class
                    return True
                local = self.app_index - self.app_view_start
                if 0 <= local < len(self.rows[0]):
                    self.rows[0][local].clicked()
            elif key in ("Escape", "BackSpace"):
                self._show_black_workspace()
                self.iconify()
                self.launcher_foreground = False
            return True

        if self.current_row == 1:
            items = self.system_items()
            if key == "Right":
                if self.system_index < len(items) - 1:
                    self.system_index += 1
                self.render_system_carousel()
                self.focus_current()
            elif key == "Left":
                if self.system_index > 0:
                    self.system_index -= 1
                self.render_system_carousel()
                self.focus_current()
            elif key == "Up":
                self.move_vertical(-1)
                self.focus_current()
            elif key in ("Return", "KP_Enter"):
                local = self.system_index - self.system_view_start
                if 0 <= local < len(self.rows[1]):
                    self.rows[1][local].clicked()
            elif key in ("Escape", "BackSpace"):
                self.show_launcher()
            return True

        return True


    # ------------------------------------------------------------------
    # Shield remote compatibility layer (restored from the last working build)
    # ------------------------------------------------------------------
    def on_taskmanager_signal(self):
        """Use evdev as the single Home/F10 source when available.

        Labwc can emit SIGUSR1 for the same physical F10 press. Handling both
        paths counts one press twice and breaks the intended single/double Home
        flow. If the input-remapper keyboard is connected, SIGUSR1 is therefore
        ignored and Home is dispatched from _on_osk_remote_fd on key release.
        """
        if getattr(self, "osk_device", None) is not None:
            return True
        return ShieldLauncher.on_taskmanager_signal(self)

    def _handle_home_from_remote(self):
        ShieldLauncher.on_taskmanager_signal(self)
        return False

    def _remote_profile_for_class(self, app_class):
        if not app_class:
            return None
        cfg = self.app_config(app_class) or {}
        parts = [app_class, cfg.get("name", ""), cfg.get("desktop_id", "")]
        parts.extend(cfg.get("match") or [])
        parts.extend(str(x) for x in (cfg.get("command") or []))
        haystack = " ".join(str(x) for x in parts if x).lower()

        # Kodi has native TV navigation and must never be grabbed here.
        if "kodi" in haystack or app_class == "kodi":
            return None
        if "freetube" in haystack:
            return "freetube"
        if "firefox" in haystack:
            return "firefox"
        if "chromium" in haystack or "google-chrome" in haystack or "chrome" in haystack:
            return "chromium"
        if "vlc" in haystack or app_class == "vlc":
            return "vlc"
        return None

    def _default_remote_mode(self, profile):
        return "media" if profile == "vlc" else "nav"

    def _remote_mode_for_class(self, app_class):
        profile = self._remote_profile_for_class(app_class)
        if not profile:
            return None
        return self.remote_modes.get(app_class, self._default_remote_mode(profile))

    def _set_remote_grab(self, enabled):
        dev = self.osk_device
        if dev is None:
            self.remote_device_grabbed = False
            return False

        if enabled:
            if self.remote_device_grabbed:
                return True
            if self.osk_visible or self.osk_device_grabbed:
                return False
            try:
                dev.grab()
                self.remote_device_grabbed = True
                return True
            except Exception:
                self.remote_device_grabbed = False
                return False

        if self.remote_device_grabbed:
            try:
                dev.ungrab()
            except Exception:
                pass
        self.remote_device_grabbed = False
        self.remote_ok_started = None
        self.remote_ok_class = None
        self.remote_menu_started = None
        self.remote_menu_class = None
        return True

    def _remote_layer_should_run(self):
        if self.remote_modal_active:
            return False
        if self.task_window is not None:
            return False
        if self.app_picker_window is not None:
            return False
        if self.remove_confirm_window is not None:
            return False
        if self.osk_visible:
            return False
        if self.launcher_foreground:
            return False
        return self._remote_profile_for_class(self.foreground_task_class) is not None

    def _sync_remote_layer(self):
        if self.osk_device is None:
            self._ensure_osk_remote_device()
        if self._remote_layer_should_run():
            self._set_remote_grab(True)
        else:
            self._set_remote_grab(False)
        return True

    def _wtype_combo(self, modifier, keyname):
        if not os.path.isfile("/usr/bin/wtype"):
            return False
        env = os.environ.copy()
        env.setdefault("XDG_RUNTIME_DIR", DEFAULT_XDG_RUNTIME_DIR)
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        try:
            r = subprocess.run(
                [
                    "/usr/bin/wtype",
                    "-M", modifier,
                    "-P", keyname,
                    "-p", keyname,
                    "-m", modifier,
                ],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _remote_send_nav(self, code, profile):
        if code in (ecodes.KEY_RIGHT, ecodes.KEY_DOWN):
            return self._wtype_key("Tab")
        if code in (ecodes.KEY_LEFT, ecodes.KEY_UP):
            return self._wtype_combo("shift", "Tab")
        if code in (ecodes.KEY_ESC, ecodes.KEY_BACKSPACE):
            if profile in ("freetube", "firefox", "chromium"):
                return self._wtype_combo("alt", "Left")
            return self._wtype_key("Escape")
        return False

    def _remote_cycle_application_area(self, app_class):
        profile = self._remote_profile_for_class(app_class)
        if not profile:
            return False
        return self._wtype_key("F6")

    def _remote_send_media(self, code):
        mapping = {
            ecodes.KEY_LEFT: "Left",
            ecodes.KEY_RIGHT: "Right",
            ecodes.KEY_UP: "Up",
            ecodes.KEY_DOWN: "Down",
        }
        keyname = mapping.get(code)
        if keyname:
            return self._wtype_key(keyname)
        if code in (ecodes.KEY_ESC, ecodes.KEY_BACKSPACE):
            return self._wtype_key("Escape")
        return False

    def _remote_short_ok(self, app_class):
        profile = self._remote_profile_for_class(app_class)
        mode = self._remote_mode_for_class(app_class)
        if not profile or not mode:
            return
        if mode == "nav":
            self._wtype_key("Return")
        else:
            self._wtype_key("space")

    def _toggle_remote_mode(self, app_class):
        profile = self._remote_profile_for_class(app_class)
        if not profile:
            return
        current = self._remote_mode_for_class(app_class)
        self.remote_modes[app_class] = "media" if current == "nav" else "nav"

    def _on_osk_remote_fd(self, source, condition):
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            self._set_remote_grab(False)
            ShieldLauncher._release_osk_remote_device(self)
            GLib.timeout_add_seconds(1, self._ensure_osk_remote_device)
            return False

        dev = self.osk_device
        if dev is None:
            return False

        try:
            events = dev.read()
        except BlockingIOError:
            return True
        except OSError:
            self._set_remote_grab(False)
            ShieldLauncher._release_osk_remote_device(self)
            GLib.timeout_add_seconds(1, self._ensure_osk_remote_device)
            return False

        for event in events:
            if event.type != ecodes.EV_KEY:
                continue
            code = event.code
            value = event.value

            # HOME/F10: exactly one physical press = exactly one launcher event.
            # Dispatch on release and swallow auto-repeat. A 110 ms guard filters
            # duplicate press/release pairs from some remapper profiles while the
            # normal 0.38 s human double-Home window remains usable.
            if code == ecodes.KEY_F10:
                if value == 1:
                    self.remote_home_pressed = True
                elif value == 0 and self.remote_home_pressed:
                    self.remote_home_pressed = False
                    now = time.monotonic()
                    if (now - self.remote_home_last_release) >= 0.11:
                        self.remote_home_last_release = now
                        if self.osk_visible:
                            self.hide_osk()
                        GLib.idle_add(self._handle_home_from_remote)
                continue

            # OSK owns the same device while visible.
            if self.osk_visible:
                if value not in (1, 2):
                    continue
                if code == ecodes.KEY_LEFT:
                    self._osk_move(0, -1)
                elif code == ecodes.KEY_RIGHT:
                    self._osk_move(0, 1)
                elif code == ecodes.KEY_UP:
                    self._osk_move(-1, 0)
                elif code == ecodes.KEY_DOWN:
                    self._osk_move(1, 0)
                elif code == ecodes.KEY_ENTER and value == 1:
                    self._osk_activate_selected()
                elif code in (ecodes.KEY_ESC, ecodes.KEY_LEFTMETA) and value == 1:
                    self.hide_osk()
                continue

            # Launcher itself continues to use normal GTK focus/navigation.
            # We only observe Menu and Home here; the device is not grabbed.
            if self.launcher_foreground:
                if code == ecodes.KEY_LEFTMETA and value == 1:
                    GLib.idle_add(self.show_osk)
                continue

            profile = self._remote_profile_for_class(self.foreground_task_class)
            managed = (
                profile is not None
                and not self.launcher_foreground
                and self.remote_device_grabbed
            )

            if not managed:
                if code == ecodes.KEY_LEFTMETA and value == 1:
                    GLib.idle_add(self.show_osk)
                continue

            # Menu short = OSK; long = switch larger app area (F6).
            if code == ecodes.KEY_LEFTMETA:
                if value == 1:
                    self.remote_menu_started = time.monotonic()
                    self.remote_menu_class = self.foreground_task_class
                elif value == 0 and self.remote_menu_started is not None:
                    started = self.remote_menu_started
                    app_class = self.remote_menu_class
                    self.remote_menu_started = None
                    self.remote_menu_class = None
                    held = time.monotonic() - started
                    if held >= self.remote_menu_hold_threshold:
                        self._remote_cycle_application_area(app_class)
                    else:
                        GLib.idle_add(self.show_osk)
                continue

            # OK short = activate; long = switch NAV/MEDIA mode.
            if code == ecodes.KEY_ENTER:
                if value == 1:
                    self.remote_ok_started = time.monotonic()
                    self.remote_ok_class = self.foreground_task_class
                elif value == 0 and self.remote_ok_started is not None:
                    started = self.remote_ok_started
                    app_class = self.remote_ok_class
                    self.remote_ok_started = None
                    self.remote_ok_class = None
                    held = time.monotonic() - started
                    if held >= self.remote_ok_hold_threshold:
                        self._toggle_remote_mode(app_class)
                    else:
                        self._remote_short_ok(app_class)
                continue

            if value not in (1, 2):
                continue

            mode = self._remote_mode_for_class(self.foreground_task_class)
            if mode == "nav":
                self._remote_send_nav(code, profile)
            elif mode == "media":
                self._remote_send_media(code)

        return True

    def show_osk(self):
        self._set_remote_grab(False)
        return ShieldLauncher.show_osk(self)

    def hide_osk(self):
        ShieldLauncher.hide_osk(self)
        GLib.idle_add(self._sync_remote_layer)

    def show_task_manager(self):
        self._set_remote_grab(False)
        return ShieldLauncher.show_task_manager(self)

    def message(self, text):
        self.remote_modal_active = True
        self._set_remote_grab(False)
        try:
            return ShieldLauncher.message(self, text)
        finally:
            self.remote_modal_active = False
            GLib.idle_add(self._sync_remote_layer)

    def _focus_launcher_window(self):
        if not self.launcher_foreground:
            return False
        helper = SHIELD_TASKS_HELPER
        try:
            subprocess.run(
                [helper, "activate", LAUNCHER_APP_ID],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
        except Exception:
            pass
        try:
            self.present()
            self.focus_current()
        except Exception:
            pass
        return False

    def show_launcher(self):
        self.launcher_foreground = True
        self._set_remote_grab(False)
        result = ShieldLauncher.show_launcher(self)
        self._ensure_osk_remote_device()
        GLib.idle_add(self.focus_current)
        GLib.timeout_add(80, self._focus_launcher_window)
        GLib.timeout_add(260, self._focus_launcher_window)
        return result

    def _release_osk_remote_device(self):
        self._set_remote_grab(False)
        return ShieldLauncher._release_osk_remote_device(self)


launcher = ShieldLauncherNeon()
Gtk.main()
