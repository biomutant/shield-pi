Shield FreeTube Navigation Restore

Dieses Update repariert ausschliesslich den Startbefehl der sichtbaren YouTube-Kachel.
Es stellt den lokalen FreeTube-Steuerkanal fuer die vorhandene Shield-Remote-Navigation wieder her:
  --remote-debugging-address=127.0.0.1
  --remote-debugging-port=9222
  --remote-allow-origins=*

Nicht veraendert werden:
- CRT-Launcher-Design
- sichtbarer Name "YouTube"
- YouTube-Logo
- Shield VLC TV
- Shield-Remote-Daemon
- Home/Taskmanager-Logik

Nach der Installation ist ein Neustart erforderlich, weil der laufende Launcher seinen App-Startbefehl bereits im Speicher hat.
