# Shield Pi

Shield Pi is an experimental Raspberry Pi 5 project for a **fully remote-controlled TV/media interface designed around a real 13-inch 720×576 4:3 CRT**.

The project combines a custom GTK3 launcher, direct NVIDIA Shield Remote input handling, a Shield-style VLC frontend, FreeTube navigation helpers, and a custom TV-oriented NordVPN control interface.

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

- `nordvpn/` — custom Shield-style NordVPN TV UI
- `launcher/` — CRT-optimized Shield launcher
- `remote/` — direct evdev Shield Remote daemon and profiles
- `vlc/` — Shield VLC frontend / DVD shuttle controls
- `freetube/` — FreeTube navigation integration
- `docs/` — architecture, project rules, current state and key mappings
- `assets/` — project visual references
- `milestones/` — development milestone material

## Design principles

**Free in the search for solutions. Conservative toward working components.**

The project prioritizes, in order: working behavior, regression prevention, D-pad usability, correct CRT geometry, stability, state preservation, approved visual fidelity, maintainability and performance.

Real Raspberry Pi/CRT tests, screenshots, logs and current source code are treated as stronger evidence than old assumptions.

## Remote interaction

Core navigation is designed to work without a mouse:

- D-pad — navigate
- short OK — select/open/connect
- long OK — details/context where defined
- Back — one level back
- Home — launcher

The project also preserves dedicated media-navigation behavior for Kodi, VLC and FreeTube where already established.

## Development status

The current development focus is the NordVPN multi-city/multi-server **SHIELD SERVER GRID**. Country/city/server cards use the established **164×102 px** geometry with four visible cards in a horizontal carousel.

For deeper project context see:

- `docs/PROJECT_MASTER_PROMPT.md`
- `docs/CURRENT_STATE.md`
- `docs/COMPONENTS_AND_PROTECTED_AREAS.md`
- `docs/VERSION_HISTORY.md`

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Bug reports and feature requests can use the repository issue templates.

For security-sensitive reports, follow [SECURITY.md](SECURITY.md) and do not publish secrets or working exploit details in a public issue.

## License

Project source code is intended to be released under **GNU GPL v3.0 only (`GPL-3.0-only`)**, except where a file or third-party asset states otherwise. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Important trademark note

NVIDIA, SHIELD, NordVPN, Kodi, VLC, FreeTube and other third-party names/logos remain the property of their respective owners. Shield Pi's Shield-inspired visual language is an independent community design and must not be presented as an official product or endorsement.
