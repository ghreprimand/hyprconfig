# Installation

## Requirements

Required:

- Linux running a Hyprland session
- Python 3.10 or newer
- GTK 4, libadwaita, and their Python GObject bindings
- `hyprctl`
- Waybar for the Waybar page

Optional features:

| Feature | Commands or libraries |
|---|---|
| Material You | `matugen` |
| Wallpapers | `swww`, GdkPixbuf image loaders |
| Rofi palette export | `rofi` and a theme importing `colors.rasi` |
| Notifications | `dunstctl` |
| Bundled Waybar click actions | `rofi`, `wlogout`, `foot`, `btop`, `pavucontrol`, `swayosd-client`, `nm-connection-editor` |

Missing optional click-action commands are ignored. Bundled layouts do not
assume NVIDIA hardware or private helper scripts.

## User installation

```bash
./install.sh
```

The installer is rootless. It copies the Python package into
`${XDG_DATA_HOME:-~/.local/share}/hyprconfig`, installs launchers into
`${XDG_BIN_HOME:-~/.local/bin}`, and installs a desktop entry.

The installer does not modify Hyprland startup files or delete the former
`hyperconfig` installation. State is migrated lazily when HyprConfig first runs.
The retired `hyprconfig-wallpaper-startup` launcher is removed during upgrade.

## Hyprland keybinding

Add a binding to your Hyprland configuration:

```ini
bindd = SUPER, slash, Open HyprConfig, exec, hyprconfig
```

## Development launch

```bash
./scripts/dev
```

This sets `PYTHONPATH` to the repository's `src` directory and does not install
or copy anything.

## Uninstallation

```bash
./uninstall.sh
```

This removes installed program files but preserves `~/.config/hyprconfig`.
To remove saved state as well:

```bash
./uninstall.sh --purge
```

`--purge` is irreversible unless the state directory is backed up.
