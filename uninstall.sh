#!/usr/bin/env bash
# Remove the per-user HyprConfig installation. Configuration is kept by default.
set -euo pipefail

data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
bin_home="${XDG_BIN_HOME:-$HOME/.local/bin}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"

rm -rf -- "$data_home/hyprconfig"
rm -f -- "$bin_home/hyprconfig" "$bin_home/hyprconfig-wallpaper-startup"
rm -f -- "$data_home/applications/io.github.ghreprimand.hyprconfig.desktop"

if [ "${1:-}" = "--purge" ]; then
    rm -rf -- "$config_home/hyprconfig"
    printf '%s\n' 'Removed HyprConfig and its saved state.'
else
    printf 'Removed HyprConfig. Preserved state in %s\n' "$config_home/hyprconfig"
fi
