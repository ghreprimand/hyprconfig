#!/usr/bin/env bash
# Install HyprConfig for the current user without requiring root.
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
bin_home="${XDG_BIN_HOME:-$HOME/.local/bin}"
app_home="$data_home/hyprconfig"
desktop_home="$data_home/applications"

for command in python3 hyprctl waybar; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Missing required command: %s\n' "$command" >&2
        exit 1
    fi
done

if ! python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" \
        >/dev/null 2>&1; then
    printf '%s\n' 'Missing Python GTK4/libadwaita bindings. See docs/INSTALLATION.md.' >&2
    exit 1
fi

install -d "$app_home" "$bin_home" "$desktop_home"
install -d "$app_home/hyprconfig"
cp -a "$project_dir/src/hyprconfig/." "$app_home/hyprconfig/"

launcher="$bin_home/hyprconfig"
cat >"$launcher" <<'EOF'
#!/usr/bin/env bash
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
export PYTHONPATH="$data_home/hyprconfig${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m hyprconfig "$@"
EOF
chmod 0755 "$launcher"

# Remove the launcher installed by pre-release versions that included the
# retired Digital Rain login hook.
rm -f -- "$bin_home/hyprconfig-wallpaper-startup"

install -m 0644 \
    "$project_dir/packaging/io.github.ghreprimand.hyprconfig.desktop" \
    "$desktop_home/io.github.ghreprimand.hyprconfig.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$desktop_home" >/dev/null 2>&1 || true
fi

printf 'Installed HyprConfig to %s\n' "$app_home"
printf 'Run: %s\n' "$launcher"
case ":$PATH:" in
    *":$bin_home:"*) ;;
    *) printf 'Add %s to PATH before running hyprconfig.\n' "$bin_home" ;;
esac
