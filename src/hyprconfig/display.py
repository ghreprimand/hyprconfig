"""HyprConfig — Display settings page (monitor scaling)."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

import subprocess
from pathlib import Path

from .parser import ensure_managed_config, hyprctl_monitors
from .paths import MANAGED_CONF
from .safe_io import update_managed_block

SCALE_OPTIONS = ['1.0', '1.25', '1.5', '1.75', '2.0']


class DisplayPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp(maximum_size=750)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(28)
        content.set_margin_bottom(28)

        # Header
        hdr = Gtk.Label(label="Display", css_classes=['page-header'])
        hdr.set_halign(Gtk.Align.START)
        content.append(hdr)
        sub = Gtk.Label(
            label="Adjust monitor scaling. Changes apply live.",
            css_classes=['page-subheader']
        )
        sub.set_halign(Gtk.Align.START)
        content.append(sub)

        # ─── Monitors ───
        self.monitors_group = Adw.PreferencesGroup(title="Monitors")
        content.append(self.monitors_group)

        # ─── Dynamic Scaling Keybind ───
        kb_group = Adw.PreferencesGroup(title="Dynamic Fractional Scaling")

        info_row = Adw.ActionRow(
            title="Zoom In / Out on Focused Monitor",
            subtitle=(
                "Super+= zooms in (higher scale, larger UI)\n"
                "Super+- zooms out (lower scale, more content)\n"
                "Cycles through: 1.0x \u2192 1.25x \u2192 1.5x \u2192 1.75x \u2192 2.0x"
            ),
        )
        kb_group.add(info_row)

        content.append(kb_group)

        # ─── Refresh ───
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect('clicked', lambda b: self._load_monitors())
        btn_box.append(refresh_btn)

        self.save_btn = Gtk.Button(label="Save to Config",
                                   css_classes=['suggested-action', 'apply-btn'])
        self.save_btn.connect('clicked', self._on_save)
        btn_box.append(self.save_btn)

        content.append(btn_box)

        clamp.set_child(content)
        scroll.set_child(clamp)
        self.append(scroll)

        self.monitor_rows = {}
        GLib.idle_add(self._load_monitors)

    def _load_monitors(self):
        # Clear existing rows
        for name, row in list(self.monitor_rows.items()):
            self.monitors_group.remove(row)
        self.monitor_rows.clear()

        monitors = hyprctl_monitors()
        for mon in sorted(monitors, key=lambda m: m.get('x', 0)):
            name = mon.get('name', '?')
            width = mon.get('width', 0)
            height = mon.get('height', 0)
            scale = mon.get('scale', 1.0)
            refresh = mon.get('refreshRate', 0)
            desc = mon.get('description', '')

            # Find connector type
            is_dp = name.startswith('DP-')

            subtitle_parts = [f"{width}x{height}@{refresh:.0f}Hz"]
            if desc:
                # Extract make/model from description
                short_desc = desc.split('(')[0].strip()[:40]
                subtitle_parts.append(short_desc)

            row = Adw.ComboRow(
                title=name,
                subtitle=' — '.join(subtitle_parts),
            )
            row.add_css_class('monitor-name')

            # Scale dropdown
            scale_model = Gtk.StringList()
            current_idx = 0
            for i, s in enumerate(SCALE_OPTIONS):
                scale_model.append(f"{s}x")
                if abs(float(s) - scale) < 0.01:
                    current_idx = i

            row.set_model(scale_model)
            row.set_selected(current_idx)
            row.connect('notify::selected', self._on_scale_changed, name)

            self.monitors_group.add(row)
            self.monitor_rows[name] = row

        return False

    def _on_scale_changed(self, row, pspec, monitor_name):
        idx = row.get_selected()
        if idx < len(SCALE_OPTIONS):
            new_scale = SCALE_OPTIONS[idx]
            # Apply live
            try:
                subprocess.run(
                    ['hyprctl', 'keyword', 'monitor',
                     f"{monitor_name},auto,auto,{new_scale}"],
                    capture_output=True, timeout=3
                )
            except Exception:
                pass

    def _on_save(self, btn):
        """Persist current scale values to HyprConfig's managed fragment."""
        monitors = hyprctl_monitors()
        lines = []
        for mon in monitors:
            name = mon.get('name', '')
            if not name:
                continue
            scale = mon.get('scale', 1.0)
            if name in self.monitor_rows:
                idx = self.monitor_rows[name].get_selected()
                if idx < len(SCALE_OPTIONS):
                    new_scale = SCALE_OPTIONS[idx]
                else:
                    new_scale = f"{scale}"
                width = mon.get('width', 0)
                height = mon.get('height', 0)
                refresh = mon.get('refreshRate', 60)
                x = mon.get('x', 0)
                y = mon.get('y', 0)
                mode = f"{width}x{height}@{refresh:.3f}" if width and height else "preferred"
                lines.append(f"monitor = {name}, {mode}, {x}x{y}, {new_scale}")

        if lines:
            ensure_managed_config()
            update_managed_block(MANAGED_CONF, "monitors", "\n".join(lines))

        btn.set_label("Saved \u2713")
        btn.set_sensitive(False)
        GLib.timeout_add(1500, lambda: (btn.set_label("Save to Config"),
                                        btn.set_sensitive(True)))
