#!/usr/bin/env bash
# Stop every known Waybar owner and leave exactly one process running.
set -u

waybar_bin="${HYPRCONFIG_WAYBAR_BIN:-$(command -v waybar 2>/dev/null || true)}"
if [ -z "$waybar_bin" ]; then
    printf '%s\n' 'hyprconfig: waybar is not installed' >&2
    exit 127
fi

runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$UID}"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/hyprconfig"
lock_file="$runtime_dir/hyprconfig-waybar.lock"
log_file="$state_dir/waybar.log"

mkdir -p "$state_dir"
exec 9>"$lock_file"
flock -x 9

# Manual invocations may not inherit the compositor environment. Import only
# the display keys Waybar needs from the systemd user manager.
while IFS='=' read -r key value; do
    case "$key" in
        DISPLAY|WAYLAND_DISPLAY|HYPRLAND_INSTANCE_SIGNATURE|XDG_CURRENT_DESKTOP|XDG_SESSION_TYPE)
            if [ -z "${!key:-}" ]; then
                export "$key=$value"
            fi
            ;;
    esac
done < <(systemctl --user show-environment 2>/dev/null)

for unit in waybar-ipc-watchdog.timer waybar-ipc-watchdog.service \
            waybar.service waybar-ipc-restart.service \
            hyde-Hyprland-bar.service hyprconfig-waybar.service; do
    systemctl --user stop "$unit" >/dev/null 2>&1 || true
done

stop_all() {
    pkill -TERM -u "$UID" -x waybar >/dev/null 2>&1 || true
    for _ in {1..20}; do
        pgrep -u "$UID" -x waybar >/dev/null 2>&1 || return 0
        sleep 0.05
    done
    pkill -KILL -u "$UID" -x waybar >/dev/null 2>&1 || true
}

start_one() {
    "$waybar_bin" >>"$log_file" 2>&1 &
    waybar_pid=$!
    sleep 0.75
    [ -d "/proc/$waybar_pid" ]
}

stop_all
if ! start_one; then
    printf '%s\n' "hyprconfig: Waybar failed to start; see $log_file" >&2
    flock -u 9
    exit 1
fi

# A competing supervisor appearing during startup is handled by one retry.
if [ "$(pgrep -u "$UID" -x waybar | wc -l)" -ne 1 ]; then
    stop_all
    if ! start_one || [ "$(pgrep -u "$UID" -x waybar | wc -l)" -ne 1 ]; then
        stop_all
        printf '%s\n' 'hyprconfig: could not establish a single Waybar process' >&2
        flock -u 9
        exit 1
    fi
fi

flock -u 9
wait "$waybar_pid"
