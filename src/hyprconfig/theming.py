"""HyprConfig — Theming page with matugen Material You integration."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

import subprocess
import shutil
import json
import os
import time
from pathlib import Path

from .parser import (hyprctl_set, persist_borders, load_state, save_state,
                     get_theme, set_theme)
from . import matrix_theme
from .paths import FISH_THEME, RESTART_WAYBAR_SCRIPT, ROFI_COLORS, WAYBAR_DIR
from .safe_io import atomic_write_text, remove_with_backup

CLASSIC_GOLD = {
    'active_border': 'rgba(ff8c00ff) rgba(ffd700ff) 45deg',
    'inactive_border': 'rgba(595959aa)',
}

WAYBAR_THEME = WAYBAR_DIR / 'theme.css'

# Static classic gold RGB triples for waybar @define-color fallbacks.
CLASSIC_GOLD_RGB = {
    'accent':  (255, 140, 0),    # #ff8c00
    'accent2': (255, 215, 0),    # #ffd700
    'accent_hi': (255, 228, 93), # #ffe44d (hover/lighter)
    'surface': (10, 10, 20),     # #0a0a14
    'surface_alt': (20, 20, 42), # #14142a
    'on_surface': (205, 214, 244),
}


def write_rofi_colors(colors_dict):
    """Write full color scheme to rofi's colors.rasi."""
    atomic_write_text(
        ROFI_COLORS,
        f"/* Dynamic colors — managed by HyprConfig theming */\n"
        f"* {{\n"
        f"    hc-bg:      {colors_dict['bg']}e6;\n"
        f"    hc-bg-alt:  {colors_dict['bg_alt']}cc;\n"
        f"    hc-fg:      {colors_dict['fg']};\n"
        f"    hc-fg-dim:  {colors_dict['fg_dim']};\n"
        f"    hc-accent:  {colors_dict['accent']};\n"
        f"    hc-accent2: {colors_dict['accent2']};\n"
        f"    hc-urgent:  #f38ba8;\n"
        f"}}\n"
    )


def _hex_to_rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def write_waybar_theme(colors_dict):
    """Write waybar GTK3 @define-color tokens to theme.css.

    GTK3 CSS has no var() with custom properties, but @define-color plus
    @token references work everywhere waybar runs. style.css files migrated
    to use @accent / @accent2 / @surface tokens pick up wallpaper-derived
    colors automatically once they @import "theme.css".
    """
    def rgb(role, fallback_key):
        v = colors_dict.get(role)
        try:
            return _hex_to_rgb(v) if v else CLASSIC_GOLD_RGB[fallback_key]
        except Exception:
            return CLASSIC_GOLD_RGB[fallback_key]

    accent = rgb('accent', 'accent')
    accent2 = rgb('accent2', 'accent2')
    accent_hi = tuple(min(255, int(c + (255 - c) * 0.35)) for c in accent2)
    surface = rgb('surface', 'surface')
    surface_alt = rgb('bg_alt', 'surface_alt')
    on_surface = rgb('fg', 'on_surface')

    atomic_write_text(
        WAYBAR_THEME,
        f"/* Dynamic colors — managed by HyprConfig theming */\n"
        f"@define-color bar-bg rgba({surface[0]}, {surface[1]}, {surface[2]}, 0.85);\n"
        f"@define-color main-bg #{surface_alt[0]:02x}{surface_alt[1]:02x}{surface_alt[2]:02x};\n"
        f"@define-color main-fg #{on_surface[0]:02x}{on_surface[1]:02x}{on_surface[2]:02x};\n"
        f"@define-color accent #{accent[0]:02x}{accent[1]:02x}{accent[2]:02x};\n"
        f"@define-color accent2 #{accent2[0]:02x}{accent2[1]:02x}{accent2[2]:02x};\n"
        f"@define-color accent-hi #{accent_hi[0]:02x}{accent_hi[1]:02x}{accent_hi[2]:02x};\n"
        f"@define-color wb-act-bg #{accent2[0]:02x}{accent2[1]:02x}{accent2[2]:02x};\n"
        f"@define-color wb-act-fg #{surface[0]:02x}{surface[1]:02x}{surface[2]:02x};\n"
        f"@define-color wb-hvr-bg #{accent_hi[0]:02x}{accent_hi[1]:02x}{accent_hi[2]:02x};\n"
        f"@define-color wb-hvr-fg #{surface[0]:02x}{surface[1]:02x}{surface[2]:02x};\n"
    )


