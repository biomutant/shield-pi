# Milestones and releases

Shield Pi development uses explicit stable milestones so working behavior can be preserved while new changes are tested.

## Current canonical milestone

**Shield NordVPN v10.24** is the current confirmed stable basis.

New NordVPN work starts logically at **v10.25** unless a newer milestone is explicitly promoted.

## Historical milestone

- v10.18 — earlier confirmed stable rollback point for the NordVPN UI.

## Release packaging policy

Source history should stay readable and should not accumulate duplicate ZIP archives. Packaged installable ZIPs are intended to be published as GitHub Releases rather than committed repeatedly under `milestones/`.

A release package should include its installer and all required project-owned assets, and should be generated from a traceable source commit/tag.

Before publishing a release, validate modified Python files with `python3 -m py_compile` and document the actual Raspberry Pi/CRT test status.
