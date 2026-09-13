# System templates

These files are sanitized examples from the confirmed 2026-09-12 Raspberry Pi
4 setup. Compare them with the target system before installation.

- Replace `@USER@`, `@GROUP@`, `@HOME@` and `@UID@` in service templates.
- Replace `@HOME@` in the desktop template.
- Keep NAS credentials outside the repository in a root-only file on the Pi.
- Copy `launcher/assets/shield-background-crt.png` to
  `~/.config/shield-launcher/` when the launcher is installed as a single file.
- The VLC installer copies its project-owned PNG assets to
  `~/.config/shield-vlc/`.

Do not overwrite an existing labwc configuration without reviewing the diff.