def write_fish_colors(colors_dict):
    """Export palette variables for fish prompts that opt into HyprConfig."""
    def hexstr(role, fallback):
        v = colors_dict.get(role)
        return v.lstrip('#') if v else fallback

    gateway_fg = hexstr('accent2', 'ffd700')
    id_bg = hexstr('accent', 'ff8c00')
    pwd_fg = hexstr('on_surface', 'ffcf6b')
    git_fg = hexstr('accent2', 'ffd700')
    git_dirty = hexstr('tertiary', 'ff9e3d')
    updates_fg = hexstr('accent2', 'ffd700')
    prompt = hexstr('accent', 'ffaa00')

    atomic_write_text(
        FISH_THEME,
        "# Dynamic palette override — managed by HyprConfig theming.\n"
        "# Prompts may consume these globals; HyprConfig does not replace your prompt.\n"
        f"set -g hyprconfig_color_gateway_fg {gateway_fg}\n"
        f"set -g hyprconfig_color_id_bg      {id_bg}\n"
        f"set -g hyprconfig_color_pwd_fg     {pwd_fg}\n"
        f"set -g hyprconfig_color_git_fg     {git_fg}\n"
        f"set -g hyprconfig_color_git_dirty  {git_dirty}\n"
        f"set -g hyprconfig_color_updates_fg {updates_fg}\n"
        f"set -g hyprconfig_color_prompt     {prompt}\n"
    )


