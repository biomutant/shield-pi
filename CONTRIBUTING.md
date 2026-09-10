# Contributing to Shield Pi

Thanks for your interest in Shield Pi. The project targets a Raspberry Pi 4 connected to a 13-inch 720×576 4:3 CRT and is designed for full D-pad/remote operation.

## Ground rules

- Preserve working subsystems unless the change explicitly targets them.
- Treat real Raspberry Pi/CRT tests, screenshots, logs, and current source as stronger evidence than assumptions.
- Prefer root-cause fixes over broad rewrites.
- Keep core navigation usable without a mouse.
- Do not change the established 164×102 country/city/server card geometry without an explicit design decision.
- Do not include credentials, tokens, personal logs, private photos, or machine-specific secrets in commits.

## Development workflow

1. Fork the repository or create a feature branch.
2. Keep each change focused on one problem or feature.
3. Explain the affected subsystem and any regression risk.
4. Run Python syntax checks for modified Python files, for example:

```bash
python3 -m py_compile nordvpn/nordvpn-app.py
```

5. For UI changes, describe how the result was tested at 720×576 and with D-pad navigation.
6. Open a pull request against `main`.

## Pull request expectations

A useful PR includes:

- what changed and why;
- files/subsystems touched;
- what was deliberately not changed;
- test steps and results;
- screenshots for visible UI changes where safe to publish;
- any known limitations.

## Current stable basis

Shield NordVPN v10.24 is the current confirmed project milestone. New NordVPN work should preserve confirmed v10.24 behavior unless the PR explicitly replaces it.

## Style

The UI language is intentionally dark, high-contrast, CRT-readable, Shield-inspired cyber/military/tactical HUD styling. Function and remote usability take priority over decoration.
