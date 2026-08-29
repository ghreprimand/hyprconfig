"""Hyprland configuration parser and writer for HyprConfig."""

import re
import json
import glob
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass, field

from .paths import (
    HYPR_DIR,
    HYPRLAND_CONF,
    KEYBINDINGS_CONF,
    LEGACY_STATE_FILE,
    MANAGED_CONF,
    STATE_FILE,
    USERPREFS_CONF,
    WAYBAR_DIR,
    WAYBAR_VARIANTS_DIR,
)
from .safe_io import atomic_write_text, update_managed_block


@dataclass
class Keybind:
    mods: str
    key: str
    description: str
    dispatcher: str
    args: str = ""
    group: str = ""
    subgroup: str = ""
    source_file: str = ""
    source_path: Path | None = None
    flags: str = ""
    line_num: int = 0

    @property
    def combo(self):
        parts = []
        if self.mods:
            parts.extend(self.mods.split())
        parts.append(self.key)
        return '+'.join(parts)

    @property
    def combo_key(self):
        mods = sorted(self.mods.lower().split()) if self.mods else []
        return '+'.join(mods) + '+' + self.key.lower()


def resolve_vars(text, variables):
    """Resolve $variables in text."""
    def replace_var(match):
        name = match.group(1)
        return variables.get(name, match.group(0))
    # Multiple passes to resolve nested variables
    for _ in range(3):
        new_text = re.sub(r'\$(\w+)', replace_var, text)
        if new_text == text:
            break
        text = new_text
    return text


def discover_hyprland_files():
    """Return the stock config and its recursively sourced configuration files."""
    if not HYPRLAND_CONF.exists():
        return [path for path in (KEYBINDINGS_CONF, USERPREFS_CONF) if path.exists()]

    discovered = []
    visited = set()

    def visit(path):
        path = Path(path).expanduser().resolve(strict=False)
        if path in visited or not path.is_file():
            return
        visited.add(path)
        discovered.append(path)
        try:
            text = path.read_text()
        except (OSError, UnicodeError):
            return
        for raw in text.splitlines():
            match = re.match(r'^\s*source\s*=\s*(.+?)\s*(?:#.*)?$', raw)
            if not match:
                continue
            expression = os.path.expandvars(os.path.expanduser(match.group(1).strip()))
            candidate = Path(expression)
            if not candidate.is_absolute():
                candidate = path.parent / candidate
            for matched in sorted(glob.glob(str(candidate))):
                visit(matched)

    visit(HYPRLAND_CONF)
    return discovered


def parse_keybindings(files=None):
    """Parse keybindings from Hyprland config files."""
    if files is None:
        files = discover_hyprland_files()

    all_binds = []

    for filepath in files:
        filepath = Path(filepath)
        if not filepath.exists():
            continue

        variables = {'mainMod': 'Super'}
        current_group = ""
        current_subgroup = ""

        with open(filepath) as f:
            for line_num, raw_line in enumerate(f, 1):
                line = raw_line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Variable assignment
                var_match = re.match(r'^\$(\w+)\s*=\s*(.+)$', line)
                if var_match:
                    name, value = var_match.groups()
                    # Strip inline comments (# ...) but not inside []
                    value = value.strip()
                    if '#' in value and not value.startswith('['):
                        # Don't strip # inside bracket groups like [$wm|...]
                        comment_pos = value.find(' #')
                        if comment_pos > 0:
                            value = value[:comment_pos].strip()
                    value = resolve_vars(value, variables)
                    variables[name] = value

                    if name == 'd':
                        group_match = re.match(r'\[([^\]]+)\]', value)
                        if group_match:
                            parts = group_match.group(1).split('|')
                            current_group = parts[0].strip()
                            current_subgroup = (
                                ' > '.join(p.strip() for p in parts[1:])
                                if len(parts) > 1 else ""
                            )
                        else:
                            current_group = ""
                            current_subgroup = ""
                    continue

                # Bind lines
                bind_match = re.match(r'^bind([delmnrt]*)\s*=\s*(.+)$', line)
                if bind_match:
                    flags = bind_match.group(1)
                    rest = bind_match.group(2)
                    rest = resolve_vars(rest, variables)

                    parts = [p.strip() for p in rest.split(',')]
                    if len(parts) < 3:
                        continue

                    mods = parts[0]
                    key = parts[1]

                    if 'd' in flags:
                        if len(parts) < 4:
                            continue
                        description = parts[2]
                        dispatcher = parts[3]
                        args = ', '.join(parts[4:]) if len(parts) > 4 else ""
                    else:
                        description = ""
                        dispatcher = parts[2]
                        args = ', '.join(parts[3:]) if len(parts) > 3 else ""

                    # Strip group prefix from description
                    desc_clean = description
                    gp = re.match(r'^\[([^\]]*)\]\s*', description)
                    if gp:
                        desc_clean = description[gp.end():]

                    bind = Keybind(
                        mods=mods,
                        key=key,
                        description=desc_clean.strip(),
                        dispatcher=dispatcher.strip(),
                        args=args.strip(),
                        group=current_group,
                        subgroup=current_subgroup,
                        source_file=filepath.name,
                        source_path=filepath,
                        flags=flags,
                        line_num=line_num,
                    )
                    all_binds.append(bind)

    return all_binds


