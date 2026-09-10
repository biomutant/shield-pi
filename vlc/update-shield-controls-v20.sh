#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
USER_HOME="${SHIELD_HOME:-$HOME}"
VLC_TARGET="$USER_HOME/shield-vlc.py"
VLC_BACKUP_DIR="$USER_HOME/.config/shield-vlc/backups"

echo "[1/5] Aktuelle Shield-VLC-Datei sichern"
mkdir -p "$VLC_BACKUP_DIR"
[ ! -f "$VLC_TARGET" ] || cp -a "$VLC_TARGET" "$VLC_BACKUP_DIR/shield-vlc.py.$STAMP"

echo "[2/5] Python pruefen"
/usr/bin/python3 -m py_compile "$HERE/shield-vlc.py"

echo "[3/5] Shield VLC v20 installieren"
install -m 0755 "$HERE/shield-vlc.py" "$VLC_TARGET"

echo "[4/5] Laufendes Shield VLC beenden"
pkill -f "$VLC_TARGET" 2>/dev/null || true
sleep 1

echo "[5/5] Fertig"
echo
echo "V20 installiert."
echo "DVD/Blu-ray VORWAERTS-Spulen nutzt jetzt native positive libVLC-Rate statt wiederholtem set_time()."
echo "Damit soll die DVD-Navigation Kapitel/Zellen selbst ueberqueren, ohne an der bisherigen Barriere zum Anfang zu springen."
echo "MP4/USB-Shuttle bleibt unveraendert; optisches Rueckwaertsspulen bleibt timed-seek."
echo "Kodi, FreeTube, Launcher, Remote-Daemon, Home und Taskmanager wurden NICHT veraendert."
echo
echo "Shield VLC neu ueber die VLC-Kachel starten."
