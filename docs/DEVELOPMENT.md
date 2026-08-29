# Development

## Setup

Install the native runtime dependencies, then create an optional tooling virtual
environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install build ruff
```

PyGObject is normally supplied by the operating system. A virtual environment
may need `--system-site-packages` to see the distro-provided `gi` module.

## Run

```bash
./scripts/dev
```

Run checks:

```bash
make check
```

`make check` compiles the package, runs the narrow Ruff safety rules, and runs
unit tests. GTK integration tests require a real Wayland session and are not run
in GitHub Actions.

## Safe test environment

Point HyprConfig at disposable directories:

```bash
tmpdir=$(mktemp -d)
XDG_CONFIG_HOME="$tmpdir/config" \
XDG_DATA_HOME="$tmpdir/data" \
HYPRCONFIG_HYPR_DIR="$tmpdir/hypr" \
PYTHONPATH=src python3 -m hyprconfig
```

Do not test persistence against valuable dotfiles without a commit or backup.

## Release process

1. Update `src/hyprconfig/__init__.py` and `pyproject.toml` versions.
2. Move user-visible changes from `Unreleased` in `CHANGELOG.md`.
3. Run `make check` in a Hyprland environment.
4. Test `install.sh` and `uninstall.sh` with temporary XDG directories.
5. Review `docs/PUBLIC_RELEASE.md` and all bundled asset licenses.
6. Build both distributions with `python -m build`.
7. Tag `vX.Y.Z` only after the release checks pass.
