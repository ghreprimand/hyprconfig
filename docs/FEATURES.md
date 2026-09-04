# Feature guide

## Keybindings

Parses `bind*` declarations and variable assignments from Hyprland configuration
files. Entries are grouped from HyDE-style `$d=[group|subgroup]` markers. The UI
supports search, conflict detection, and editing the modifier/key portion of an
existing declaration.

## Effects

Reads live values through `hyprctl getoption`, previews changes with
`hyprctl keyword`, and persists a managed `decoration` block. Supported controls
include rounding, opacity, blur, shadow, and animation presets.

## Waybar

HyprConfig prefers variants in `~/.config/waybar/variants/<name>` and falls back
to bundled variants. Applying one copies its `config.jsonc` and `style.css` into
the active Waybar directory.

Use **Save current setup as a profile**, enter a name and optional description,
then select **Save profile**. The new profile appears above the built-in styles
and is marked active without restarting Waybar. Choose another style and use
**Apply** on the saved profile to restore it later.

Profiles preserve `config.jsonc` (or the extensionless `config`) and `style.css`
verbatim, including comments, multiple bar definitions, monitor selection, and
workspace styling. Applying validates both files before replacing the active
files, creates timestamped backups, and rolls back replacements on write failure.

Profiles are private local snapshots under
`${XDG_CONFIG_HOME:-~/.config}/hyprconfig/waybar-profiles/<id>/`, with private
directory and file permissions. They are not bundled, uploaded, or added to the
source repository. Names are display labels; generated IDs determine paths.
Each save creates a separate snapshot, even when a name is reused.

Only the two active files are captured. Imported CSS (including `theme.css`),
included configuration files, scripts, fonts, and icons stay shared on the device.
Profiles that reference those files require them to remain available. Theme
changes continue to affect profiles that import the shared theme. These are
local layout snapshots, not portable theme bundles. Treat exported copies as
personal dotfiles: they can contain device identifiers, paths, and commands.

Restarting Waybar stops known systemd/HyDE owners, terminates every remaining
Waybar process, serializes concurrent requests, and starts one instance. Logs
are stored under `${XDG_STATE_HOME:-~/.local/state}/hyprconfig/waybar.log`.

## Theming

Material You runs `matugen` against the first wallpaper reported by `swww`.
HyprConfig then updates Hyprland borders, Rofi variables, Waybar GTK colors,
Dunst overrides, and opt-in Fish variables. Classic Gold and Matrix Green are
static alternatives.

## Displays

Lists monitors from `hyprctl monitors -j`, applies scale changes live, and can
persist them to `monitors.conf`.

## Wallpapers

Indexes common image formats below the configured wallpaper directory, creates
GTK thumbnails incrementally, applies images through `swww`, and can generate a
per-monitor `wallpapers.sh` startup script.

## Matrix elements

Matrix palette mode is functional. Animation and lock-screen selectors appear
only when their expected local variant files exist. Unsupported integrations
are omitted instead of displaying inactive placeholders.
