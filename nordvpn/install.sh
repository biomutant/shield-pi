#!/bin/bash
set -e
USER_HOME="${SHIELD_HOME:-$HOME}"
APP="$USER_HOME/nordvpn-app.py"
LAUNCHER="$USER_HOME/shield-launcher-test.py"
DATA_DIR="$USER_HOME/.local/share/shield-nordvpn"
CACHE_DIR="$USER_HOME/.cache/shield-nordvpn/flags"
STAMP="$(date +%Y%m%d-%H%M%S)"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "===== SHIELD NORDVPN V10.24 SHIELD SERVER GRID ====="
mkdir -p "$DATA_DIR" "$CACHE_DIR"

if [ -f "$APP" ]; then
  cp "$APP" "$APP.backup-v10.24-$STAMP"
  echo "Backup App: $APP.backup-v10.24-$STAMP"
fi

cp "$HERE/nordvpn-app.py" "$APP"
cp "$HERE/hero-world.png" "$DATA_DIR/hero-world.png"
cp "$HERE/system-shield.png" "$DATA_DIR/system-shield.png"
cp "$HERE/shield-band.png" "$DATA_DIR/shield-band.png"
cp "$HERE/footer-shield.png" "$DATA_DIR/footer-shield.png"
mkdir -p "$DATA_DIR/cityflags"
cp -f "$HERE/cityflags/"*.png "$DATA_DIR/cityflags/" 2>/dev/null || true
cp "$HERE/system-page-bg.png" "$DATA_DIR/system-page-bg.png"
cp "$HERE/vpn-page-bg.png" "$DATA_DIR/vpn-page-bg.png"
cp "$HERE/dns-page-bg.png" "$DATA_DIR/dns-page-bg.png"
cp "$HERE/status-page-bg.png" "$DATA_DIR/status-page-bg.png"
cp "$HERE/country-grid-bg.png" "$DATA_DIR/country-grid-bg.png"
cp "$HERE/country-preview-bg.png" "$DATA_DIR/country-preview-bg.png"
chmod +x "$APP"
python3 -m py_compile "$APP"
echo "App: Syntax OK"

if [ -f "$LAUNCHER" ]; then
  cp "$LAUNCHER" "$LAUNCHER.backup-nordvpn-v10.24-$STAMP"
  python3 - "$LAUNCHER" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); lines=p.read_text().splitlines(True)
idx=next((i for i,l in enumerate(lines) if '"name": "NordVPN"' in l),None)
if idx is not None:
    start=idx
    while start>=0 and '{' not in lines[start]: start-=1
    depth=0; end=None
    for i in range(start,len(lines)):
        depth += lines[i].count('{')-lines[i].count('}')
        if depth==0 and i>start: end=i; break
    if start>=0 and end is not None:
        indent=lines[start][:len(lines[start])-len(lines[start].lstrip())]
        block=f'''{indent}{{\n{indent}    "name": "NordVPN",\n{indent}    "subtitle": "",\n{indent}    "command": [\n{indent}        "/usr/bin/env",\n{indent}        "GDK_SCALE=1",\n{indent}        "GDK_DPI_SCALE=1.0",\n{indent}        "/usr/bin/python3",\n{indent}        os.path.expanduser("~/nordvpn-app.py")\n{indent}    ],\n{indent}    "class": "shield-nordvpn",\n{indent}    "match": ["shield-nordvpn", "Shield NordVPN", "nordvpn-app.py"],\n{indent}    "icon_file": os.path.expanduser(\n{indent}        "~/.local/share/icons/NordVPN.png"\n{indent}    ),\n{indent}    "icon": "nordvpn"\n{indent}}},\n'''
        lines[start:end+1]=[block]
        p.write_text(''.join(lines))
        print('Launcher: NordVPN-Kachel auf Shield NordVPN V10.24 gesetzt.')
PY
fi

nordvpn set tray off >/dev/null 2>&1 || true

echo
echo "Installation fertig."
echo "Direkter Test:"
echo "GDK_SCALE=1 GDK_DPI_SCALE=1.0 /usr/bin/python3 $APP"
