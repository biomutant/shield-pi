# NVIDIA SHIELD REMOTE — KEYCODES

| Input | Linux keycode |
| --- | ---: |
| Up | 103 |
| Down | 108 |
| Left | 105 |
| Right | 106 |
| OK / KEY_SELECT | 353 |
| Back | 158 |
| Home | 172 |
| Menu | 139 |
| Play/Pause | 164 |
| Volume up | 115 |
| Volume down | 114 |
| Microphone/Search | 217 |
| Netflix/Video | 393 |
| Rewind | 168 |
| Fast-forward | 208 |

## Global Home behavior

- one Home press → Launcher
- rapid double Home within 380 ms → Task manager
- Home while the task manager is visible → Launcher

## Application profiles

The remote daemon selects a profile from the active window:

- **Kodi:** physical remote keycodes are passed through unchanged, preserving Kodi's native TV navigation. Short OK selects the focused item; long OK opens Kodi's context menu.
- **Firefox / Chromium / Chrome:** Down, Right and Menu advance focus with Tab; Up and Left move to the previous focus target with Shift+Tab; OK sends Enter; Back sends Alt+Left.
- **FreeTube:** application-specific navigation uses the Chromium remote-debugging integration.
- **VLC / Shield VLC:** dedicated player, menu, dialog and media mappings are used.
- **Generic applications:** OK maps to Enter, Back maps to Escape and Menu maps to Tab; remaining keys pass through.

The Microphone/Search button is the dedicated on-screen-keyboard control. In browser profiles it first focuses the address bar. In FreeTube it first requests the application's search field.

See [Launcher, application navigation and task manager](LAUNCHER_NAVIGATION.md) for the user-facing navigation and task-switching behavior.
