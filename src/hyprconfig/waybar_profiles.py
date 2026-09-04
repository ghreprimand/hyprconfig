"""Local Waybar snapshots. Personal configuration never becomes bundled data."""

import json
import re
import shutil
import tempfile
import uuid
from pathlib import Path

from .jsonc import loads as load_jsonc
from .paths import WAYBAR_DIR, WAYBAR_PROFILES_DIR
from .safe_io import UnsafeWriteError, atomic_write_bytes, backup_file

PROFILE_ID = re.compile(r"[0-9a-f]{32}")
FILES = ("config.jsonc", "style.css")
MAX_FILE_SIZE = 5 * 1024 * 1024


def _read_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular file: {path.name}")
    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"File exceeds the 5 MiB profile limit: {path.name}")
    return path.read_bytes()


def _read_setup(directory, *, allow_config=False):
    config = directory / "config.jsonc"
    if allow_config and not config.exists() and not config.is_symlink():
        config = directory / "config"
    data = {"config.jsonc": _read_file(config),
            "style.css": _read_file(directory / "style.css")}
    parsed = load_jsonc(data["config.jsonc"].decode("utf-8"))
    if not (isinstance(parsed, dict) or
            (isinstance(parsed, list) and parsed and
             all(isinstance(bar, dict) for bar in parsed))):
        raise ValueError("Waybar configuration must be an object or a nonempty array of objects.")
    data["style.css"].decode("utf-8")
    return data


def profile_dir(profile_id):
    if not isinstance(profile_id, str) or not PROFILE_ID.fullmatch(profile_id):
        raise ValueError("Invalid local profile ID.")
    path = WAYBAR_PROFILES_DIR / profile_id
    if WAYBAR_PROFILES_DIR.is_symlink() or path.is_symlink():
        raise ValueError("Local profile directories must not be symbolic links.")
    return path


def save_profile(name, description=""):
    """Snapshot both active files without changing or restarting Waybar."""
    name, description = name.strip(), description.strip()
    if not name or len(name) > 80 or len(description) > 400:
        raise ValueError("Use a name of 1–80 characters and a description of at most 400 characters.")
    data = _read_setup(WAYBAR_DIR, allow_config=True)
    profile_id = uuid.uuid4().hex
    destination = profile_dir(profile_id)
    WAYBAR_PROFILES_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = Path(tempfile.mkdtemp(prefix=".saving-", dir=WAYBAR_PROFILES_DIR))
    info = {"name": name, "desc": description, "version": 1}
    try:
        for filename, content in data.items():
            atomic_write_bytes(temporary / filename, content, mode=0o600, backup=False)
        atomic_write_bytes(temporary / "profile.json",
                           (json.dumps(info, indent=2) + "\n").encode("utf-8"),
                           mode=0o600, backup=False)
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return profile_id


def list_profiles():
    """Discover complete local snapshots; ignore damaged or unrelated entries."""
    if WAYBAR_PROFILES_DIR.is_symlink() or not WAYBAR_PROFILES_DIR.is_dir():
        return {}
    profiles = {}
    for directory in sorted(WAYBAR_PROFILES_DIR.iterdir()):
        if not PROFILE_ID.fullmatch(directory.name):
            continue
        try:
            directory = profile_dir(directory.name)
            info = json.loads(_read_file(directory / "profile.json"))
            if (not isinstance(info, dict) or info.get("version") != 1 or
                    not isinstance(info.get("name"), str) or
                    not 1 <= len(info["name"].strip()) <= 80 or
                    not isinstance(info.get("desc", ""), str) or
                    len(info.get("desc", "")) > 400):
                continue
            _read_setup(directory)
        except (OSError, ValueError):
            continue
        profiles[directory.name] = {
            "name": info["name"],
            "desc": info.get("desc") or "Saved Waybar layout and styling on this device.",
            "preview": "Local profile · layout + styling · current theme colors",
        }
    return profiles


def apply_setup(directory):
    """Validate both files, back up destinations, and restore them if a write fails."""
    data = _read_setup(Path(directory))
    WAYBAR_DIR.mkdir(parents=True, exist_ok=True)
    previous = {}
    for filename in FILES:
        path = WAYBAR_DIR / filename
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise UnsafeWriteError(f"Refusing to replace non-regular file: {filename}")
        previous[filename] = path.read_bytes() if path.exists() else None
    for filename in FILES:
        backup_file(WAYBAR_DIR / filename)
    written = []
    try:
        for filename in FILES:
            # Track before writing: a write may fail after its atomic replacement.
            written.append(filename)
            atomic_write_bytes(WAYBAR_DIR / filename, data[filename], backup=False)
    except OSError:
        for filename in reversed(written):
            path = WAYBAR_DIR / filename
            if previous[filename] is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write_bytes(path, previous[filename], backup=False)
        raise
