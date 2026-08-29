# Roadmap

## 0.1 — Private extraction

- [x] Extract the application into a standalone repository
- [x] Rename the project to HyprConfig
- [x] Add XDG-aware paths and legacy state migration
- [x] Bundle Waybar fallback variants
- [x] Add installer, documentation, CI, and lightweight project policies
- [x] Consolidate Waybar restarts to one process

## 0.2 — Portable alpha

- [x] Parse recursive Hyprland `source` graphs
- [x] Support monolithic `hyprland.conf`
- [x] Add capability detection for optional theme and wallpaper controls
- [x] Back up and validate configuration before atomic replacement
- [ ] Move optional theme elements behind an integration interface
- [x] Add a supported-environment matrix
- [ ] Add screenshots

## 0.3 — Public alpha candidate

- [x] Resolve licenses for all bundled Waybar assets
- [x] License the project under GPL-3.0-only
- [x] Expand parser and write-path tests
- [ ] Add structured logging and user-visible errors
- [x] Test fresh installation with isolated XDG directories

## 1.0 — Stable

- [ ] Publish a documented compatibility contract
- [ ] Provide migration guarantees for state and managed blocks
- [ ] Package for at least one distribution repository
- [ ] Complete accessibility and localization review
