# Launcher, application navigation and task manager

This document describes the behavior implemented by the current Shield Pi launcher and Shield Remote daemon.

## Launcher applications

The launcher starts with four built-in application tiles:

- VLC
- FreeTube
- Kodi
- NordVPN
- **Add application** as the management entry point

The launcher is designed for D-pad operation. Move between tiles with the D-pad and press **OK** to launch the selected application. If a managed application is already running, Shield Pi activates its existing window instead of starting a duplicate instance.

## Adding installed applications

**Add application** scans graphical desktop entries in:

- `/usr/share/applications`
- `$HOME/.local/share/applications`

Hidden, terminal-only and `NoDisplay` entries are ignored. This means Firefox, Chromium and other graphical applications can be added when their packages provide a normal `.desktop` file. Firefox and Chromium are supported navigation profiles, but they are not hard-coded default launcher tiles.

Added applications are stored locally in:

`$HOME/.config/shield-launcher/launcher-apps.json`

For a user-added tile, a long **OK** press opens the removal confirmation. Removing a tile only removes it from Shield Pi's launcher configuration; it does **not** uninstall the application from the operating system.

## Application activation and workspaces

The launcher manages applications on persistent labwc workspaces:

- the launcher remains on workspace 1;
- managed applications are assigned workspaces beginning with workspace 2;
- known window IDs are saved and reused;
- new window IDs can be learned after an application's first launch;
- opening a running application activates its existing window;
- opening a stopped application starts it once.

Workspace assignments are stored in:

`$HOME/.config/shield-launcher/workspaces.json`

Shield Pi writes the corresponding managed application rules to the user's labwc configuration.

## Task manager

A single **Home** press returns to the launcher. A rapid double **Home** press, within the configured 380 ms window, opens **Recent applications**.

The task manager tracks applications launched and managed by Shield Pi. It is a recent-application switcher, not a complete list of every arbitrary desktop process.

Up to four task cards are visible at once in a horizontal carousel. A card can show a captured thumbnail when `grim` is available; otherwise it uses the application icon. The card also indicates whether the application is currently active or only remembered.

Task manager controls:

| Remote input | Action |
| --- | --- |
| Left / Right | Select a recent application |
| OK | Open or activate the selected application |
| Down | Enter close/remove mode |
| Up | Cancel close/remove mode |
| OK in close/remove mode | Close the selected application and remove it from the recent list |
| Back | Close the task manager and return to the launcher |
| Home | Return to the launcher |

Recent tasks and thumbnails are stored under:

- `$HOME/.config/shield-launcher/recent-tasks.json`
- `$HOME/.config/shield-launcher/thumbnails/`

The launcher uses `$HOME/shield-tasks/shield-tasks` to list, activate and close Wayland windows.

## Application-aware remote navigation

The active window determines which navigation profile the Shield Remote daemon uses.

| Context | D-pad | OK | Back | Search / Menu |
| --- | --- | --- | --- | --- |
| Launcher | Move between launcher controls | Open or activate | Return/cancel where defined | Search opens the on-screen keyboard |
| Kodi | Passed through unchanged for Kodi's native TV navigation | Native Kodi select | Native Kodi back | Native key handling |
| Firefox / Chromium / Chrome | Down or Right: next focus; Up or Left: previous focus | Enter/activate | Browser history back | Search focuses the address bar and opens the on-screen keyboard; Menu advances focus |
| FreeTube | Application-specific spatial navigation through the remote-debugging integration | Activate focused item | Application-aware back behavior | Search focuses FreeTube search and opens the on-screen keyboard |
| VLC / Shield VLC | Dedicated player, menu, dialog and media navigation | Context-dependent selection/playback control | Context-dependent back/close | Dedicated VLC behavior |
| Generic application | Arrow keys are passed through; compatibility mappings apply where defined | Enter | Escape | Menu sends Tab |

**Home** is global: one press returns to the launcher and a rapid double press opens the task manager.

## Local state and privacy

Launcher state, learned application IDs, thumbnails and recent-task data remain local under `$HOME/.config/shield-launcher/` and are not part of the repository. These files can contain local application names or screenshots and should not be committed to GitHub.

## Current scope

Application discovery depends on valid desktop entries, and window activation depends on the labwc/Wayland helper. Remote behavior may vary for applications whose interfaces do not expose predictable keyboard focus. New application profiles should preserve the global Home behavior and must remain usable without a mouse.
