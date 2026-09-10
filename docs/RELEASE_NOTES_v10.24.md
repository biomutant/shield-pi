# Shield Pi v10.24 — First Public Release

Shield Pi v10.24 is the first public open-source snapshot of the Raspberry Pi 4 TV/media interface developed for remote-only use on a real 13-inch 720×576 4:3 CRT.

## Highlights

- CRT-optimized GTK3 launcher with built-in VLC, FreeTube, Kodi and NordVPN entries
- **Add application** flow for installed graphical applications, including Firefox and Chromium when available
- persistent per-application labwc workspaces
- activation of existing application windows to avoid duplicate launches
- recent-application task manager with a four-card carousel, active-state indicators and optional thumbnails
- single Home → launcher; rapid double Home → task manager
- application-aware NVIDIA Shield Remote profiles
- native Kodi TV-navigation passthrough
- Firefox/Chromium focus traversal, browser Back and address-bar/on-screen-keyboard integration
- dedicated FreeTube remote-debugging navigation
- Shield VLC TV frontend with media, DVD and shuttle controls
- Shield NordVPN v10.24 TV interface with the confirmed 164×102 country/city/server card geometry

## Task manager controls

- Left/Right — select a recent application
- OK — open or activate
- Down — enter close mode
- Up — cancel close mode
- OK in close mode — close the application and remove it from the recent list
- Back/Home — return to the launcher

## Security and privacy

- No NordVPN account credentials, login tokens or authenticated session data are included.
- Each installation requires its own locally installed and authenticated NordVPN CLI.
- Personal CRT/home photographs, runtime network details and local launcher state are excluded.
- Runtime paths are user-independent and resolve from the installing user's home directory where supported.

## Target environment

- Raspberry Pi 4
- Raspberry Pi OS / Debian Trixie
- labwc / Wayland
- Python / GTK3
- NVIDIA Shield Remote through evdev
- 720×576, 4:3 CRT target

## Important notes

This is an experimental community release originating from one physical target setup. Hardware, package and window-class differences may require local adjustment. Application discovery depends on valid `.desktop` files, and task activation depends on the included Wayland helper being installed at the expected location.

Shield Pi is an independent community project and is not affiliated with, endorsed by, sponsored by or supported by NVIDIA or NordVPN. Third-party product names are used only to describe interoperability.

For navigation details, see [Launcher, application navigation and task manager](LAUNCHER_NAVIGATION.md). For installation material and subsystem scripts, use the corresponding repository directories.