def restart_waybar():
    """Replace every Waybar instance with one session-owned instance."""
    try:
        if RESTART_WAYBAR_SCRIPT.exists():
            subprocess.Popen(['bash', str(RESTART_WAYBAR_SCRIPT)], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        for unit in ('waybar-ipc-watchdog.timer', 'waybar-ipc-watchdog.service',
                     'waybar.service', 'waybar-ipc-restart.service',
                     'hyde-Hyprland-bar.service'):
            subprocess.run(['systemctl', '--user', 'stop', unit],
                           capture_output=True, timeout=5)
        subprocess.run(['pkill', '-TERM', '-u', str(os.getuid()), '-x', 'waybar'],
                       capture_output=True, timeout=5)
        for _ in range(20):
            if subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'waybar'],
                              capture_output=True).returncode != 0:
                break
            time.sleep(0.05)
        subprocess.Popen(['waybar'], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def apply_matugen_palette(colors):
    """Apply a matugen color map to all themed surfaces (no GTK side-effects).

    Shared by the ThemingPage UI path and regenerate_theme_from_wallpaper so
    wallpaper changes keep every surface in sync. Writes Hyprland border
    colors live + persists them, writes rofi/waybar/fish theme files, and
    restarts waybar to pick up the new CSS.
    """
    color_map = colors.get('colors', {})

    def get_dark(role, fallback):
        entry = color_map.get(role, {})
        return entry.get('dark', {}).get('color', fallback)

    primary = get_dark('primary', '#ff8c00')
    secondary = get_dark('secondary', '#ffd700')
    surface_variant = get_dark('surface_variant', '#595959')

    p_hex = primary.lstrip('#')
    s_hex = secondary.lstrip('#')
    sv_hex = surface_variant.lstrip('#')

    active_border = f"rgba({p_hex}ff) rgba({s_hex}ff) 45deg"
    inactive_border = f"rgba({sv_hex}aa)"

    hyprctl_set('general:col.active_border', active_border)
    hyprctl_set('general:col.inactive_border', inactive_border)
    persist_borders(active_border, inactive_border)

    surface = get_dark('surface', '#0a0a14')
    surface_container = get_dark('surface_container', '#141420')
    on_surface = get_dark('on_surface', '#cdd6f4')
    on_surface_var = get_dark('on_surface_variant', '#a6adc8')
    tertiary = get_dark('tertiary', '#ff9e3d')

    palette = {
        'bg': surface,
        'bg_alt': surface_container,
        'fg': on_surface,
        'fg_dim': on_surface_var,
        'accent': primary,
        'accent2': secondary,
        'tertiary': tertiary,
    }
    write_rofi_colors(palette)
    write_waybar_theme(palette)
    write_fish_colors(palette)
    # NOTE: waybar CSS is regenerated above, but the restart is intentionally
    # manual (Theming page "Restart Waybar" button). Auto-restarting here raced
    # the systemd unit and crashed the bar on every palette change.
    return palette


def regenerate_theme_from_wallpaper():
    """Regenerate full theme (hypr/rofi/waybar/fish) from current wallpaper.

    Public entry point so other HyprConfig pages (e.g. wallpaper apply) can
    trigger a theme refresh without the GTK UI. Reads the first monitor's
    wallpaper from swww query, runs matugen, and applies the result.
    Returns True on success, False otherwise.
    """
    try:
        r = subprocess.run(['swww', 'query'], capture_output=True, text=True, timeout=3)
        if r.returncode != 0:
            return False
        wallpaper = None
        for line in r.stdout.splitlines():
            if 'image:' in line:
                wallpaper = line.split('image:')[-1].strip()
                break
        if not wallpaper or not Path(wallpaper).exists():
            return False
        r = subprocess.run(
            ['matugen', 'image', wallpaper, '--json', 'hex',
             '--dry-run', '--source-color-index', '0'],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            return False
        colors = json.loads(r.stdout)
        apply_matugen_palette(colors)
        return True
    except Exception:
        return False


GOLD_PALETTE = {
    'bg': '#0a0a14',
    'bg_alt': '#14142a',
    'fg': '#cdd6f4',
    'fg_dim': '#a6adc8',
    'accent': '#ffd700',
    'accent2': '#ff8c00',
    'tertiary': '#ff9e3d',
}


def apply_gold_palette():
    """Apply the static Classic Gold palette to every themed surface.

    Module-level twin of ThemingPage._apply_gold so the declarative theme
    registry (matrix_theme.py) can select the gold mode without the GTK UI.
    Writes hypr borders (live + persisted), rofi/waybar theme files, and
    removes the matugen fish override so the static palette wins.
    """
    hyprctl_set('general:col.active_border', CLASSIC_GOLD['active_border'])
    hyprctl_set('general:col.inactive_border', CLASSIC_GOLD['inactive_border'])
    persist_borders(CLASSIC_GOLD['active_border'], CLASSIC_GOLD['inactive_border'])
    write_rofi_colors(GOLD_PALETTE)
    write_waybar_theme(GOLD_PALETTE)
    try:
        remove_with_backup(FISH_THEME)
    except Exception:
        pass
    return GOLD_PALETTE



class ThemingPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp(maximum_size=700)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        # Header
        hdr = Gtk.Label(label="Theming", css_classes=['page-header'])
        hdr.set_halign(Gtk.Align.START)
        content.append(hdr)
        sub = Gtk.Label(
            label="Generate colors from your wallpaper or use the static classic gold theme.",
            css_classes=['page-subheader']
        )
        sub.set_halign(Gtk.Align.START)
        sub.set_wrap(True)
        content.append(sub)

        # ─── Matugen Toggle ───
        matugen_group = Adw.PreferencesGroup(title="Material You")

        self.matugen_installed = self._check_matugen()
        state = load_state()

        if not self.matugen_installed:
            install_row = Adw.ActionRow(
                title="matugen not installed",
                subtitle="Material You color generation requires matugen (Rust tool)"
            )
            install_btn = Gtk.Button(label="Install via cargo", css_classes=['install-btn'])
            install_btn.set_valign(Gtk.Align.CENTER)
            install_btn.connect('clicked', self._on_install_matugen)
            install_row.add_suffix(install_btn)
            self.install_btn = install_btn
            matugen_group.add(install_row)

        self.matugen_toggle = Adw.SwitchRow(
            title="Material You Theming",
            subtitle="Generate border colors from current wallpaper"
        )
        self.matugen_toggle.set_active(state.get('matugen_enabled', False))
        self.matugen_toggle.set_sensitive(self.matugen_installed)
        self.matugen_toggle.connect('notify::active', self._on_matugen_toggled)
        matugen_group.add(self.matugen_toggle)

        content.append(matugen_group)

        # ─── Current Wallpaper ───
        wall_group = Adw.PreferencesGroup(title="Current Wallpaper")

        self.wallpaper_row = Adw.ActionRow(title="Loading...")
        wall_group.add(self.wallpaper_row)

        generate_btn = Gtk.Button(label="Generate Colors", css_classes=['suggested-action'])
        generate_btn.set_valign(Gtk.Align.CENTER)
        generate_btn.connect('clicked', self._on_generate)
        self.generate_btn = generate_btn
        self.wallpaper_row.add_suffix(generate_btn)

        content.append(wall_group)

        # ─── Color Preview ───
        self.palette_group = Adw.PreferencesGroup(title="Generated Palette")
        self.palette_box = Gtk.FlowBox()
        self.palette_box.set_max_children_per_line(8)
        self.palette_box.set_min_children_per_line(4)
        self.palette_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.palette_box.set_row_spacing(4)
        self.palette_box.set_column_spacing(4)
        self.palette_group.add(self.palette_box)
        content.append(self.palette_group)

        # ─── Static Theme ───
        static_group = Adw.PreferencesGroup(title="Classic Gold (Static)")

        restore_row = Adw.ActionRow(
            title="Restore Classic Gold",
            subtitle="Active: #ff8c00 \u2192 #ffd700 gradient  |  Inactive: #595959"
        )
        restore_btn = Gtk.Button(label="Restore")
        restore_btn.set_valign(Gtk.Align.CENTER)
        restore_btn.connect('clicked', self._on_restore_gold)
        restore_row.add_suffix(restore_btn)
        static_group.add(restore_row)

        content.append(static_group)

        # ─── Theme Elements (declarative selectors) ───
        # Each element is a selector with named values; the look is fully
        # described by these values. Base config files are never mutated.
        self._mtx = matrix_theme
        self._syncing = False
        elem_group = Adw.PreferencesGroup(
            title="Theme Elements",
            description=("Each element is a selector. Material You reproduces your "
                         "current look from the wallpaper; Matrix is another set of "
                         "values. Base config files are never modified \u2014 switching "
                         "back re-selects the base variant."))

        self._element_combos = {}
        for key, el in matrix_theme.visible_elements().items():
            subtitle = el['subtitle']
            if not el.get('live') and el.get('status'):
                subtitle = f"{subtitle}  \u2022  {el['status']}"
            row = Adw.ComboRow(title=el['title'], subtitle=subtitle)
            model = Gtk.StringList()
            for _val, label in el['values']:
                model.append(label)
            row.set_model(model)
            cur = get_theme(key)
            idx = next((i for i, (v, _l) in enumerate(el['values']) if v == cur), 0)
            row.set_selected(idx)
            if not el.get('live'):
                row.set_sensitive(False)
            row.connect('notify::selected', self._on_element_changed, key)
            elem_group.add(row)
            self._element_combos[key] = row

        batch_row = Adw.ActionRow(
            title="Apply a whole look",
            subtitle="Batch-set the live selectors (you can still tweak any row)")
        all_current_btn = Gtk.Button(label="Everything Current")
        all_current_btn.set_valign(Gtk.Align.CENTER)
        all_current_btn.connect('clicked', self._on_all_current)
        all_matrix_btn = Gtk.Button(label="Everything Matrix",
                                    css_classes=['suggested-action'])
        all_matrix_btn.set_valign(Gtk.Align.CENTER)
        all_matrix_btn.connect('clicked', self._on_all_matrix)
        batch_row.add_suffix(all_current_btn)
        batch_row.add_suffix(all_matrix_btn)
        elem_group.add(batch_row)

        content.append(elem_group)

        # --- Waybar lifecycle (manual restart) ---
        wb_group = Adw.PreferencesGroup(title="Waybar")
        wb_row = Adw.ActionRow(
            title="Restart Waybar",
            subtitle="Stops all Waybar instances, then starts exactly one"
        )
        restart_btn = Gtk.Button(label="Restart")
        restart_btn.set_valign(Gtk.Align.CENTER)
        restart_btn.connect('clicked', self._on_restart_waybar)
        wb_row.add_suffix(restart_btn)
        wb_group.add(wb_row)
        content.append(wb_group)

        clamp.set_child(content)
        scroll.set_child(clamp)
        self.append(scroll)

        # Load wallpaper info
        GLib.idle_add(self._load_wallpaper)

    def _check_matugen(self):
        for path in ['/usr/bin/matugen', '/usr/local/bin/matugen',
                     str(Path.home() / '.cargo' / 'bin' / 'matugen')]:
            if Path(path).exists():
                return True
        return shutil.which('matugen') is not None

    def _load_wallpaper(self):
        try:
            r = subprocess.run(['swww', 'query'], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    if 'image:' in line:
                        path = line.split('image:')[-1].strip()
                        name = Path(path).name
                        self.wallpaper_row.set_title(name)
                        self.wallpaper_row.set_subtitle(path)
                        self._current_wallpaper = path
                        return False
            self.wallpaper_row.set_title("No wallpaper detected")
        except Exception:
            self.wallpaper_row.set_title("swww not running")
        return False

    def _on_install_matugen(self, btn):
        btn.set_label("Installing...")
        btn.set_sensitive(False)

        def do_install():
            try:
                subprocess.run(
                    ['cargo', 'install', 'matugen'],
                    capture_output=True, timeout=600
                )
                GLib.idle_add(self._post_install, True)
            except Exception:
                GLib.idle_add(self._post_install, False)

        import threading
        threading.Thread(target=do_install, daemon=True).start()

    def _post_install(self, success):
        if success and self._check_matugen():
            self.matugen_installed = True
            self.matugen_toggle.set_sensitive(True)
            self.install_btn.set_label("Installed \u2713")
        else:
            self.install_btn.set_label("Install failed")
            self.install_btn.set_sensitive(True)
        return False

    def _on_matugen_toggled(self, row, pspec):
        if getattr(self, '_syncing', False):
            return
        enabled = row.get_active()
        # Route through the declarative selector so palette stays single-source.
        self._mtx.set_element('palette', 'matugen' if enabled else 'gold')
        if enabled:
            # refresh preview swatches from the freshly generated palette
            self._on_generate(None)
        if hasattr(self, '_element_combos'):
            self._resync_combos()

    def _on_generate(self, btn):
        if not self.matugen_installed:
            return

        wallpaper = getattr(self, '_current_wallpaper', None)
        if not wallpaper:
            return

        if btn:
            btn.set_label("Generating...")
            btn.set_sensitive(False)

        def do_generate():
            try:
                r = subprocess.run(
                    ['matugen', 'image', wallpaper, '--json', 'hex',
                     '--dry-run', '--source-color-index', '0'],
                    capture_output=True, text=True, timeout=30
                )
                if r.returncode == 0:
                    colors = json.loads(r.stdout)
                    GLib.idle_add(self._apply_matugen_colors, colors)
            except Exception:
                pass
            if btn:
                GLib.idle_add(lambda: (btn.set_label("Generate Colors"), btn.set_sensitive(True)))

        import threading
        threading.Thread(target=do_generate, daemon=True).start()

    def _apply_matugen_colors(self, colors):
        """Apply matugen-generated colors to every themed surface."""
        try:
            palette = apply_matugen_palette(colors)

            # Show palette preview — flatten to simple {role: color} dict
            color_map = colors.get('colors', {})
            flat = {role: color_map.get(role, {}).get('dark', {}).get('color', '')
                    for role in color_map}
            self._show_palette(flat)
        except Exception:
            pass
        return False

    def _show_palette(self, colors):
        """Display color swatches."""
        # Clear existing
        while True:
            child = self.palette_box.get_first_child()
            if child is None:
                break
            self.palette_box.remove(child)

        # Add swatches
        for role in ['primary', 'secondary', 'tertiary', 'error',
                     'surface', 'surface_variant', 'on_surface',
                     'primary_container', 'secondary_container']:
            color = colors.get(role)
            if color:
                swatch = Gtk.Box(css_classes=['color-swatch'])
                css = Gtk.CssProvider()
                css.load_from_string(
                    f".color-swatch {{ background-color: {color}; }}")
                swatch.get_style_context().add_provider(
                    css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)

                swatch.set_tooltip_text(f"{role}: {color}")
                self.palette_box.append(swatch)

    def _on_restart_waybar(self, btn):
        restart_waybar()
        btn.set_label("Restarted \u2713")
        btn.set_sensitive(False)
        GLib.timeout_add(1500, lambda: (btn.set_label("Restart"), btn.set_sensitive(True)))

    def _on_restore_gold(self, btn):
        self._mtx.set_element('palette', 'gold')
        if hasattr(self, '_element_combos'):
            self._resync_combos()
        btn.set_label("Restored \u2713")
        btn.set_sensitive(False)
        GLib.timeout_add(1500, lambda: (btn.set_label("Restore"), btn.set_sensitive(True)))

    def _apply_gold(self):
        # Delegates to the module-level apply_gold_palette so the same code path
        # serves both the UI button and the declarative theme registry.
        apply_gold_palette()
        # waybar theme.css is rewritten above; restart is manual to avoid the
        # supervised-unit crash. Use the "Restart Waybar" button on this page.

    # ─── Declarative theme-element selectors ───

    def _on_element_changed(self, row, pspec, key):
        if getattr(self, '_syncing', False):
            return
        el = self._mtx.ELEMENTS[key]
        idx = row.get_selected()
        if idx < 0 or idx >= len(el['values']):
            return
        value = el['values'][idx][0]
        self._mtx.set_element(key, value)
        if key == 'palette':
            self._sync_palette_switch(value)

    def _on_all_matrix(self, btn):
        self._mtx.set_all_matrix()
        self._resync_combos()
        self._flash(btn, "Applied \u2713")

    def _on_all_current(self, btn):
        self._mtx.set_all_current()
        self._resync_combos()
        self._flash(btn, "Applied \u2713")

    def _resync_combos(self):
        """Reflect current selector values into every combo + the legacy switch."""
        self._syncing = True
        try:
            for key, combo in self._element_combos.items():
                el = self._mtx.ELEMENTS[key]
                cur = get_theme(key)
                idx = next((i for i, (v, _l) in enumerate(el['values']) if v == cur), 0)
                combo.set_selected(idx)
        finally:
            self._syncing = False
        self._sync_palette_switch(get_theme('palette'))

    def _sync_palette_switch(self, palette_value):
        self._syncing = True
        try:
            self.matugen_toggle.set_active(palette_value == 'matugen')
        except Exception:
            pass
        finally:
            self._syncing = False

    def _flash(self, btn, label):
        old = btn.get_label()
        btn.set_label(label)
        btn.set_sensitive(False)
        GLib.timeout_add(1500, lambda: (btn.set_label(old), btn.set_sensitive(True)))
