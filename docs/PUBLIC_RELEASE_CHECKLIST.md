# Public release checklist

This repository is being prepared for public collaboration.

## Completed in `public-release-prep`

- Public-facing README and independent-project disclaimer
- GPL-3.0-only project license notice
- CONTRIBUTING.md
- SECURITY.md
- CODE_OF_CONDUCT.md
- third-party/trademark notices
- bug and feature issue templates
- pull-request template
- public-safe `.gitignore`
- one-time bootstrap workflow removed
- private CRT photo removed from the public candidate tree
- unverified bundled city-flag asset removed from the public candidate tree
- duplicate packaged ZIP archives removed from the public candidate tree
- source scan found no obvious committed passwords/API keys/private keys in the v10.24 source bundle

## Blocking before changing repository visibility

The existing private Git history contains material that should not automatically become public even though it is removed from the current candidate tree:

1. The initial repository commit records a personal email address in Git commit metadata.
2. Earlier history contains a real CRT/home-environment photograph.
3. Earlier history contains bootstrap/release archives that duplicate historical project contents and have not all been independently reviewed for public redistribution.

Deleting a file in a later commit does **not** remove it from Git history. Therefore the repository should remain private until history is rewritten to a clean public baseline, or a new clean public repository is created from the `public-release-prep` tree.

## Asset rule for future contributions

Do not commit third-party logos, city/municipal flags, photos, screenshots, or other externally sourced visual material without recording provenance and redistribution terms. Runtime-downloaded caches should remain ignored.

## Final publication steps

- create/rewrite a clean history containing only the public candidate tree;
- ensure future Git commits use a privacy-safe/noreply author email if desired;
- verify the clean history contains no private photo or unreviewed archives;
- optionally replace the short GPL notice with the full canonical GPLv3 license text;
- mark the repository Public in GitHub settings;
- publish installable versions as GitHub Releases from traceable tags/commits.
