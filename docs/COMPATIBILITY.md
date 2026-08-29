# Compatibility

## Supported public-alpha target

HyprConfig's initial supported environment is:

| Component | Supported scope |
|---|---|
| Operating system | Arch Linux and Arch-based systems |
| Desktop session | A running Hyprland session |
| Python | 3.10 or newer |
| UI runtime | GTK 4, libadwaita 1, and PyGObject |
| Status bar | Waybar |
| Hyprland configuration | Stock monolithic `hyprland.conf`, relative or absolute `source` files, and source globs |

CI tests Python 3.10, 3.12, and 3.14. Other Linux distributions can work when
they provide the required runtime packages, but are community-supported until
their installation and behavior are tested.

## Optional integrations

HyprConfig detects optional commands at runtime. Missing optional software does
not prevent the core application from launching.

| Integration | Command | Behavior when unavailable |
|---|---|---|
| Wallpaper management | `swww` | Wallpaper apply and save controls are disabled |
| Material You colors | `matugen` | Material You generation is unavailable |
| Notifications | `dunstctl` | Dunst-specific palette application is skipped |
| Waybar actions | `rofi`, `wlogout`, `foot`, `btop`, `pavucontrol`, `swayosd-client`, `nm-connection-editor` | The affected click action does nothing |

Bundled Waybar configurations do not require NVIDIA tools or private helper
scripts.

## Configuration safety contract

- HyprConfig follows the `source` graph reachable from `hyprland.conf` when it
  reads keybindings.
- Persistent visual and display settings are isolated in
  `~/.config/hypr/hyprconfig.conf`.
- HyprConfig adds one `source` line to `hyprland.conf` when managed settings are
  first saved.
- Replaced regular files receive timestamped copies under
  `~/.config/hyprconfig/backups/`.
- Replacements are written to a temporary file and atomically renamed.
- HyprConfig refuses to replace symbolic links and non-file targets.

The public alpha does not promise compatibility with generated configuration
trees that are rewritten concurrently by another program. Keep dotfiles under
version control and review the managed fragment after upgrading.

## Reporting another environment

Compatibility reports should include the distribution, Hyprland version,
Waybar version, Python version, and whether the configuration is monolithic or
split across sourced files. Do not attach private configuration without first
removing usernames, paths, hostnames, tokens, and command arguments.
