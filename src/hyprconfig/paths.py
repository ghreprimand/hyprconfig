"""Filesystem locations used by HyprConfig.

Every user-facing location honors XDG variables or an explicit HYPRCONFIG_*
override so development and testing never need to touch a real desktop.
"""

import os
from pathlib import Path


HOME = Path.home()
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share"))

APP_DIR = XDG_CONFIG_HOME / "hyprconfig"
STATE_FILE = APP_DIR / "state.json"
BACKUP_DIR = APP_DIR / "backups"
LEGACY_STATE_FILE = XDG_CONFIG_HOME / "hyperconfig" / "state.json"

HYPR_DIR = Path(os.environ.get("HYPRCONFIG_HYPR_DIR", XDG_CONFIG_HOME / "hypr"))
HYPRLAND_CONF = HYPR_DIR / "hyprland.conf"
MANAGED_CONF = HYPR_DIR / "hyprconfig.conf"
KEYBINDINGS_CONF = HYPR_DIR / "keybindings.conf"
USERPREFS_CONF = HYPR_DIR / "userprefs.conf"

WAYBAR_DIR = Path(os.environ.get("HYPRCONFIG_WAYBAR_DIR", XDG_CONFIG_HOME / "waybar"))
WAYBAR_VARIANTS_DIR = WAYBAR_DIR / "variants"
ROFI_COLORS = XDG_CONFIG_HOME / "rofi" / "colors.rasi"
FISH_THEME = XDG_CONFIG_HOME / "fish" / "conf.d" / "zz_hyprconfig_theme.fish"

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
BUILTIN_VARIANTS_DIR = DATA_DIR / "waybar" / "variants"
RESTART_WAYBAR_SCRIPT = DATA_DIR / "restart-waybar.sh"

WALLPAPERS_SH = HYPR_DIR / "wallpapers.sh"
_wallpaper_override = os.environ.get("HYPRCONFIG_WALLPAPER_DIR")
if _wallpaper_override:
    WALLPAPER_DIR = Path(_wallpaper_override).expanduser()
else:
    _candidates = (HOME / "Pictures" / "walls", HOME / "Pictures" / "Wallpapers")
    WALLPAPER_DIR = next((path for path in _candidates if path.exists()), _candidates[0])
