#!/bin/bash
set -euo pipefail

USER_NAME="${SHIELD_USER:-${SUDO_USER:-$(id -un)}}"
if [ "$USER_NAME" = "root" ]; then
  echo "FEHLER: Zielbenutzer ist root. Als normaler Benutzer starten oder SHIELD_USER setzen." >&2
  exit 1
fi
HOME_DIR="${SHIELD_HOME:-$(getent passwd "$USER_NAME" | cut -d: -f6)}"
if [ -z "$HOME_DIR" ]; then
  echo "FEHLER: Home-Verzeichnis fuer $USER_NAME konnte nicht ermittelt werden." >&2
  exit 1
fi
USER_ID="$(id -u "$USER_NAME")"
USER_GROUP="$(id -gn "$USER_NAME")"
TARGET="${HOME_DIR}/shield-remote"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

echo "[1/7] Abhaengigkeiten sicherstellen"
$SUDO apt-get update
$SUDO apt-get install -y python3-evdev python3-websocket wlrctl

echo "[2/7] Alten input-remapper weiterhin deaktiviert halten"
$SUDO systemctl disable --now input-remapper 2>/dev/null || true
$SUDO systemctl disable --now input-remapper-daemon.service 2>/dev/null || true
if command -v input-remapper-control >/dev/null 2>&1; then
  input-remapper-control --command quit >/dev/null 2>&1 || true
fi

echo "[3/7] input/uinput Rechte sicherstellen"
$SUDO usermod -aG input "$USER_NAME"
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | $SUDO tee /etc/udev/rules.d/99-shield-uinput.rules >/dev/null
$SUDO modprobe uinput || true
$SUDO udevadm control --reload-rules
$SUDO udevadm trigger --name-match=uinput 2>/dev/null || true

echo "[4/7] Aktuelle Shield-Remote-Dateien wiederherstellen"
$SUDO mkdir -p "$TARGET"
$SUDO install -m 0755 "$SCRIPT_DIR/shield-remote.py" "$TARGET/shield-remote.py"
$SUDO install -m 0644 "$SCRIPT_DIR/profiles.json" "$TARGET/profiles.json"
$SUDO chown -R "$USER_NAME:$USER_NAME" "$TARGET"

echo "[5/7] Python/JSON pruefen"
/usr/bin/python3 -m py_compile "$TARGET/shield-remote.py"
/usr/bin/python3 -m json.tool "$TARGET/profiles.json" >/dev/null

echo "[6/7] systemd-Dienst wiederherstellen"
SERVICE_TMP="$(mktemp)"
trap 'rm -f "$SERVICE_TMP"' EXIT
python3 - "$SCRIPT_DIR/shield-remote.service" "$SERVICE_TMP" "$USER_NAME" "$USER_GROUP" "$USER_ID" "$HOME_DIR" <<'PY'
from pathlib import Path
import sys

template, destination, user, group, uid, home = sys.argv[1:]
text = Path(template).read_text(encoding="utf-8")
for marker, value in {
    "@USER@": user,
    "@GROUP@": group,
    "@UID@": uid,
    "@HOME@": home,
}.items():
    text = text.replace(marker, value)
Path(destination).write_text(text, encoding="utf-8")
PY
$SUDO install -m 0644 "$SERVICE_TMP" /etc/systemd/system/shield-remote.service
$SUDO systemctl daemon-reload
$SUDO systemctl enable shield-remote.service
$SUDO systemctl restart shield-remote.service
sleep 2

echo "[7/7] Status"
$SUDO systemctl --no-pager --full status shield-remote.service | sed -n '1,18p' || true

echo
echo "Wiederherstellung abgeschlossen."
echo "Launcher, Hintergrund, FreeTube und VLC-Dateien wurden NICHT veraendert."
echo "Wenn der Dienst nicht active (running) ist:"
echo "  journalctl -u shield-remote -n 80 --no-pager"
echo
echo "Falls die Fernbedienung trotz active (running) noch nicht reagiert, einmal neu starten:"
echo "  sudo reboot"