def find_conflicts(binds):
    """Find keybinds sharing the same key combo (excluding intentional chains)."""
    combo_map = {}
    for bind in binds:
        key = bind.combo_key
        if key not in combo_map:
            combo_map[key] = []
        combo_map[key].append(bind)

    conflicts = {}
    for k, v in combo_map.items():
        if len(v) <= 1:
            continue
        # Same file + consecutive lines = intentional chain (e.g. movefocus + bringactivetotop)
        all_same_file = len(set(b.source_file for b in v)) == 1
        if all_same_file:
            lines = sorted(b.line_num for b in v)
            consecutive = all(lines[i+1] - lines[i] <= 2 for i in range(len(lines)-1))
            if consecutive:
                continue
        conflicts[k] = v
    return conflicts


def rewrite_bind(bind, new_mods, new_key):
    """Rewrite a keybind's mods and key in its source config file."""
    filepath = bind.source_path or (HYPR_DIR / bind.source_file)
    if not filepath.exists():
        return False

    lines = filepath.read_text().splitlines()
    if bind.line_num < 1 or bind.line_num > len(lines):
        return False

    old_line = lines[bind.line_num - 1]

    # Match: bind[flags] = MODS, KEY, ...rest
    m = re.match(r'^(bind[delmnrt]*\s*=\s*)([^,]*),\s*([^,]*),(.*)$', old_line)
    if not m:
        return False

    prefix = m.group(1)
    rest = m.group(4)

    new_line = f"{prefix}{new_mods}, {new_key},{rest}"
    lines[bind.line_num - 1] = new_line
    atomic_write_text(filepath, '\n'.join(lines) + '\n')
    return True


