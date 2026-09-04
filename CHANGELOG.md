# Changelog

All notable changes will be documented here. This project follows Keep a
Changelog conventions and intends to use semantic versioning after the first
public release.

## [Unreleased]

### Added

- Local Waybar profiles: save and restore the current layout and styling,
  including multiple bars and per-monitor workspace indicators, from the Waybar page
- Standalone HyprConfig repository and source package
- XDG-aware path configuration and environment overrides
- Migration from the former `hyperconfig` state directory
- Bundled fallback Waybar variants
- Generic, serialized single-instance Waybar restart routine
- User installer, uninstaller, tests, CI, and documentation suite
- GPL-3.0-only project license and third-party license notices
- Recursive stock/split Hyprland configuration discovery
- Recoverable atomic configuration writes and managed Hyprland fragment
- Sanitized application screenshot and documented compatibility matrix

### Changed

- Validate both Waybar files before applying a style, retain backups, and roll
  back file replacements if a write fails; refresh all card buttons after selection
- Standardized all product-facing references on the `HyprConfig` name
- Removed personal monitor mappings and absolute home-directory paths
- Replaced system-specific public labels with generic terminology
- Made bundled Waybar layouts hardware-neutral and optional-command aware
- Replaced generic governance boilerplate with lightweight project policies

### Removed

- Digital Rain wallpaper mode and its font-derived carrier assets
