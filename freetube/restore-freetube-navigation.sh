#!/bin/bash
set -euo pipefail

USER_HOME="${SHIELD_HOME:-$HOME}"
LAUNCHER="$USER_HOME/shield-launcher-test.py"
BACKUP_DIR="$USER_HOME/.config/shield-launcher/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$LAUNCHER" ]; then
  echo "FEHLER: $LAUNCHER wurde nicht gefunden."
  exit 1
fi

mkdir -p "$BACKUP_DIR"
cp -a "$LAUNCHER" "$BACKUP_DIR/shield-launcher-test.py.$STAMP.before-freetube-nav-restore"

echo "[1/4] FreeTube-Steuerkanal in der YouTube-Kachel wiederherstellen"
python3 - "$LAUNCHER" <<'PY'
from pathlib import Path
import re, sys

path = Path(sys.argv[1])
text = path.read_text(encoding='utf-8')

# Change only the command of the launcher entry whose class is "freetube".
# The visible name (YouTube), artwork and all CRT design code remain untouched.
pattern = re.compile(
    r'("name"\s*:\s*"(?:YouTube|FreeTube)"\s*,.*?"command"\s*:\s*)'
    r'\[[^\]]*\]'
    r'(\s*,\s*"class"\s*:\s*"freetube")',
    re.S,
)

command = '''[
            "/usr/bin/freetube",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=9222",
            "--remote-allow-origins=*"
        ]'''

new_text, count = pattern.subn(r'\1' + command + r'\2', text, count=1)
if count != 1:
    raise SystemExit('FEHLER: FreeTube/YouTube-Eintrag im Launcher nicht eindeutig gefunden.')

path.write_text(new_text, encoding='utf-8')
PY

echo "[2/4] Launcher-Syntax pruefen"
python3 -m py_compile "$LAUNCHER"

echo "[3/4] FreeTube beenden, damit es beim naechsten Start Port 9222 verwendet"
pkill -f '/usr/bin/freetube' 2>/dev/null || true
pkill -x freetube 2>/dev/null || true
sleep 1

echo "[4/4] Kontrolle"
grep -n -A11 -B2 '"name": "YouTube"' "$LAUNCHER" | sed -n '1,18p'

echo
echo "Fertig. Das CRT-Design und Shield VLC wurden NICHT veraendert."
echo "Jetzt den Pi einmal neu starten: sudo reboot"
