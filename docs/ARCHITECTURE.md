# Architecture

HyprConfig is a single-process GTK4 application. Each navigation page is loaded
on first use and talks directly to local configuration files or desktop command
line tools.

## Modules

| Module | Responsibility |
|---|---|
| `main.py` | Application lifecycle, CSS, sidebar, lazy page loading |
| `paths.py` | XDG-aware paths and environment overrides |
| `safe_io.py` | Timestamped backups and atomic file replacement |
| `parser.py` | Hyprland parsing, writes, state, and `hyprctl` adapters |
| `keybindings.py` | Keybinding browser and editor |
| `effects.py` | Decoration/effect controls |
| `display.py` | Monitor discovery and scaling |
| `waybar_page.py` | Variant selection and activation |
| `theming.py` | Matugen/static palettes and Waybar lifecycle |
| `wallpaper.py` | Wallpaper browser, apply, and persistence |
| `matrix_theme.py` | Declarative cross-surface Matrix theme elements |

## Data flow

```text
GTK page
   ├── parser.py ──> source graph / hyprconfig.conf / state.json
   ├── subprocess ─> hyprctl, swww, matugen, dunstctl
   └── data/ ──────> bundled Waybar variants
```

## Design constraints

- Configuration files remain inspectable and editable outside HyprConfig.
- Live changes and persistence are separate actions where the UI exposes both.
- External processes use argument arrays rather than interpolated shell strings.
- Process matching uses exact names where possible.
- User paths are centralized in `paths.py`.
- Persistent writes use `safe_io.py` and refuse ordinary symlink targets.
- Bundled Waybar variants are fallback data; user variants take precedence.

## Known architectural debt

- Multi-file theme application is not transactional.
- GTK widgets and system adapters are not separated enough for broad unit tests.
- Several optional integrations are represented directly instead of through a
  plugin interface.
