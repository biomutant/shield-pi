# Shield Pi

Shield Pi is an experimental Raspberry Pi 5 project for a **fully remote-controlled TV/media interface designed around a real 13-inch 720×576 4:3 CRT**.

The project combines a custom GTK3 launcher, application-aware NVIDIA Shield Remote input, dynamic management of installed applications, persistent labwc workspaces, a recent-application task manager, a Shield-style VLC frontend, FreeTube navigation helpers, and a custom TV-oriented NordVPN control interface.

> **Independent community project:** Shield Pi is not affiliated with, endorsed by, sponsored by, or supported by NVIDIA or NordVPN. Product names are used only to describe interoperability. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Current milestone

**Shield NordVPN v10.24** is the current confirmed stable basis. New NordVPN development starts logically with **v10.25**.

The repository is still experimental, but installer, launcher and service paths are user-independent. Runtime files are resolved from the installing user's home directory; `SHIELD_HOME` can override that location where supported. Every installation requires its own locally authenticated NordVPN CLI session—no account credentials are included in this repository.

## Target platform

- Raspberry Pi 5
- Raspberry Pi OS / Debian Trixie
- labwc / Wayland
- GTK3 / Python
- 13-inch CRT, 720×576, 4:3
- NVIDIA Shield Remote via evdev

## Components

- `nordvpn/` — custom Shield-style NordVPN TV UI and distributable UI assets
- `launcher/` — CRT-optimized launcher, installed-app management, persistent workspaces and task manager
- `remote/` — direct evdev Shield Remote daemon with profiles for Kodi, Firefox/Chromium, FreeTube and VLC
- `vlc/` — Shield VLC frontend / DVD shuttle controls
- `freetube/` — FreeTube navigation integration
- `docs/` — architecture, project rules, current state and key mappings
- `milestones/` — milestone policy and development notes

## Launcher and application management

The launcher includes built-in entries for **VLC, FreeTube, Kodi and NordVPN**. The **Add application** tile discovers normal graphical `.desktop` entries installed by the operating system. Firefox, Chromium and other desktop applications can therefore be added when installed; they are not hard-coded default tiles.

- D-pad selects a launcher tile.
- Short **OK** launches an application or activates its existing window.
- The launcher avoids duplicate application instances.
- User-added tiles can be removed with a long **OK** press; this does not uninstall the application.
- Each managed application receives a persistent labwc workspace.

See [Launcher, application navigation and task manager](docs/LAUNCHER_NAVIGATION.md) for the complete behavior.

## Task manager

- One **Home** press returns to the launcher.
- A rapid double **Home** press opens **Recent applications**.
- Up to four recent-task cards are visible in a horizontal carousel.
- Cards show a thumbnail when available and indicate whether the application is active.
- **OK** opens or activates a task.
- **Down**, followed by **OK**, closes the selected task and removes it from the recent list.
- **Back** or **Home** returns to the launcher.

The task manager tracks applications launched and managed by Shield Pi; it is not a complete system process monitor.

## Remote interaction

Core navigation is designed to work without a mouse:

| Context | Main behavior |
| --- | --- |
| Launcher | D-pad selects; OK opens or activates |
| Kodi | Physical remote keys pass through for Kodi's native TV navigation |
| Firefox / Chromium | D-pad traverses focus, OK activates, Back goes through browser history, Search opens the address bar and on-screen keyboard |
| FreeTube | Application-specific spatial navigation and search integration |
| VLC / Shield VLC | Dedicated player, menu, dialog and media controls |
| Task manager | Left/Right select, OK opens, Down enters close mode, Up cancels |

**Home** remains global: one press opens the launcher and a rapid double press opens the task manager.

## Design principles

**Free in the search for solutions. Conservative toward working components.**

The project prioritizes, in order: working behavior, regression prevention, D-pad usability, correct CRT geometry, stability, state preservation, approved visual fidelity, maintainability and performance.

Real Raspberry Pi/CRT tests, screenshots, logs and current source code are treated as stronger evidence than old assumptions.

## Development status

The current development focus is the NordVPN multi-city/multi-server **SHIELD SERVER GRID**. Country/city/server cards use the established **164×102 px** geometry with four visible cards in a horizontal carousel.

For deeper project context see:

- [Launcher, application navigation and task manager](docs/LAUNCHER_NAVIGATION.md)
- [Current state](docs/CURRENT_STATE.md)
- [Components and protected areas](docs/COMPONENTS_AND_PROTECTED_AREAS.md)
- [Remote keycodes](docs/REMOTE_KEYCODES.md)
- [Project master definition](docs/PROJECT_MASTER_PROMPT.md)
- [Version history](docs/VERSION_HISTORY.md)

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Bug reports and feature requests can use the repository issue templates.

For security-sensitive reports, follow [SECURITY.md](SECURITY.md) and do not publish secrets or working exploit details in a public issue.

## License

Project source code is intended to be released under **GNU GPL v3.0 only (`GPL-3.0-only`)**, except where a file or third-party asset states otherwise. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Important trademark note

NVIDIA, SHIELD, NordVPN, Kodi, VLC, FreeTube, Firefox, Chromium and other third-party names/logos remain the property of their respective owners. Shield Pi's Shield-inspired visual language is an independent community design and must not be presented as an official product or endorsement.
