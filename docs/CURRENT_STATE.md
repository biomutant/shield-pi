# CURRENT STATE — SHIELD PI

## Canonical complete-system milestone

**Stable 2026-09-12** is the confirmed basis for launcher, task manager,
remote daemon, Shield VLC/NAS playback and the projectM/MilkDrop music player.

The task manager now displays three enlarged cards, stores one persistent
screenshot per application, pauses multimedia on leaving a task and resumes it
when the same task is activated again. Discarding a card remains the explicit
operation that closes that task.

## Canonical NordVPN milestone

**v10.24** is the current confirmed Shield NordVPN milestone and preferred stable basis.

The authoritative source snapshot lives in `nordvpn/`. New NordVPN development should start at v10.25 unless a newer milestone is explicitly promoted.

## Current main NordVPN concern

The last real CRT test before v10.24 showed that the Server Grid's vertical regions overlapped after restoring the card size to **164×102 px**. The card size itself is correct and protected; v10.24 was created specifically to correct the surrounding vertical geometry.

When continuing this work:

- inspect the actual current `nordvpn/nordvpn-app.py` first;
- treat new real Raspberry Pi/CRT evidence as stronger than old assumptions;
- change only the Server Grid geometry unless the task explicitly expands the scope;
- do not solve overlap by changing the established 164×102 card size.

## Current launcher and navigation behavior

The published launcher contains built-in entries for VLC, FreeTube, Kodi and NordVPN. It can discover additional graphical applications from system and user `.desktop` files through **Add application**. Firefox and Chromium therefore appear as addable applications when installed.

Managed applications receive persistent labwc workspaces. Selecting a running application activates its existing window rather than launching a duplicate.

The task manager tracks recent Shield Pi applications, displays three enlarged
cards at once, preserves application-specific screenshots and supports
activating or explicitly discarding a task. One Home press returns to the
launcher; a rapid double Home opens the task manager.

Remote behavior is selected from the active application:

- Kodi receives the physical remote keys unchanged for native Kodi TV navigation; short OK selects and long OK opens Kodi's context menu.
- Firefox/Chromium use focus traversal, Enter activation, browser Back and address-bar/on-screen-keyboard integration.
- FreeTube and VLC use their dedicated application-specific navigation paths.

See `LAUNCHER_NAVIGATION.md` for details.

## Stable / protected working areas

Unless explicitly targeted, preserve:

- Launcher visual design, installed-app management and navigation
- persistent application workspaces and duplicate-instance prevention
- recent-application task manager behavior
- Shield Remote daemon behavior
- Kodi native key passthrough
- Firefox/Chromium remote-navigation profile
- single Home → Launcher and rapid double Home → Task manager
- Shield VLC seek/DVD behavior
- FreeTube remote navigation
- NordVPN Home
- NordVPN first System page
- NordVPN VPN/DNS/Status second-level pages

## Repository component snapshots

- `nordvpn/` — current v10.24 NordVPN source and project-owned UI assets
- `launcher/` — current Shield Launcher, app-management and task-manager snapshot
- `remote/` — current Shield Remote daemon, profiles and service material
- `vlc/` — Shield VLC with NAS/video playback, remote controls and the 4:3
  projectM/MilkDrop music-player design
- `freetube/` — FreeTube navigation integration
- `system/` — sanitized CRT, labwc, projectM and service templates

## Approved visual references

The public repository contains only the approved visual references that passed
the privacy review and had image metadata removed. Personal CRT/home photos and
runtime screenshots remain in the private development archive.

## Public collaboration note

The public repository intentionally excludes personal CRT/home photos,
duplicate release ZIP archives, credentials, runtime state and unverified
third-party flag assets. See `PUBLIC_RELEASE_CHECKLIST.md` and the
repository-level `THIRD_PARTY_NOTICES.md`.