def hyprctl_get(option_path):
    """Get a Hyprland option via hyprctl getoption."""
    try:
        r = subprocess.run(
            ['hyprctl', 'getoption', option_path],
            capture_output=True, text=True, timeout=2
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                s = line.strip()
                if s.startswith('int:'):
                    return int(s.split(':')[1].strip())
                elif s.startswith('float:'):
                    return float(s.split(':')[1].strip())
                elif s.startswith('str:'):
                    return s.split(':', 1)[1].strip().strip('"')
    except Exception:
        pass
    return None


def hyprctl_set(option_path, value):
    """Set a Hyprland option live via hyprctl keyword."""
    try:
        subprocess.run(
            ['hyprctl', 'keyword', option_path, str(value)],
            capture_output=True, timeout=2
        )
    except Exception:
        pass


def hyprctl_monitors():
    """Get monitor info."""
    try:
        r = subprocess.run(
            ['hyprctl', 'monitors', '-j'],
            capture_output=True, text=True, timeout=2
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return []


def hyprctl_reload():
    """Reload Hyprland config."""
    try:
        subprocess.run(['hyprctl', 'reload'], capture_output=True, timeout=2)
    except Exception:
        pass


def ensure_managed_config():
    """Ensure the stock Hyprland entry point loads HyprConfig's fragment."""
    HYPR_DIR.mkdir(parents=True, exist_ok=True)
    content = HYPRLAND_CONF.read_text() if HYPRLAND_CONF.exists() else ""
    for raw in content.splitlines():
        match = re.match(r'^\s*source\s*=\s*(.+?)\s*(?:#.*)?$', raw)
        if not match:
            continue
        expression = os.path.expandvars(os.path.expanduser(match.group(1).strip()))
        candidate = Path(expression)
        if not candidate.is_absolute():
            candidate = HYPRLAND_CONF.parent / candidate
        if candidate.resolve(strict=False) == MANAGED_CONF.resolve(strict=False):
            return
    source_line = f"source = {MANAGED_CONF}"
    updated = content.rstrip()
    updated = f"{updated}\n\n# HyprConfig managed settings\n{source_line}\n" if updated else f"{source_line}\n"
    atomic_write_text(HYPRLAND_CONF, updated)


def persist_decoration(settings):
    """Write decoration settings to HyprConfig's sourced fragment."""
    new_block = f"""decoration {{
    rounding = {settings['rounding']}
    active_opacity = {settings['active_opacity']:.2f}
    inactive_opacity = {settings['inactive_opacity']:.2f}
    blur {{
        enabled = {'true' if settings['blur_enabled'] else 'false'}
        size = {settings['blur_size']}
        passes = {settings['blur_passes']}
    }}
    shadow {{
        enabled = {'true' if settings['shadow_enabled'] else 'false'}
        range = {settings['shadow_range']}
        render_power = {settings['shadow_render_power']}
    }}
}}"""

    ensure_managed_config()
    update_managed_block(MANAGED_CONF, "decoration", new_block)


def persist_borders(active_border, inactive_border):
    """Write border colors to HyprConfig's sourced fragment."""
    new_block = f"""general {{
    col.active_border = {active_border}
    col.inactive_border = {inactive_border}
}}"""

    ensure_managed_config()
    update_managed_block(MANAGED_CONF, "borders", new_block)


# ─── Declarative theme selector model ───────────────────────────────────────
# The visible look is fully described by these selector values. Each key names
# an element; each value names which variant is active. One value per element is
# always the untouched "base" (current look). No snapshot/restore — switching an
# element back to its base value re-points at a variant that was never mutated.
DEFAULT_THEME = {
    "palette":       "matugen",          # matugen | gold | matrix
    "animations":    "theme",            # <preset name> | matrix
    "lock":          "base",             # base | matrix
}


def _migrate_theme(state):
    """Materialise state['theme'] from legacy keys. Returns (state, changed)."""
    changed = False
    theme = state.get("theme")
    if not isinstance(theme, dict):
        theme = dict(DEFAULT_THEME)
        # Derive palette from the legacy matugen_enabled flag so the current
        # look is preserved as a selector value (matugen on -> matugen mode).
        if state.get("matugen_enabled") is False:
            theme["palette"] = "gold"
        else:
            theme["palette"] = "matugen"
        state["theme"] = theme
        changed = True
    else:
        # Drop selectors retired during standalone/public-alpha cleanup.
        for obsolete in ("wallpaper", "waybar_layout", "wlogout", "terminal", "boot"):
            if obsolete in theme:
                theme.pop(obsolete)
                changed = True
        for k, v in DEFAULT_THEME.items():
            if k not in theme:
                theme[k] = v
                changed = True
    # Keep the legacy flag in sync with the declarative palette value.
    want = (theme.get("palette") == "matugen")
    if state.get("matugen_enabled") != want:
        state["matugen_enabled"] = want
        changed = True
    return state, changed


def get_theme(key, default=None):
    """Read a theme selector value (with DEFAULT_THEME fallback)."""
    theme = load_state().get("theme", {})
    if key in theme:
        return theme[key]
    return DEFAULT_THEME.get(key, default)


def set_theme(key, value):
    """Write a theme selector value and persist. Keeps matugen_enabled synced."""
    state = load_state()
    theme = state.setdefault("theme", dict(DEFAULT_THEME))
    theme[key] = value
    if key == "palette":
        state["matugen_enabled"] = (value == "matugen")
    save_state(state)


def load_state():
    """Load HyprConfig state (migrating the declarative theme{} block in)."""
    source = STATE_FILE
    migrated_path = False
    if not source.exists() and LEGACY_STATE_FILE.exists():
        source = LEGACY_STATE_FILE
        migrated_path = True
    try:
        state = json.loads(source.read_text())
    except Exception:
        state = {"matugen_enabled": False, "waybar_style": "powerline",
                 "effects_enabled": True}
    state, changed = _migrate_theme(state)
    if changed or migrated_path:
        try:
            save_state(state)
        except Exception:
            pass
    return state


def save_state(state):
    """Save HyprConfig state."""
    atomic_write_text(STATE_FILE, json.dumps(state, indent=2) + "\n")
