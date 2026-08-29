"""Recoverable, atomic filesystem writes used by HyprConfig."""

import hashlib
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .paths import BACKUP_DIR, HOME


class UnsafeWriteError(RuntimeError):
    """Raised when a managed write targets a symbolic link or non-file."""


def _backup_destination(path):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    try:
        relative = path.resolve(strict=False).relative_to(HOME.resolve())
    except ValueError:
        digest = hashlib.sha256(str(path).encode()).hexdigest()[:12]
        relative = Path("external") / digest / path.name
    return BACKUP_DIR / stamp / relative


def backup_file(path):
    """Copy an existing regular file into the timestamped backup tree."""
    path = Path(path)
    if path.is_symlink():
        raise UnsafeWriteError(f"Refusing to follow symbolic link: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise UnsafeWriteError(f"Refusing to replace non-file: {path}")
    destination = _backup_destination(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    return destination


def atomic_write_bytes(path, content, *, mode=None, backup=True):
    """Back up and atomically replace a regular file in its own directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise UnsafeWriteError(f"Refusing to replace symbolic link: {path}")

    existing_mode = None
    if path.exists():
        if not path.is_file():
            raise UnsafeWriteError(f"Refusing to replace non-file: {path}")
        existing_mode = path.stat().st_mode & 0o777
        if backup:
            backup_file(path)

    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode if mode is not None else (existing_mode or 0o644))
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(path, content, *, mode=None, backup=True):
    atomic_write_bytes(path, content.encode("utf-8"), mode=mode, backup=backup)


def atomic_copy(source, destination, *, backup=True):
    source = Path(source)
    atomic_write_bytes(
        destination,
        source.read_bytes(),
        mode=source.stat().st_mode & 0o777,
        backup=backup,
    )


def remove_with_backup(path):
    """Remove a regular managed file after preserving a timestamped copy."""
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return None
    destination = backup_file(path)
    path.unlink()
    return destination


def atomic_symlink(path, target):
    """Atomically replace a link, backing up a pre-existing regular file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.is_symlink():
        backup_file(path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.hyprconfig-link.", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    temporary.symlink_to(target)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def update_managed_block(path, name, body):
    """Insert or replace one named marker block without touching other blocks."""
    path = Path(path)
    begin = f"# BEGIN HyprConfig: {name}"
    end = f"# END HyprConfig: {name}"
    block = f"{begin}\n{body.rstrip()}\n{end}"
    current = path.read_text() if path.exists() else ""
    start = current.find(begin)
    finish = current.find(end, start + len(begin)) if start >= 0 else -1
    if start >= 0 and finish >= 0:
        finish += len(end)
        updated = current[:start] + block + current[finish:]
    else:
        updated = current.rstrip()
        updated = f"{updated}\n\n{block}" if updated else block
    atomic_write_text(path, updated.rstrip() + "\n")
