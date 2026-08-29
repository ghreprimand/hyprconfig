# Configuration

HyprConfig intentionally works with existing text files instead of maintaining
a separate generated configuration tree.

## Environment overrides

| Variable | Default | Purpose |
|---|---|---|
| `XDG_CONFIG_HOME` | `~/.config` | User configuration root |
| `XDG_DATA_HOME` | `~/.local/share` | User data root |
| `HYPRCONFIG_HYPR_DIR` | `$XDG_CONFIG_HOME/hypr` | Hyprland configuration directory |
| `HYPRCONFIG_WAYBAR_DIR` | `$XDG_CONFIG_HOME/waybar` | Waybar configuration directory |
| `HYPRCONFIG_WALLPAPER_DIR` | `~/Pictures/walls` | Wallpaper library |
| `HYPRCONFIG_WAYBAR_BIN` | command named `waybar` | Waybar executable used on restart |

## Hyprland discovery

HyprConfig starts at `hyprland.conf` and recursively follows `source =` entries,
including glob patterns. This supports a stock monolithic file and split layouts
such as:

- `keybindings.conf`
- `userprefs.conf`
- `monitors.conf`
- `animations.conf`

Set `HYPRCONFIG_HYPR_DIR` when the entry point lives somewhere else. If no
`hyprland.conf` exists, keybinding discovery falls back to `keybindings.conf`
and `userprefs.conf`.

Persistent effects, borders, and monitor settings are stored in
`hyprconfig.conf`. HyprConfig adds one `source =` line to `hyprland.conf` when
the managed fragment is first needed; it does not replace existing decoration,
general, or monitor blocks.

## State

State is JSON stored at `~/.config/hyprconfig/state.json`. It records UI choices,
not a copy of the user's complete configuration. On first run, HyprConfig reads
the former `~/.config/hyperconfig/state.json` if the new file does not exist and
writes the migrated state to the new location.

## Managed output

HyprConfig may write:

- decoration and border blocks in `userprefs.conf`
- monitor scale entries in `monitors.conf`
- active Waybar `config.jsonc`, `style.css`, and `theme.css`
- Rofi color variables in `colors.rasi`
- Dunst's `zzz-hyprconfig-matrix.conf` palette drop-in
- opt-in Fish variables in `zz_hyprconfig_theme.fish`
- `wallpapers.sh`

Keep these files under version control. The write paths are designed to be
repeatable. Each file is written through an atomic same-directory replacement,
and an existing regular file is copied into the timestamped tree under
`~/.config/hyprconfig/backups/` first. HyprConfig refuses to replace symbolic
links through ordinary managed-file writes.
