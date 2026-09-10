# COMPONENTS AND PROTECTED AREAS

This document identifies the current source locations and the behavior that should not be changed accidentally while working on another subsystem.

## NordVPN

Repository source:
`nordvpn/`

Primary Pi target in the current prototype:
`$HOME/nordvpn-app.py`

Status:
**v10.24 is the canonical confirmed milestone.**

Protected unless explicitly targeted:

- Home layout/behavior
- first System page
- VPN/DNS/Status second-level pages
- established 164×102 country/city/server card geometry
- short/long OK semantics

## Launcher

Repository source:
`launcher/shield-launcher-test.py`

Current Pi target:
`$HOME/shield-launcher-test.py`

Status:
working and protected unless the launcher itself is the requested scope.

Protected behavior:

- built-in VLC, FreeTube, Kodi and NordVPN entries
- graphical `.desktop` discovery through **Add application**
- removing a user-added tile without uninstalling the operating-system application
- persistent per-application labwc workspaces
- activation of an existing window instead of launching duplicate instances
- recent-task state and thumbnail handling
- single Home → Launcher
- rapid double Home → Task manager
- remote-only operation without requiring a mouse

See `LAUNCHER_NAVIGATION.md` for the complete behavior.

## Shield Remote

Repository source:
`remote/`

Current Pi targets:

- `$HOME/shield-remote/shield-remote.py`
- `$HOME/shield-remote/profiles.json`
- `/etc/systemd/system/shield-remote.service`

Status:
working. Avoid changes unless remote behavior itself is shown to be the root cause.

Protected behavior:

- single Home → Launcher
- rapid double Home → Task manager
- Kodi physical-key passthrough for native Kodi TV navigation, including short-OK selection and the long-OK context menu
- Firefox/Chromium focus traversal, browser Back behavior and Search-to-address-bar OSK flow
- established FreeTube/VLC mappings
- application-profile selection from the active window

## Shield VLC

Repository source:
`vlc/`

Current Pi target:
`$HOME/shield-vlc.py`

Status:
working dedicated seek/DVD behavior; protected unless VLC is explicitly targeted.

## FreeTube navigation

Repository source:
`freetube/`

Purpose:
restores/preserves the FreeTube Chromium remote-debugging navigation path without redesigning unrelated launcher behavior.

## Releases and rollback points

Installable ZIP archives are intended to live in GitHub Releases rather than being duplicated in source history. See `../milestones/README.md` for the milestone policy.

The historical v10.18 NordVPN milestone remains an important conceptual rollback reference, while v10.24 is the current preferred baseline.

## Scope rule

When a task says “only X”, only X should change. A stable component is treated as an asset, not as an invitation to refactor adjacent code.
