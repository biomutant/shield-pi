#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
try:
    gi.require_version('GdkX11', '3.0')
except ValueError:
    pass

from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
try:
    from gi.repository import GdkX11  # noqa: F401 - adds get_xid() on X11 windows
except Exception:
    GdkX11 = None

import json
import os
import socket
import subprocess
import time
from pathlib import Path

try:
    import vlc
except ImportError:
    vlc = None

APP_ID = 'shield-vlc.py'
APP_TITLE = 'Shield VLC TV'
HOME = Path.home()
RUNTIME_DIR = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
CONTROL_SOCKET = RUNTIME_DIR / 'shield-vlc-control.sock'
USB_HUB = RUNTIME_DIR / 'shield-vlc-usb'
EXTERNAL_MEDIA_TITLE = 'USB / DISC'
STATE_DIR = HOME / '.config' / 'shield-vlc'
STATE_FILE = STATE_DIR / 'state.json'
SETTINGS_FILE = STATE_DIR / 'settings.json'
BG_CANDIDATES = [
    HOME / '.config' / 'shield-launcher' / 'shield-background-crt.png',
    Path(__file__).resolve().with_name('shield-background-crt.png'),
]
PLAYABLE_EXTS = {
    '.3gp', '.aac', '.ac3', '.avi', '.flac', '.flv', '.m2ts', '.m4a', '.m4v',
    '.mkv', '.mov', '.mp3', '.mp4', '.mpeg', '.mpg', '.mts', '.ogg', '.ogv',
    '.opus', '.ts', '.vob', '.wav', '.webm', '.wma', '.wmv', '.m3u', '.m3u8'
}


def text_of(value):
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return str(value)


def fmt_time(ms):
    if ms is None or ms < 0:
        return '--:--'
    sec = int(ms // 1000)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m:02d}:{s:02d}'


class Background(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.pixbuf = None
        for p in BG_CANDIDATES:
            if p.is_file():
                try:
                    self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(p))
                    break
                except Exception:
                    pass
        self.connect('draw', self._draw)

    def _draw(self, widget, cr):
        a = self.get_allocation()
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, a.width, a.height)
        cr.fill()
        if self.pixbuf:
            w, h = self.pixbuf.get_width(), self.pixbuf.get_height()
            scale = max(a.width / max(1, w), a.height / max(1, h))
            nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
            try:
                pix = self.pixbuf.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
                x, y = (a.width - nw) // 2, (a.height - nh) // 2
                Gdk.cairo_set_source_pixbuf(cr, pix, x, y)
                cr.paint()
                # Dark veil so TV controls stay readable without losing the CRT landscape.
                cr.set_source_rgba(0, 0, 0, 0.28)
                cr.rectangle(0, 0, a.width, a.height)
                cr.fill()
            except Exception:
                pass
        return False


