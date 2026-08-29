# Troubleshooting

## `ModuleNotFoundError: No module named 'gi'`

Install your distribution's Python GObject, GTK4, and libadwaita packages. On
Arch Linux these are `python-gobject`, `gtk4`, and `libadwaita`.

## No keybindings appear

HyprConfig currently reads `keybindings.conf` and `userprefs.conf` below the
Hyprland directory. Set `HYPRCONFIG_HYPR_DIR` or create the expected split. A
single-file parser is planned.

## Effects change live but do not survive restart

Use the page's persistence action and confirm `userprefs.conf` is writable and
sourced by the main Hyprland configuration.

## Waybar duplicates

Use HyprConfig's Restart Waybar action. It stops known Waybar user services and
kills remaining exact-name processes before starting one. Inspect:

```bash
pgrep -a -x waybar
systemctl --user status waybar.service hyde-Hyprland-bar.service
```

Logs are written to:

```text
${XDG_STATE_HOME:-~/.local/state}/hyprconfig/waybar.log
```

## Waybar does not return

Verify `WAYLAND_DISPLAY` and `HYPRLAND_INSTANCE_SIGNATURE` are exported to the
systemd user manager and inspect the Waybar log. Override the binary with
`HYPRCONFIG_WAYBAR_BIN` if Waybar is not on `PATH`.

## Material You does nothing

Confirm `matugen` and `swww` are installed, `swww query` reports an existing
image, and the active Waybar style imports `theme.css`.

## Wallpaper library is empty

Set `HYPRCONFIG_WALLPAPER_DIR` to a directory containing PNG, JPEG, WebP, or BMP
files.

## Reset application state

Move the state aside, then restart HyprConfig:

```bash
mv ~/.config/hyprconfig/state.json ~/.config/hyprconfig/state.json.backup
```
