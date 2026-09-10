# CURRENT STATE — SHIELD PI

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

## Stable / protected working areas

Unless explicitly targeted, preserve:

- Launcher visual design and navigation
- Shield Remote daemon behavior
- Kodi short/long OK behavior
- single Home → Launcher and rapid double Home → Task Manager
- Shield VLC seek/DVD behavior
- FreeTube remote navigation
- NordVPN Home
- NordVPN first System page
- NordVPN VPN/DNS/Status second-level pages

## Repository component snapshots

- `nordvpn/` — current v10.24 NordVPN source and project-owned UI assets
- `launcher/` — current Shield Launcher snapshot
- `remote/` — current Shield Remote daemon, profiles and service material
- `vlc/` — Shield VLC v20 DVD/shuttle snapshot
- `freetube/` — FreeTube navigation integration

## Approved visual references

Project-approved visual references and CRT photographs remain in the private development archive because they may contain environmental details or runtime network information. The public repository contains only the distributable application assets.

## Public collaboration note

The public candidate intentionally excludes personal CRT/home photos, duplicate release ZIP archives and unverified third-party flag assets from the current tree. See `PUBLIC_RELEASE_CHECKLIST.md` and the repository-level `THIRD_PARTY_NOTICES.md`.