class ShieldVlcTV(Gtk.Window):
    def __init__(self):
        GLib.set_prgname(APP_ID)
        super().__init__(title=APP_TITLE)
        try:
            self.set_wmclass(APP_ID, APP_ID)
        except Exception:
            pass
        self.set_name('shield-vlc-window')
        self.set_decorated(False)
        self.fullscreen()
        self.set_default_size(720, 576)
        self.connect('destroy', self._on_destroy)
        self.connect('key-press-event', self._on_key)

        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load_json(STATE_FILE, {'recent': []})
        self.settings = self._load_json(SETTINGS_FILE, {
            'seek_seconds': 10,
            'default_aspect': 'Auto',
        })

        self.mode = 'home'
        self.return_mode = 'home'
        self.browser_dir = HOME
        self.browser_root = HOME
        self.browser_exit_mode = 'home'
        self.browser_items = []
        self.browser_index = 0
        self.recent_items = []
        self.recent_index = 0
        self.home_index = 0
        self.settings_index = 0
        self.external_items = []
        self.external_index = 0
        self.optical_source_device = None
        self.optical_source_kind = None
        self.player_control_index = 0
        self.player_menu_items = []
        self.player_menu_index = 0
        self.player_menu_kind = None
        self.controls_visible = False
        self.current_source = None
        self.current_title = ''

        # Classic shuttle seek.  For normal files we move the timeline ourselves.
        # DVD/Blu-ray forward shuttle is different: repeated set_time() calls can
        # hit DVD navigation/title/cell boundaries and cause a title/menu restart.
        # Therefore optical forward shuttle uses libVLC's native positive playback
        # rate so the DVD/BD navigator itself crosses those boundaries.  Reverse
        # remains deterministic timed seeking because negative playback rates are
        # not reliably supported by libVLC inputs/codecs.
        self.shuttle_speeds = (2, 4, 8, 16, 32)
        self.shuttle_direction = 0
        self.shuttle_level = 0
        self.shuttle_last_tick = 0.0
        self.shuttle_native_rate = False

        # Direct Shield-Remote IPC.  The TV frontend is an XWayland window for
        # libVLC video embedding; sending synthetic keyboard events through the
        # compositor is not reliable on every Pi/labwc combination.  A local
        # Unix datagram socket lets our own remote daemon drive this UI directly.
        self.control_socket = None
        self.control_watch_id = 0

        self.instance = None
        self.player = None
        if vlc is not None:
            try:
                self.instance = vlc.Instance(
                    '--no-video-title-show',
                    '--quiet',
                    '--no-snapshot-preview',
                    '--network-caching=1200',
                )
                self.player = self.instance.media_player_new()
                em = self.player.event_manager()
                em.event_attach(vlc.EventType.MediaPlayerEndReached, self._vlc_end)
                em.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._vlc_error)
            except Exception as e:
                print('libVLC init error:', e, flush=True)
                self.instance = None
                self.player = None

        self._build_ui()
        self._load_css()
        self.show_all()
        self._show_home()
        self._start_control_socket()
        GLib.timeout_add(400, self._update_player_status)
        GLib.timeout_add(100, self._shuttle_tick)

    # ---------------- state ----------------
    def _load_json(self, path, default):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else dict(default)
        except Exception:
            return dict(default)

    def _save_json(self, path, data):
        try:
            tmp = path.with_suffix(path.suffix + '.tmp')
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            tmp.replace(path)
        except Exception:
            pass

    def _remember_recent(self, source):
        if not source:
            return
        src = str(source)
        recent = [x for x in self.state.get('recent', []) if x != src]
        recent.insert(0, src)
        self.state['recent'] = recent[:30]
        self._save_json(STATE_FILE, self.state)

    # ---------------- base UI ----------------
    def _build_ui(self):
        self.base = Gtk.Overlay()
        self.add(self.base)
        bg = Background()
        bg.set_hexpand(True)
        bg.set_vexpand(True)
        self.base.add(bg)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(100)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.base.add_overlay(self.stack)

        self.home_page = self._build_home_page()
        self.browser_page = self._build_browser_page()
        self.recent_page = self._build_recent_page()
        self.network_page = self._build_network_page()
        self.external_page = self._build_external_page()
        self.settings_page = self._build_settings_page()
        self.player_page = self._build_player_page()
        self.message_page = self._build_message_page()

        for name, page in [
            ('home', self.home_page), ('browser', self.browser_page),
            ('recent', self.recent_page), ('network', self.network_page),
            ('external', self.external_page), ('settings', self.settings_page), ('player', self.player_page),
            ('message', self.message_page),
        ]:
            self.stack.add_named(page, name)

    def _header(self, title, subtitle=''):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title_label = Gtk.Label(label=title)
        title_label.set_name('screen-title')
        title_label.set_halign(Gtk.Align.START)
        box.pack_start(title_label, False, False, 0)
        if subtitle:
            sub = Gtk.Label(label=subtitle)
            sub.set_name('screen-subtitle')
            sub.set_halign(Gtk.Align.START)
            box.pack_start(sub, False, False, 0)
        return box

    def _build_home_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(24)
        outer.set_margin_bottom(24)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.pack_start(self._header('SHIELD VLC', 'TV MEDIA CENTER'), False, False, 0)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)
        outer.pack_start(grid, True, True, 0)

        entries = [
            ('Videos', 'Lokale Videos'),
            ('Ordner', 'Dateien durchsuchen'),
            ('Zuletzt', 'Zuletzt abgespielt'),
            ('Netzwerk', 'Stream / URL'),
            ('USB / Disc', 'Stick, DVD, Blu-ray'),
            ('Einstellungen', 'Player anpassen'),
        ]
        self.home_buttons = []
        for i, (name, sub) in enumerate(entries):
            b = Gtk.Button()
            b.set_name('home-card')
            b.set_size_request(205, 126)
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            content.set_halign(Gtk.Align.CENTER)
            content.set_valign(Gtk.Align.CENTER)
            l = Gtk.Label(label=name)
            l.set_name('home-card-title')
            s = Gtk.Label(label=sub)
            s.set_name('home-card-subtitle')
            content.pack_start(l, False, False, 0)
            content.pack_start(s, False, False, 0)
            b.add(content)
            grid.attach(b, i % 3, i // 3, 1, 1)
            self.home_buttons.append(b)
        footer = Gtk.Label(label='Pfeile Navigieren   OK Öffnen   Netflix Player-Menü   Home Launcher')
        footer.set_name('footer')
        outer.pack_end(footer, False, False, 0)
        return outer

    def _build_browser_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(18); outer.set_margin_bottom(18)
        outer.set_margin_start(22); outer.set_margin_end(22)
        self.browser_title = Gtk.Label(label='ORDNER')
        self.browser_title.set_name('screen-title'); self.browser_title.set_halign(Gtk.Align.START)
        self.browser_path = Gtk.Label(label='')
        self.browser_path.set_name('path'); self.browser_path.set_halign(Gtk.Align.START)
        self.browser_path.set_ellipsize(3)
        outer.pack_start(self.browser_title, False, False, 0)
        outer.pack_start(self.browser_path, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.browser_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroll.add(self.browser_list)
        outer.pack_start(scroll, True, True, 0)
        hint = Gtk.Label(label='↑ ↓ Auswählen   OK Öffnen/Abspielen   Zurück Ordner höher')
        hint.set_name('footer'); hint.set_halign(Gtk.Align.START)
        outer.pack_end(hint, False, False, 0)
        return outer

    def _build_external_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(18); outer.set_margin_bottom(18)
        outer.set_margin_start(22); outer.set_margin_end(22)
        outer.pack_start(self._header('USB / DISC', 'Externe Medien und optische Laufwerke'), False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.external_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroll.add(self.external_list)
        outer.pack_start(scroll, True, True, 0)
        hint = Gtk.Label(label='↑ ↓ Auswählen   OK Öffnen/Ausführen   Zurück Hauptmenü')
        hint.set_name('footer'); hint.set_halign(Gtk.Align.START)
        outer.pack_end(hint, False, False, 0)
        return outer

    def _build_recent_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(18); outer.set_margin_bottom(18)
        outer.set_margin_start(22); outer.set_margin_end(22)
        outer.pack_start(self._header('ZULETZT', 'Zuletzt abgespielte Medien'), False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.recent_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroll.add(self.recent_list)
        outer.pack_start(scroll, True, True, 0)
        hint = Gtk.Label(label='↑ ↓ Auswählen   OK Abspielen   Zurück Hauptmenü')
        hint.set_name('footer'); hint.set_halign(Gtk.Align.START)
        outer.pack_end(hint, False, False, 0)
        return outer

    def _build_network_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        outer.set_margin_top(40); outer.set_margin_bottom(30)
        outer.set_margin_start(46); outer.set_margin_end(46)
        outer.pack_start(self._header('NETZWERK', 'Stream-Adresse eingeben'), False, False, 0)
        self.network_entry = Gtk.Entry()
        self.network_entry.set_name('network-entry')
        self.network_entry.set_placeholder_text('https://…  oder  smb://…')
        self.network_entry.set_size_request(-1, 62)
        outer.pack_start(self.network_entry, False, False, 16)
        note = Gtk.Label(label='Mikrofontaste öffnet die virtuelle Tastatur.\nOK startet die eingegebene Adresse.')
        note.set_name('screen-subtitle'); note.set_justify(Gtk.Justification.LEFT); note.set_halign(Gtk.Align.START)
        outer.pack_start(note, False, False, 0)
        return outer

    def _build_settings_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(20); outer.set_margin_bottom(20)
        outer.set_margin_start(30); outer.set_margin_end(30)
        outer.pack_start(self._header('EINSTELLUNGEN', 'Nur wichtige TV-Optionen'), False, False, 0)
        self.settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.pack_start(self.settings_box, True, True, 12)
        hint = Gtk.Label(label='↑ ↓ Auswählen   OK Wert ändern   Zurück Hauptmenü')
        hint.set_name('footer'); hint.set_halign(Gtk.Align.START)
        outer.pack_end(hint, False, False, 0)
        return outer

    def _build_player_page(self):
        overlay = Gtk.Overlay()
        overlay.set_name('player-page')
        self.video_area = Gtk.DrawingArea()
        self.video_area.set_name('video-area')
        self.video_area.set_hexpand(True); self.video_area.set_vexpand(True)
        self.video_area.connect('realize', self._video_realize)
        overlay.add(self.video_area)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top.set_name('player-top')
        top.set_margin_top(12); top.set_margin_start(16); top.set_margin_end(16)
        top.set_halign(Gtk.Align.FILL); top.set_valign(Gtk.Align.START)
        self.player_title = Gtk.Label(label='')
        self.player_title.set_name('player-title'); self.player_title.set_halign(Gtk.Align.START)
        self.player_title.set_ellipsize(3)
        top.pack_start(self.player_title, True, True, 0)
        self.player_time = Gtk.Label(label='00:00 / 00:00')
        self.player_time.set_name('player-time'); self.player_time.set_halign(Gtk.Align.END)
        top.pack_end(self.player_time, False, False, 0)
        overlay.add_overlay(top)
        self.player_top = top

        self.shuttle_label = Gtk.Label(label='')
        self.shuttle_label.set_name('shuttle-label')
        self.shuttle_label.set_halign(Gtk.Align.CENTER)
        self.shuttle_label.set_valign(Gtk.Align.START)
        self.shuttle_label.set_margin_top(72)
        overlay.add_overlay(self.shuttle_label)
        self.shuttle_label.hide()

        self.controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.controls.set_name('player-controls')
        self.controls.set_margin_start(16); self.controls.set_margin_end(16); self.controls.set_margin_bottom(15)
        self.controls.set_valign(Gtk.Align.END); self.controls.set_halign(Gtk.Align.FILL)
        self.progress = Gtk.ProgressBar(); self.progress.set_name('progress')
        self.controls.pack_start(self.progress, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        row.set_halign(Gtk.Align.CENTER)
        # Transport/seek is intentionally NOT present in this D-pad menu.
        # << and >> are dedicated physical remote buttons handled by shield-remote.
        labels = ['Play / Pause', 'Audio', 'Untertitel', 'Bild', 'Info', 'Stop']
        self.control_buttons = []
        for label in labels:
            b = Gtk.Button(label=label)
            b.set_name('player-control')
            b.set_size_request(78 if label != 'Play / Pause' else 112, 54)
            row.pack_start(b, False, False, 0)
            self.control_buttons.append(b)
        self.controls.pack_start(row, False, False, 0)
        overlay.add_overlay(self.controls)

        self.menu_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.menu_panel.set_name('player-menu')
        self.menu_panel.set_size_request(430, -1)
        self.menu_panel.set_halign(Gtk.Align.CENTER); self.menu_panel.set_valign(Gtk.Align.CENTER)
        self.menu_title = Gtk.Label(label='')
        self.menu_title.set_name('menu-title')
        self.menu_panel.pack_start(self.menu_title, False, False, 10)
        self.menu_items_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.menu_panel.pack_start(self.menu_items_box, False, False, 0)
        overlay.add_overlay(self.menu_panel)
        self.menu_panel.hide()
        return overlay

    def _build_message_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(80); outer.set_margin_start(50); outer.set_margin_end(50)
        self.message_title = Gtk.Label(label='HINWEIS')
        self.message_title.set_name('screen-title')
        self.message_text = Gtk.Label(label='')
        self.message_text.set_name('message-text'); self.message_text.set_line_wrap(True)
        self.message_text.set_justify(Gtk.Justification.CENTER)
        outer.pack_start(self.message_title, False, False, 0)
        outer.pack_start(self.message_text, True, True, 20)
        hint = Gtk.Label(label='OK oder Zurück')
        hint.set_name('footer')
        outer.pack_end(hint, False, False, 10)
        return outer

    def _load_css(self):
        css = b'''
        #shield-vlc-window { background: #000000; }
        #screen-title { color: #ffffff; font-size: 30px; font-weight: 800; letter-spacing: 3px; }
        #screen-subtitle { color: #d8e2d0; font-size: 16px; font-weight: 600; }
        #path { color: #a8ff22; font-size: 16px; font-weight: bold; }
        #footer { color: #f0f0f0; font-size: 13px; font-weight: 600; }
        #home-card, #list-row, #setting-row, #player-control, #menu-row {
            background: rgba(4, 10, 7, 0.94);
            color: #ffffff;
            border: 2px solid rgba(154,255,25,0.72);
            border-radius: 6px;
            box-shadow: inset 0 0 16px rgba(90,255,0,0.08);
        }
        #home-card:focus, #list-row:focus, #setting-row:focus, #player-control:focus, #menu-row:focus {
            border: 4px solid #a6ff20;
            box-shadow: 0 0 14px rgba(150,255,30,0.95), inset 0 0 20px rgba(100,255,0,0.18);
            background: rgba(12, 25, 13, 0.98);
        }
        #home-card-title { color: #ffffff; font-size: 22px; font-weight: 800; }
        #home-card-subtitle { color: #cbd8c7; font-size: 12px; font-weight: 600; }
        #list-row { font-size: 17px; font-weight: 700; padding: 8px; }
        #setting-row { font-size: 18px; font-weight: 700; padding: 10px; }
        #network-entry { background: rgba(0,0,0,0.92); color: white; border: 3px solid #9cff1a; font-size: 20px; padding: 8px; }
        #player-page, #video-area { background: #000000; }
        #player-top { background: rgba(0,0,0,0.64); padding: 7px; }
        #player-title { color: white; font-size: 17px; font-weight: 800; }
        #player-time { color: #a6ff20; font-size: 16px; font-weight: 800; }
        #shuttle-label {
            color: #a6ff20;
            background: rgba(0,0,0,0.88);
            border: 3px solid #9cff1a;
            border-radius: 7px;
            font-size: 28px;
            font-weight: 900;
            padding: 8px 18px;
        }
        #player-controls { background: rgba(0,0,0,0.78); border: 2px solid rgba(156,255,26,0.65); border-radius: 8px; padding: 10px; }
        #player-control { font-size: 13px; font-weight: 800; }
        #progress trough { min-height: 8px; background: #263020; }
        #progress progress { min-height: 8px; background: #9cff1a; }
        #player-menu { background: rgba(0,0,0,0.94); border: 3px solid #9cff1a; border-radius: 8px; padding: 14px; }
        #menu-title { color: #a6ff20; font-size: 22px; font-weight: 800; }
        #menu-row { font-size: 16px; font-weight: 700; padding: 7px; }
        #message-text { color: white; font-size: 20px; font-weight: 700; }
        '''
        p = Gtk.CssProvider(); p.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ---------------- home/navigation ----------------
    def _show_home(self):
        self.mode = 'home'; self.stack.set_visible_child_name('home')
        self.home_index = max(0, min(self.home_index, len(self.home_buttons)-1))
        GLib.idle_add(self.home_buttons[self.home_index].grab_focus)

    def _activate_home(self):
        idx = self.home_index
        if idx == 0:
            self._open_browser(self._videos_dir(), 'VIDEOS')
        elif idx == 1:
            self._open_browser(HOME, 'ORDNER')
        elif idx == 2:
            self._show_recent()
        elif idx == 3:
            self.mode = 'network'; self.stack.set_visible_child_name('network')
            GLib.idle_add(self.network_entry.grab_focus)
        elif idx == 4:
            self._show_external_media()
        elif idx == 5:
            self._show_settings()

    def _lsblk_tree(self):
        """Return lsblk JSON for removable/USB media discovery."""
        try:
            r = subprocess.run(
                [
                    'lsblk', '-J',
                    '-o', 'NAME,PATH,PKNAME,TYPE,FSTYPE,LABEL,MOUNTPOINTS,RM,TRAN,SIZE,MODEL,VENDOR'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=3,
            )
            if r.returncode != 0:
                return []
            data = json.loads(r.stdout or '{}')
            return data.get('blockdevices') or []
        except Exception:
            return []

    def _usb_block_devices(self):
        """Find filesystem-bearing partitions that belong to a USB/removable disk."""
        found = []

        def walk(node, inherited_usb=False, drive_path=None):
            tran = str(node.get('tran') or '').lower()
            try:
                removable = int(node.get('rm') or 0) == 1
            except Exception:
                removable = bool(node.get('rm'))
            ntype = str(node.get('type') or '')
            path = str(node.get('path') or '').strip()
            is_usb = inherited_usb or tran == 'usb' or removable
            if ntype == 'disk' and path:
                drive_path = path
            fstype = str(node.get('fstype') or '').strip()
            if is_usb and path and fstype and ntype in ('part', 'crypt', 'lvm', 'disk'):
                mps = node.get('mountpoints')
                if isinstance(mps, str):
                    mps = [mps]
                elif not isinstance(mps, list):
                    mps = []
                found.append({
                    'path': path,
                    'drive_path': drive_path or path,
                    'label': str(node.get('label') or '').strip(),
                    'fstype': fstype,
                    'size': str(node.get('size') or '').strip(),
                    'mountpoints': [str(x) for x in mps if x],
                    'tran': tran,
                    'model': str(node.get('model') or '').strip(),
                    'vendor': str(node.get('vendor') or '').strip(),
                })
            for child in node.get('children') or []:
                walk(child, is_usb, drive_path)

        for node in self._lsblk_tree():
            walk(node, False, None)

        unique = {}
        for item in found:
            unique[item['path']] = item
        return list(unique.values())

    def _mount_usb_device(self, devpath):
        """Ask udisks2 to mount one removable filesystem as the logged-in user."""
        if not devpath:
            return False
        try:
            env = os.environ.copy()
            env.setdefault('XDG_RUNTIME_DIR', str(RUNTIME_DIR))
            env.setdefault('DBUS_SESSION_BUS_ADDRESS', f'unix:path={RUNTIME_DIR}/bus')
            r = subprocess.run(
                ['udisksctl', 'mount', '-b', devpath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                timeout=12,
            )
            if r.returncode == 0:
                print('USB mounted:', devpath, r.stdout.strip(), flush=True)
                return True
            print('USB mount failed:', devpath, r.stderr.strip(), flush=True)
        except Exception as e:
            print('USB mount error:', devpath, e, flush=True)
        return False

    def _usb_mounts(self):
        """Return readable USB mount points, mounting unmounted devices first."""
        devices = self._usb_block_devices()
        for item in devices:
            if not item.get('mountpoints'):
                self._mount_usb_device(item.get('path'))

        # Re-read after mounting.
        devices = self._usb_block_devices()
        mounts = []
        seen = set()
        for item in devices:
            for mp in item.get('mountpoints') or []:
                p = Path(mp)
                try:
                    good = p.is_dir()
                except Exception:
                    good = False
                if not good:
                    continue
                key = str(p)
                if key in seen:
                    continue
                seen.add(key)
                mounts.append({
                    'path': p,
                    'label': item.get('label') or p.name or item.get('path'),
                    'size': item.get('size') or '',
                    'devpath': item.get('path') or '',
                    'drive_path': item.get('drive_path') or item.get('path') or '',
                })

        # Fallback for media already mounted by another desktop component.
        for base in (
            Path('/media') / HOME.name,
            Path('/run/media') / HOME.name,
            Path('/media'),
            Path('/run/media'),
            Path('/mnt'),
        ):
            try:
                if not base.is_dir():
                    continue
                for p in base.iterdir():
                    if not p.is_dir():
                        continue
                    key = str(p)
                    if key in seen:
                        continue
                    # Only use fallback roots that contain something; this avoids
                    # displaying empty system mount folders as USB media.
                    try:
                        next(p.iterdir())
                    except StopIteration:
                        continue
                    except Exception:
                        continue
                    seen.add(key)
                    mounts.append({'path': p, 'label': p.name, 'size': '', 'devpath': '', 'drive_path': ''})
            except Exception:
                pass
        return mounts

    def _udev_props(self, devpath):
        if not devpath:
            return {}
        try:
            r = subprocess.run(
                ['udevadm', 'info', '--query=property', '--name', devpath],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=3,
            )
            if r.returncode != 0:
                return {}
            out = {}
            for line in r.stdout.splitlines():
                if '=' in line:
                    k, v = line.split('=', 1)
                    out[k.strip()] = v.strip()
            return out
        except Exception:
            return {}

    def _optical_drives(self):
        drives = []
        for node in self._lsblk_tree():
            stack = [node]
            while stack:
                cur = stack.pop(0)
                stack.extend(cur.get('children') or [])
                if str(cur.get('type') or '') != 'rom':
                    continue
                dev = str(cur.get('path') or '').strip()
                if not dev:
                    continue
                props = self._udev_props(dev)
                media = None
                if any(props.get(k) == '1' for k in ('ID_CDROM_MEDIA_BD','ID_CDROM_MEDIA_BD_R','ID_CDROM_MEDIA_BD_RE')):
                    media = 'bluray'
                elif any(props.get(k) == '1' for k in ('ID_CDROM_MEDIA_DVD','ID_CDROM_MEDIA_DVD_R','ID_CDROM_MEDIA_DVD_RW','ID_CDROM_MEDIA_DVD_RAM','ID_CDROM_MEDIA_DVD_PLUS_R','ID_CDROM_MEDIA_DVD_PLUS_RW')):
                    media = 'dvd'
                elif any(props.get(k) == '1' for k in ('ID_CDROM_MEDIA_CD','ID_CDROM_MEDIA_CD_R','ID_CDROM_MEDIA_CD_RW')):
                    media = 'cdda'
                elif props.get('ID_CDROM_MEDIA') == '1':
                    media = 'disc'
                mps = cur.get('mountpoints')
                if isinstance(mps, str):
                    mps = [mps]
                elif not isinstance(mps, list):
                    mps = []
                model = ' '.join(x for x in [str(cur.get('vendor') or '').strip(), str(cur.get('model') or '').strip()] if x).strip()
                drives.append({
                    'path': dev,
                    'media': media,
                    'label': str(cur.get('label') or '').strip(),
                    'mountpoints': [str(x) for x in mps if x],
                    'tran': str(cur.get('tran') or props.get('ID_BUS') or '').lower(),
                    'model': model or props.get('ID_MODEL_FROM_DATABASE') or props.get('ID_MODEL') or Path(dev).name,
                })
        return drives

    def _optical_mrl(self, item):
        dev = item.get('path') or '/dev/sr0'
        kind = item.get('media')
        if kind == 'bluray':
            return f'bluray:///{dev}'
        if kind == 'dvd':
            return f'dvd:///{dev}'
        if kind == 'cdda':
            return f'cdda:///{dev}'
        return None

    def _all_drive_nodes(self, drive_path):
        result = []
        def walk(node, active=False):
            path = str(node.get('path') or '')
            active = active or path == drive_path
            if active and path:
                mps = node.get('mountpoints')
                if isinstance(mps, str): mps = [mps]
                elif not isinstance(mps, list): mps = []
                result.append((path, [str(x) for x in mps if x]))
            for child in node.get('children') or []:
                walk(child, active)
        for node in self._lsblk_tree():
            walk(node, False)
        return result

    def _stop_if_device_in_use(self, drive_path=None, devpath=None):
        src = str(self.current_source or '')
        must_stop = False
        if devpath and devpath in src:
            must_stop = True
        if drive_path:
            for _path, mps in self._all_drive_nodes(drive_path):
                for mp in mps:
                    if src.startswith(mp.rstrip('/') + '/') or src == mp:
                        must_stop = True
        if must_stop:
            try:
                if self.player:
                    self.player.stop()
            except Exception:
                pass
            self.current_source = None
            self.optical_source_device = None
            self.optical_source_kind = None

    def _udisks(self, *args, timeout=15):
        env = os.environ.copy()
        env.setdefault('XDG_RUNTIME_DIR', str(RUNTIME_DIR))
        env.setdefault('DBUS_SESSION_BUS_ADDRESS', f'unix:path={RUNTIME_DIR}/bus')
        try:
            return subprocess.run(
                ['udisksctl', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env, timeout=timeout,
            )
        except Exception as e:
            print('udisksctl error:', e, flush=True)
            return None

    def _safe_remove_usb(self, drive_path):
        if not drive_path:
            self._message('NICHT MÖGLICH', 'Das physische USB-Laufwerk konnte nicht bestimmt werden.', 'external')
            return
        self._stop_if_device_in_use(drive_path=drive_path)
        errors = []
        # Children first, then whole-disk filesystem if there is one.
        nodes = self._all_drive_nodes(drive_path)
        for path, mps in reversed(nodes):
            if not mps:
                continue
            r = self._udisks('unmount', '-b', path)
            if r is not None and r.returncode != 0 and 'not mounted' not in (r.stderr or '').lower():
                errors.append((r.stderr or r.stdout or path).strip())
        r = self._udisks('power-off', '-b', drive_path)
        if r is None or r.returncode != 0:
            detail = ((r.stderr or r.stdout).strip() if r is not None else 'udisksctl konnte nicht gestartet werden')
            errors.append(detail or 'USB-Laufwerk konnte nicht abgeschaltet werden')
        if errors:
            self._message('SICHERES ENTFERNEN', 'Aushängen/Abschalten nicht vollständig gelungen:\n' + '\n'.join(errors[:3]), 'external')
        else:
            self._message('SICHER ENTFERNT', 'USB-Laufwerk wurde ausgehängt und abgeschaltet.\nEs kann jetzt abgezogen werden.', 'external')

    def _eject_optical(self, devpath, power_off=False):
        if not devpath:
            return
        self._stop_if_device_in_use(devpath=devpath)
        # Unmount a data disc first if the desktop/udisks mounted it.
        for path, mps in reversed(self._all_drive_nodes(devpath)):
            if mps:
                self._udisks('unmount', '-b', path)
        eject_error = ''
        try:
            r = subprocess.run(['eject', devpath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12)
            if r.returncode != 0:
                eject_error = (r.stderr or r.stdout or '').strip()
        except Exception as e:
            eject_error = str(e)
        if power_off:
            r2 = self._udisks('power-off', '-b', devpath)
            if r2 is not None and r2.returncode == 0:
                self._message('LAUFWERK SICHER ENTFERNT', 'Disc wurde freigegeben und das externe Laufwerk abgeschaltet.\nEs kann jetzt abgezogen werden.', 'external')
                return
            detail = ((r2.stderr or r2.stdout).strip() if r2 is not None else '')
            text = 'Disc wurde ausgeworfen, aber das USB-Laufwerk konnte nicht vollständig abgeschaltet werden.'
            if detail: text += '\n' + detail
            self._message('LAUFWERK FREIGEGEBEN', text, 'external')
            return
        if eject_error:
            self._message('AUSWERFEN FEHLGESCHLAGEN', eject_error, 'external')
        else:
            self._message('DISC AUSGEWORFEN', 'Die Disc kann entnommen werden.', 'external')

    def _show_external_media(self):
        self.external_items = []
        mounts = self._usb_mounts()
        # Group USB volumes by physical drive. Open rows come first, followed by one safe-remove row per drive.
        drive_labels = {}
        for item in mounts:
            drive = item.get('drive_path') or item.get('devpath') or ''
            label = item.get('label') or item.get('path').name or 'USB-Medium'
            size = item.get('size') or ''
            suffix = f'  ·  {size}' if size else ''
            self.external_items.append({
                'kind': 'usb-open', 'label': f'USB  ▶  {label}{suffix}',
                'path': item.get('path'), 'drive_path': drive,
            })
            if drive:
                drive_labels.setdefault(drive, label)
        for drive, label in drive_labels.items():
            self.external_items.append({
                'kind': 'usb-remove', 'label': f'USB  ⏏  {label} sicher entfernen',
                'drive_path': drive,
            })

        for item in self._optical_drives():
            dev = item.get('path')
            model = item.get('model') or Path(dev).name
            kind = item.get('media')
            if kind == 'bluray':
                media_name = 'Blu-ray'
            elif kind == 'dvd':
                media_name = 'DVD'
            elif kind == 'cdda':
                media_name = 'Audio-CD'
            elif kind:
                media_name = 'Disc'
            else:
                media_name = 'Keine Disc'
            mrl = self._optical_mrl(item)
            if mrl:
                self.external_items.append({
                    'kind': 'disc-play', 'label': f'{media_name}  ▶  {model}',
                    'source': mrl, 'devpath': dev, 'disc_kind': kind,
                })
            else:
                self.external_items.append({
                    'kind': 'disc-info', 'label': f'{media_name}  ·  {model}', 'devpath': dev,
                })
            if kind:
                self.external_items.append({
                    'kind': 'disc-eject', 'label': f'Disc  ⏏  auswerfen ({model})', 'devpath': dev,
                })
            if item.get('tran') == 'usb':
                self.external_items.append({
                    'kind': 'disc-remove', 'label': f'Laufwerk  ⏏  sicher entfernen ({model})', 'devpath': dev,
                })

        self.external_index = min(self.external_index, max(0, len(self.external_items)-1))
        for c in self.external_list.get_children():
            self.external_list.remove(c)
        if not self.external_items:
            l = Gtk.Label(label='Keine externen Medien gefunden')
            l.set_name('screen-subtitle'); self.external_list.pack_start(l, False, False, 20)
        else:
            for item in self.external_items:
                b = Gtk.Button(label=item.get('label') or 'Medium')
                b.set_name('list-row'); b.set_size_request(-1, 52); b.set_halign(Gtk.Align.FILL)
                self.external_list.pack_start(b, False, False, 0)
        self.external_list.show_all()
        self.mode = 'external'; self.stack.set_visible_child_name('external')
        self._focus_external()

    def _focus_external(self):
        buttons = [c for c in self.external_list.get_children() if isinstance(c, Gtk.Button)]
        if buttons:
            self.external_index = max(0, min(self.external_index, len(buttons)-1))
            GLib.idle_add(buttons[self.external_index].grab_focus)

    def _activate_external(self):
        if not self.external_items:
            return
        item = self.external_items[self.external_index]
        kind = item.get('kind')
        if kind == 'usb-open':
            root = item.get('path')
            self._open_browser(root, 'USB-MEDIEN', root=root, exit_mode='external')
        elif kind == 'usb-remove':
            self._safe_remove_usb(item.get('drive_path'))
        elif kind == 'disc-play':
            self.return_mode = 'external'
            self.optical_source_device = item.get('devpath')
            self.optical_source_kind = item.get('disc_kind')
            self._play(item.get('source'))
        elif kind == 'disc-eject':
            self._eject_optical(item.get('devpath'), False)
        elif kind == 'disc-remove':
            self._eject_optical(item.get('devpath'), True)
        else:
            self._message('OPTISCHES LAUFWERK', 'Laufwerk erkannt, aber aktuell ist keine abspielbare DVD/Blu-ray/CD eingelegt.', 'external')

    def _open_usb_media(self):
        # Compatibility entry point kept for older callers.
        self._show_external_media()

    def _videos_dir(self):
        try:
            r = subprocess.run(['xdg-user-dir', 'VIDEOS'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1)
            p = Path(r.stdout.strip())
            if p.exists(): return p
        except Exception:
            pass
        p = HOME / 'Videos'
        return p if p.exists() else HOME

    def _open_browser(self, path, title='ORDNER', root=None, exit_mode='home'):
        try: p = Path(path).expanduser().resolve()
        except Exception: p = Path(path).expanduser()
        if not p.exists() or not p.is_dir():
            self._message('ORDNER NICHT GEFUNDEN', str(p), 'home')
            return
        self.return_mode = 'browser'
        self.browser_dir = p
        if root is None:
            self.browser_root = HOME
        else:
            try:
                self.browser_root = Path(root).expanduser()
            except Exception:
                self.browser_root = p
        self.browser_exit_mode = exit_mode
        self.browser_title.set_text(title)
        self._refresh_browser()
        self.mode = 'browser'; self.stack.set_visible_child_name('browser')
        self._focus_browser()

    def _refresh_browser(self):
        self.browser_path.set_text(str(self.browser_dir))
        try:
            dirs, files = [], []
            for p in self.browser_dir.iterdir():
                if p.name.startswith('.'):
                    continue
                try:
                    if p.is_dir(): dirs.append(p)
                    elif p.suffix.lower() in PLAYABLE_EXTS: files.append(p)
                except OSError:
                    continue
            dirs.sort(key=lambda x: x.name.lower()); files.sort(key=lambda x: x.name.lower())
            self.browser_items = dirs + files
        except Exception:
            self.browser_items = []
        self.browser_index = min(self.browser_index, max(0, len(self.browser_items)-1))
        for c in self.browser_list.get_children(): self.browser_list.remove(c)
        if not self.browser_items:
            l = Gtk.Label(label='Keine abspielbaren Medien gefunden')
            l.set_name('screen-subtitle'); self.browser_list.pack_start(l, False, False, 20)
        else:
            for p in self.browser_items:
                prefix = '▸  ' if p.is_dir() else '▶  '
                b = Gtk.Button(label=prefix + p.name)
                b.set_name('list-row'); b.set_size_request(-1, 52)
                b.set_halign(Gtk.Align.FILL)
                self.browser_list.pack_start(b, False, False, 0)
        self.browser_list.show_all()

    def _focus_browser(self):
        children = [c for c in self.browser_list.get_children() if isinstance(c, Gtk.Button)]
        if children:
            self.browser_index = max(0, min(self.browser_index, len(children)-1))
            GLib.idle_add(children[self.browser_index].grab_focus)

    def _browser_activate(self):
        if not self.browser_items: return
        p = self.browser_items[self.browser_index]
        if p.is_dir():
            self.browser_dir = p; self.browser_index = 0; self._refresh_browser(); self._focus_browser()
        else:
            self.return_mode = 'browser'; self._play(str(p))

    def _browser_back(self):
        parent = self.browser_dir.parent
        root = getattr(self, 'browser_root', HOME)
        if parent != self.browser_dir and self.browser_dir != root:
            self.browser_dir = parent; self.browser_index = 0; self._refresh_browser(); self._focus_browser()
        else:
            if getattr(self, 'browser_exit_mode', 'home') == 'external':
                self._show_external_media()
            else:
                self._show_home()

    def _show_recent(self):
        self.mode = 'recent'; self.stack.set_visible_child_name('recent')
        self.recent_items = [x for x in self.state.get('recent', []) if x.startswith(('http://','https://','rtsp://','smb://')) or Path(x).exists()]
        self.recent_index = min(self.recent_index, max(0, len(self.recent_items)-1))
        for c in self.recent_list.get_children(): self.recent_list.remove(c)
        if not self.recent_items:
            l = Gtk.Label(label='Noch keine Medien abgespielt')
            l.set_name('screen-subtitle'); self.recent_list.pack_start(l, False, False, 18)
        else:
            for src in self.recent_items:
                name = Path(src).name if '://' not in src else src
                b = Gtk.Button(label='▶  ' + name)
                b.set_name('list-row'); b.set_size_request(-1, 52)
                self.recent_list.pack_start(b, False, False, 0)
        self.recent_list.show_all()
        self._focus_recent()

    def _focus_recent(self):
        buttons = [c for c in self.recent_list.get_children() if isinstance(c, Gtk.Button)]
        if buttons:
            self.recent_index = max(0, min(self.recent_index, len(buttons)-1))
            GLib.idle_add(buttons[self.recent_index].grab_focus)

    def _show_settings(self):
        self.mode = 'settings'; self.stack.set_visible_child_name('settings')
        for c in self.settings_box.get_children(): self.settings_box.remove(c)
        seek = int(self.settings.get('seek_seconds', 10))
        aspect = self.settings.get('default_aspect', 'Auto')
        rows = [f'Spulen: {seek} Sekunden', f'Standard-Bildformat: {aspect}', 'Verlauf löschen']
        self.setting_buttons = []
        for text in rows:
            b = Gtk.Button(label=text); b.set_name('setting-row'); b.set_size_request(-1, 62)
            self.settings_box.pack_start(b, False, False, 0); self.setting_buttons.append(b)
        self.settings_box.show_all(); self._focus_settings()

    def _focus_settings(self):
        if self.setting_buttons:
            self.settings_index = max(0, min(self.settings_index, len(self.setting_buttons)-1))
            GLib.idle_add(self.setting_buttons[self.settings_index].grab_focus)

    def _activate_setting(self):
        if self.settings_index == 0:
            vals = [10, 30, 60]
            cur = int(self.settings.get('seek_seconds', 10))
            self.settings['seek_seconds'] = vals[(vals.index(cur) + 1) % len(vals)] if cur in vals else 10
        elif self.settings_index == 1:
            vals = ['Auto', '4:3', '16:9']
            cur = self.settings.get('default_aspect', 'Auto')
            self.settings['default_aspect'] = vals[(vals.index(cur) + 1) % len(vals)] if cur in vals else 'Auto'
        elif self.settings_index == 2:
            self.state['recent'] = []; self._save_json(STATE_FILE, self.state)
        self._save_json(SETTINGS_FILE, self.settings)
        self._show_settings()

    # ---------------- player ----------------
    def _video_realize(self, area):
        self._attach_video()

    def _attach_video(self):
        if not self.player: return
        try:
            gw = self.video_area.get_window()
            if gw is None: return
            xid = gw.get_xid()
            self.player.set_xwindow(int(xid))
        except Exception as e:
            print('Video-XID attach error:', e, flush=True)

    def _play(self, source):
        if not self.player or not self.instance:
            self._message('LIBVLC FEHLT', 'python3-vlc konnte nicht geladen werden.\nInstallation: sudo apt install python3-vlc', self.return_mode)
            return
        self.current_source = source
        if not str(source).startswith(('dvd://', 'bluray://', 'cdda://')):
            self.optical_source_device = None
            self.optical_source_kind = None
        self.current_title = Path(source).name if '://' not in source else source
        self.player_title.set_text(self.current_title)
        self.mode = 'player'; self.stack.set_visible_child_name('player')
        self.controls_visible = False; self.controls.hide(); self.player_top.hide(); self.menu_panel.hide()
        self.player_menu_kind = None
        self._reset_shuttle_state(resume=False)
        try:
            media = self.instance.media_new(source)
            self.player.set_media(media)
            self._attach_video()
            self.player.play()
            self._remember_recent(source)
            GLib.timeout_add(250, self._apply_default_aspect)
        except Exception as e:
            self._message('STARTFEHLER', str(e), self.return_mode)

    def _apply_default_aspect(self):
        if not self.player: return False
        aspect = self.settings.get('default_aspect', 'Auto')
        try:
            self.player.video_set_aspect_ratio(None if aspect == 'Auto' else aspect)
        except Exception: pass
        return False

    def _toggle_pause(self):
        if self.shuttle_direction:
            self._stop_shuttle_and_play()
            return
        if self.player:
            try: self.player.pause()
            except Exception: pass

    def _seek(self, delta):
        if not self.player: return
        try:
            now = self.player.get_time()
            if now >= 0: self.player.set_time(max(0, now + int(delta * 1000)))
        except Exception: pass

    def _update_shuttle_label(self):
        if not getattr(self, 'shuttle_label', None):
            return
        if not self.shuttle_direction:
            self.shuttle_label.hide()
            return
        speed = self.shuttle_speeds[self.shuttle_level]
        arrows = '>>' if self.shuttle_direction > 0 else '<<'
        self.shuttle_label.set_text(f'{arrows}  x{speed}')
        self.shuttle_label.show()

    def _reset_shuttle_state(self, resume=True):
        was_active = bool(self.shuttle_direction)
        was_native = bool(getattr(self, 'shuttle_native_rate', False))
        self.shuttle_direction = 0
        self.shuttle_level = 0
        self.shuttle_last_tick = 0.0
        self.shuttle_native_rate = False
        if getattr(self, 'shuttle_label', None):
            self.shuttle_label.hide()
        if self.player:
            # Always restore x1 after optical native-rate fast forward.
            if was_native:
                try:
                    self.player.set_rate(1.0)
                except Exception:
                    pass
            if resume and was_active:
                try:
                    self.player.play()
                except Exception:
                    pass

    def _start_shuttle(self, direction):
        if not self.player or self.mode != 'player':
            return
        direction = 1 if direction > 0 else -1

        old_native = bool(getattr(self, 'shuttle_native_rate', False))
        old_direction = self.shuttle_direction
        if old_direction == direction:
            self.shuttle_level = min(self.shuttle_level + 1, len(self.shuttle_speeds) - 1)
        else:
            self.shuttle_direction = direction
            self.shuttle_level = 0

        speed = self.shuttle_speeds[self.shuttle_level]
        self.shuttle_last_tick = time.monotonic()
        optical_forward = self.optical_source_kind in ('dvd', 'bluray') and direction > 0

        # If we are leaving a previous native-rate forward run (for example >>
        # followed by <<), first put libVLC back to normal speed.
        if old_native and not optical_forward:
            try:
                self.player.set_rate(1.0)
            except Exception:
                pass

        self.shuttle_native_rate = False
        if optical_forward:
            # Let the DVD/Blu-ray input advance naturally.  This is important:
            # set_time() is title-relative on optical media and repeatedly seeking
            # toward a DVD title/cell boundary can make the DVD VM jump back to a
            # menu/title start.  Native positive playback rate keeps the disc
            # navigator in control and can cross normal chapter/cell transitions.
            try:
                self.player.play()
                result = self.player.set_rate(float(speed))
                if result == 0:
                    self.shuttle_native_rate = True
                    print(f'Optical native shuttle rate accepted: x{speed}', flush=True)
                else:
                    print(f'Optical native shuttle rate rejected ({result}); timed fallback.', flush=True)
            except Exception as e:
                print(f'Optical native shuttle rate failed: {e}; timed fallback.', flush=True)

        if not self.shuttle_native_rate:
            # Normal files and optical reverse: pause normal playback while we
            # advance/rewind the timeline ourselves.
            try:
                self.player.set_rate(1.0)
            except Exception:
                pass
            try:
                self.player.set_pause(1)
            except Exception:
                try:
                    self.player.pause()
                except Exception:
                    pass

        self.controls_visible = False
        self.controls.hide(); self.player_top.hide(); self.menu_panel.hide()
        self.player_menu_kind = None
        self._update_shuttle_label()
        print(
            f'Shield VLC shuttle gestartet: '
            f'{">>" if self.shuttle_direction > 0 else "<<"} '
            f'x{speed} mode={"native-rate" if self.shuttle_native_rate else "timed-seek"}',
            flush=True,
        )

    def _stop_shuttle_and_play(self):
        if self.shuttle_direction:
            self._reset_shuttle_state(resume=True)

    def _shuttle_tick(self):
        if not self.shuttle_direction or self.mode != 'player' or not self.player:
            return True

        # DVD/Blu-ray forward shuttle is already moving at the requested libVLC
        # playback rate.  Do NOT call set_time() here; that was the DVD barrier
        # bug.
        if getattr(self, 'shuttle_native_rate', False):
            return True

        now_clock = time.monotonic()
        if not self.shuttle_last_tick:
            self.shuttle_last_tick = now_clock
            return True
        elapsed = max(0.0, min(0.5, now_clock - self.shuttle_last_tick))
        self.shuttle_last_tick = now_clock
        speed = self.shuttle_speeds[self.shuttle_level]
        try:
            pos = self.player.get_time()
            length = self.player.get_length()
            if pos < 0:
                return True
            delta_ms = int(self.shuttle_direction * speed * elapsed * 1000.0)
            target = max(0, pos + delta_ms)
            if length and length > 0:
                target = min(max(0, length - 250), target)
            self.player.set_time(int(target))
            if target <= 0 and self.shuttle_direction < 0:
                self._stop_shuttle_and_play()
            elif length and length > 0 and target >= max(0, length - 250) and self.shuttle_direction > 0:
                self._stop_shuttle_and_play()
        except Exception:
            pass
        return True

    def _volume(self, delta):
        if not self.player: return
        try:
            v = self.player.audio_get_volume()
            if v < 0: v = 80
            self.player.audio_set_volume(max(0, min(125, v + delta)))
        except Exception: pass

    def _show_controls(self):
        self.controls_visible = True
        self.player_top.show(); self.controls.show(); self.menu_panel.hide(); self.player_menu_kind = None
        self._focus_control()

    def _hide_controls(self):
        self.controls_visible = False; self.controls.hide(); self.player_top.hide(); self.menu_panel.hide(); self.player_menu_kind = None
        try: self.video_area.grab_focus()
        except Exception: pass

    def _focus_control(self):
        self.player_control_index = max(0, min(self.player_control_index, len(self.control_buttons)-1))
        GLib.idle_add(self.control_buttons[self.player_control_index].grab_focus)

    def _activate_control(self):
        # No seek entries here: D-pad + OK can never seek the movie.
        # Seeking belongs exclusively to the physical << / >> buttons.
        i = self.player_control_index
        if i == 0: self._toggle_pause()
        elif i == 1: self._open_track_menu('audio')
        elif i == 2: self._open_track_menu('subtitle')
        elif i == 3: self._open_aspect_menu()
        elif i == 4: self._open_info_menu()
        elif i == 5: self._stop_and_return()

    def _desc_list(self, value):
        out = []
        for d in value or []:
            try:
                if isinstance(d, tuple) and len(d) >= 2:
                    ident, name = d[0], d[1]
                else:
                    ident, name = getattr(d, 'id'), getattr(d, 'name')
                out.append((int(ident), text_of(name)))
            except Exception:
                pass
        return out

    def _open_track_menu(self, kind):
        if not self.player: return
        if kind == 'audio':
            try: items = self._desc_list(self.player.audio_get_track_description())
            except Exception: items = []
            self._show_player_menu('AUDIOSPUR', [(name or f'Spur {i}', i) for i, name in items], 'audio')
        else:
            try: items = self._desc_list(self.player.video_get_spu_description())
            except Exception: items = []
            normalized = []
            if not any(i == -1 for i, _ in items): normalized.append(('Aus', -1))
            normalized.extend([(name or f'Untertitel {i}', i) for i, name in items])
            self._show_player_menu('UNTERTITEL', normalized, 'subtitle')

    def _open_aspect_menu(self):
        self._show_player_menu('BILDFORMAT', [('Auto', None), ('4:3', '4:3'), ('16:9', '16:9'), ('Original', 'original')], 'aspect')

    def _open_info_menu(self):
        length = self.player.get_length() if self.player else -1
        text = f'{self.current_title}\nDauer: {fmt_time(length)}\n\nZurück = schließen'
        self._show_player_menu('INFO', [(text, 'close')], 'info')

    def _show_player_menu(self, title, items, kind):
        self.player_menu_items = items or [('Keine Einträge', None)]
        self.player_menu_index = 0; self.player_menu_kind = kind
        self.menu_title.set_text(title)
        for c in self.menu_items_box.get_children(): self.menu_items_box.remove(c)
        self.menu_buttons = []
        for name, _value in self.player_menu_items:
            b = Gtk.Button(label=name); b.set_name('menu-row'); b.set_size_request(390, 48)
            self.menu_items_box.pack_start(b, False, False, 0); self.menu_buttons.append(b)
        self.menu_panel.show_all(); self.controls.show(); self.player_top.show(); self.controls_visible = True
        self._focus_player_menu()

    def _focus_player_menu(self):
        if self.menu_buttons:
            self.player_menu_index = max(0, min(self.player_menu_index, len(self.menu_buttons)-1))
            GLib.idle_add(self.menu_buttons[self.player_menu_index].grab_focus)

    def _activate_player_menu(self):
        if not self.player_menu_items: return
        _name, val = self.player_menu_items[self.player_menu_index]
        try:
            if self.player_menu_kind == 'audio' and val is not None:
                self.player.audio_set_track(int(val))
            elif self.player_menu_kind == 'subtitle' and val is not None:
                self.player.video_set_spu(int(val))
            elif self.player_menu_kind == 'aspect':
                self.player.video_set_aspect_ratio(None if val in (None, 'original') else str(val))
        except Exception: pass
        self.player_menu_kind = None; self.menu_panel.hide(); self._focus_control()

    def _stop_and_return(self):
        self._reset_shuttle_state(resume=False)
        try:
            if self.player: self.player.stop()
        except Exception: pass
        self.controls_visible = False; self.controls.hide(); self.player_top.hide(); self.menu_panel.hide(); self.player_menu_kind = None
        self.optical_source_device = None; self.optical_source_kind = None
        if self.return_mode == 'browser':
            self.mode = 'browser'; self.stack.set_visible_child_name('browser'); self._focus_browser()
        elif self.return_mode == 'recent':
            self._show_recent()
        elif self.return_mode == 'external':
            self._show_external_media()
        else:
            self._show_home()

    def _update_player_status(self):
        if self.mode == 'player' and self.player:
            try:
                now = self.player.get_time(); length = self.player.get_length()
                self.player_time.set_text(f'{fmt_time(now)} / {fmt_time(length)}')
                self.progress.set_fraction(max(0.0, min(1.0, now / length))) if length and length > 0 and now >= 0 else self.progress.set_fraction(0.0)
            except Exception: pass
        return True

    def _vlc_end(self, event):
        GLib.idle_add(self._stop_and_return)

    def _vlc_error(self, event):
        GLib.idle_add(self._message, 'WIEDERGABEFEHLER', 'Das Medium konnte nicht abgespielt werden.', self.return_mode)

    # ---------------- messages ----------------
    def _message(self, title, text, return_mode='home'):
        self.message_title.set_text(title); self.message_text.set_text(text)
        self.message_return_mode = return_mode
        self.mode = 'message'; self.stack.set_visible_child_name('message')
        return False

    def _return_from_message(self):
        target = getattr(self, 'message_return_mode', 'home')
        if target == 'browser':
            self.mode = 'browser'; self.stack.set_visible_child_name('browser'); self._focus_browser()
        elif target == 'external':
            self._show_external_media()
        else:
            self._show_home()

    # ---------------- direct Shield-Remote IPC ----------------
    def _start_control_socket(self):
        try:
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            try:
                CONTROL_SOCKET.unlink()
            except FileNotFoundError:
                pass
            self.control_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.control_socket.setblocking(False)
            self.control_socket.bind(str(CONTROL_SOCKET))
            self.control_watch_id = GLib.io_add_watch(
                self.control_socket.fileno(),
                GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR,
                self._on_control_socket,
            )
            print(f'Shield VLC control socket bereit: {CONTROL_SOCKET}', flush=True)
        except Exception as e:
            print(f'Shield VLC control socket Fehler: {e}', flush=True)
            self.control_socket = None
            self.control_watch_id = 0

    def _on_control_socket(self, source, condition):
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            return True
        if self.control_socket is None:
            return False
        try:
            while True:
                raw = self.control_socket.recv(256)
                if not raw:
                    break
                command = raw.decode('utf-8', 'replace').strip().lower()
                if command:
                    self._handle_remote_command(command)
        except BlockingIOError:
            pass
        except Exception as e:
            print(f'Shield VLC control read Fehler: {e}', flush=True)
        return True

    def _handle_remote_command(self, command):
        # Transport keys use direct stateful commands; navigation reuses the
        # keyboard state machine below.
        if command in ('rewind', 'fastforward', 'seek_back', 'seek_forward'):
            print(
                f'Shield VLC transport command={command} mode={self.mode} '
                f'direction={self.shuttle_direction} level={self.shuttle_level}',
                flush=True,
            )
        if command in ('rewind', 'seek_back'):
            self._start_shuttle(-1)
            return
        if command in ('fastforward', 'seek_forward'):
            self._start_shuttle(+1)
            return
        if command == 'select' and self.mode == 'player' and self.shuttle_direction:
            self._stop_shuttle_and_play()
            return
        if command == 'playpause' and self.mode == 'player' and self.shuttle_direction:
            self._stop_shuttle_and_play()
            return
        if self.mode == 'player' and self.shuttle_direction and command in ('up', 'down', 'left', 'right'):
            # While shuttle seek is active, D-pad navigation must not change the
            # transport state or accidentally reveal/move the player controls.
            # OK or Play/Pause is the deliberate way back to normal x1 playback.
            return

        # Reuse the exact same state machine as physical keyboard navigation,
        # but without relying on uinput -> wlroots -> XWayland key delivery.
        names = {
            'up': 'Up',
            'down': 'Down',
            'left': 'Left',
            'right': 'Right',
            'select': 'Return',
            'back': 'BackSpace',
            'menu': 'F6',
            'playpause': 'space',
        }
        keyname = names.get(command)
        if not keyname:
            return
        keyval = Gdk.keyval_from_name(keyname)
        if not keyval:
            return

        class RemoteEvent:
            pass

        event = RemoteEvent()
        event.keyval = keyval
        self._on_key(self, event)

    # ---------------- keyboard / remote ----------------
    def _on_key(self, widget, event):
        key = Gdk.keyval_name(event.keyval) or ''

        if self.mode == 'home':
            row, col = divmod(self.home_index, 3)
            if key == 'Left': col = max(0, col-1)
            elif key == 'Right': col = min(2, col+1)
            elif key == 'Up': row = max(0, row-1)
            elif key == 'Down': row = min(1, row+1)
            elif key in ('Return','KP_Enter'): self._activate_home(); return True
            elif key in ('BackSpace','Escape'): return True
            else: return False
            self.home_index = min(len(self.home_buttons)-1, row*3+col); self.home_buttons[self.home_index].grab_focus(); return True

        if self.mode == 'browser':
            if key == 'Up' and self.browser_items: self.browser_index = max(0, self.browser_index-1); self._focus_browser()
            elif key == 'Down' and self.browser_items: self.browser_index = min(len(self.browser_items)-1, self.browser_index+1); self._focus_browser()
            elif key in ('Return','KP_Enter'): self._browser_activate()
            elif key in ('BackSpace','Escape','Left'): self._browser_back()
            return True

        if self.mode == 'external':
            if key == 'Up' and self.external_items:
                self.external_index = max(0, self.external_index-1); self._focus_external()
            elif key == 'Down' and self.external_items:
                self.external_index = min(len(self.external_items)-1, self.external_index+1); self._focus_external()
            elif key in ('Return','KP_Enter'):
                self._activate_external()
            elif key in ('BackSpace','Escape','Left'):
                self._show_home()
            return True

        if self.mode == 'recent':
            if key == 'Up' and self.recent_items: self.recent_index = max(0, self.recent_index-1); self._focus_recent()
            elif key == 'Down' and self.recent_items: self.recent_index = min(len(self.recent_items)-1, self.recent_index+1); self._focus_recent()
            elif key in ('Return','KP_Enter') and self.recent_items: self.return_mode='recent'; self._play(self.recent_items[self.recent_index])
            elif key in ('BackSpace','Escape','Left'): self._show_home()
            return True

        if self.mode == 'network':
            if key in ('Return','KP_Enter'):
                src = self.network_entry.get_text().strip()
                if src: self.return_mode='home'; self._play(src)
                return True
            if key in ('BackSpace','Escape') and not self.network_entry.get_text(): self._show_home(); return True
            return False

        if self.mode == 'settings':
            if key == 'Up': self.settings_index = max(0, self.settings_index-1); self._focus_settings()
            elif key == 'Down': self.settings_index = min(len(self.setting_buttons)-1, self.settings_index+1); self._focus_settings()
            elif key in ('Return','KP_Enter'): self._activate_setting()
            elif key in ('BackSpace','Escape','Left'): self._show_home()
            return True

        if self.mode == 'message':
            if key in ('Return','KP_Enter','BackSpace','Escape'): self._return_from_message(); return True
            return True

        if self.mode == 'player':
            # Netflix key is remapped to F6 by shield-remote.
            if key == 'F6':
                if self.player_menu_kind:
                    self.player_menu_kind = None; self.menu_panel.hide(); self._focus_control()
                elif self.controls_visible: self._hide_controls()
                else: self._show_controls()
                return True
            if key == 'space': key = 'Space'
            if key == 'Space': self._toggle_pause(); return True

            if self.player_menu_kind:
                if key == 'Up': self.player_menu_index = max(0, self.player_menu_index-1); self._focus_player_menu()
                elif key == 'Down': self.player_menu_index = min(len(self.player_menu_items)-1, self.player_menu_index+1); self._focus_player_menu()
                elif key in ('Return','KP_Enter'): self._activate_player_menu()
                elif key in ('BackSpace','Escape','Left'): self.player_menu_kind=None; self.menu_panel.hide(); self._focus_control()
                return True

            if self.controls_visible:
                if key == 'Left': self.player_control_index = max(0, self.player_control_index-1); self._focus_control()
                elif key == 'Right': self.player_control_index = min(len(self.control_buttons)-1, self.player_control_index+1); self._focus_control()
                elif key == 'Down': self._hide_controls()
                elif key in ('Return','KP_Enter'): self._activate_control()
                elif key in ('BackSpace','Escape'): self._hide_controls()
                return True

            # Optical DVD/Blu-ray menus are real libVLC navigation menus.
            # While an optical disc is active, arrows/OK go directly to libVLC's
            # menu navigator. Netflix still opens the Shield player bar, so seek,
            # audio/subtitles and Stop stay available at any time.
            if self.optical_source_kind in ('dvd', 'bluray') and self.player:
                nav = {'Return': 0, 'KP_Enter': 0, 'Up': 1, 'Down': 2, 'Left': 3, 'Right': 4}
                if key in nav:
                    try: self.player.navigate(nav[key])
                    except Exception as e: print('Disc navigation error:', e, flush=True)
                    return True
                if key in ('BackSpace','Escape'):
                    self._stop_and_return(); return True

            # Normal video: transport is EXCLUSIVELY on the physical << / >>
            # buttons.  D-pad can only expose/navigate the Shield control bar.
            # First D-pad press while hidden merely reveals the bar at
            # Play/Pause; it never changes playback time.
            if key in ('Return','KP_Enter'):
                self.player_control_index = 0
                self._show_controls()
            elif key in ('Left','Right','Up','Down'):
                self.player_control_index = 0
                self._show_controls()
            elif key in ('BackSpace','Escape'):
                self._stop_and_return()
            return True

        return False

    def _on_destroy(self, *args):
        self._reset_shuttle_state(resume=False)
        try:
            if self.player: self.player.stop()
        except Exception: pass
        if self.control_watch_id:
            try: GLib.source_remove(self.control_watch_id)
            except Exception: pass
            self.control_watch_id = 0
        if self.control_socket is not None:
            try: self.control_socket.close()
            except Exception: pass
            self.control_socket = None
        try: CONTROL_SOCKET.unlink()
        except FileNotFoundError: pass
        except Exception: pass
        Gtk.main_quit()


if __name__ == '__main__':
    app = ShieldVlcTV()
    Gtk.main()
