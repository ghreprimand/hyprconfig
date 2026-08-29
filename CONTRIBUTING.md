# Contributing to HyprConfig

HyprConfig is a small, maintainer-led project. Bug reports, documentation fixes,
portability improvements, and focused patches are welcome.

## Before starting

- Search open and closed issues first.
- Use a change proposal before implementing a substantial feature or changing
  managed configuration formats.
- Coordinate on an accepted issue before beginning a large patch.
- Never include private dotfiles, credentials, hostnames, device identifiers,
  or identifying local paths in issues, screenshots, logs, or commits.

## Development workflow

1. Create a focused branch.
2. Add or update tests for non-GTK behavior.
3. Run `make check`.
4. Test UI or compositor changes in a Hyprland session.
5. Update user documentation and `CHANGELOG.md` when behavior changes.
6. Open a pull request linked to the relevant issue or proposal.

No Contributor License Agreement or Developer Certificate of Origin is
required. Contributions are submitted under the repository's GPL-3.0-only
license, and contributors retain copyright in their contributions.

## Project rules

- Preserve user data. Configuration changes need a recoverable backup and an
  atomic replacement path.
- Use `pathlib.Path` for filesystem paths.
- Pass argument arrays to subprocesses; do not use `shell=True`.
- Match managed processes by exact executable name.
- Keep user paths centralized in `paths.py`.
- Treat missing optional programs and configuration files as supported states.
- Do not add third-party code or assets without the upstream URL, author,
  license, and required notices.

## Verification

Before submitting:

```bash
make check
```

Also inspect the staged diff, run `git diff --cached --check`, and scan it for
secrets, personal data, machine-local configuration, and unlicensed material.
