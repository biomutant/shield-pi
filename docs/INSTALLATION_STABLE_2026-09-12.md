# Installation – öffentliche Vorlage

## Systempakete

Der Stable-Stand verwendet unter anderem:

- Python 3, PyGObject/GTK 3 und PyCairo
- VLC mit Python-Bindings
- mpv
- NumPy
- PulseAudio-Werkzeuge
- projectM PulseAudio und projectM-Daten
- X11-Werkzeuge, ydotool und grim

Die genauen Paketnamen richten sich nach Raspberry Pi OS / Debian Trixie.

## Beispielpfade

Die Laufzeitquellen ermitteln das Benutzerverzeichnis über `$HOME` oder
optional `SHIELD_HOME`. Dokumentierte Beispiele verwenden:

- Benutzerkonto `/home/shield`
- NAS-Mount `/mnt/shield-nas`

Vor der Installation müssen diese Pfade an das Zielsystem angepasst werden.
Zugangsdaten dürfen nicht direkt in Quellcode, Dienste oder Skripte geschrieben
werden.

## projectM

Die Datei `system/projectM/config.inp` nutzt die klassische
MilkDrop-Sammlung unter `/usr/share/projectM/presets/presets_milkdrop`.
Shield VLC bettet projectM als rahmenloses X11-Kindfenster ein.

## Konfigurationen

Die Dateien unter `system` sind geprüfte Beispiele des
Stable-Systems. Vor einer Übernahme immer gegen die vorhandene Zielkonfiguration
vergleichen; bestehende Desktop- oder labwc-Einstellungen nicht blind ersetzen.
Vorlagen mit `@USER@`, `@GROUP@`, `@HOME@` und `@UID@` müssen vor der
Installation mit den Werten des Zielkontos ersetzt werden.
