"""HyprConfig — Visual Effects settings page."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from .parser import hyprctl_get, hyprctl_set, persist_decoration, HYPR_DIR

import os
from pathlib import Path

ANIMATIONS_DIR = HYPR_DIR / 'animations'


class EffectsPage(Gtk.Box):
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
        hdr = Gtk.Label(label="Visual Effects", css_classes=['page-header'])
        hdr.set_halign(Gtk.Align.START)
        content.append(hdr)
        sub = Gtk.Label(label="Changes apply live. Click Apply to persist across reboots.",
                        css_classes=['page-subheader'])
        sub.set_halign(Gtk.Align.START)
        sub.set_wrap(True)
        sub.set_xalign(0)
        content.append(sub)

        # ─── Blur ───
        blur_group = Adw.PreferencesGroup(title="Blur")

        self.blur_toggle = Adw.SwitchRow(
            title="Enable Blur",
            subtitle="Gaussian blur behind transparent windows and layers"
        )
        self.blur_toggle.connect('notify::active', self._on_blur_toggled)
        blur_group.add(self.blur_toggle)

        self.blur_size = Adw.SpinRow.new_with_range(1, 20, 1)
        self.blur_size.set_title("Blur Size")
        self.blur_size.set_subtitle("Kernel size (higher = more spread)")
        blur_group.add(self.blur_size)

        self.blur_passes = Adw.SpinRow.new_with_range(1, 6, 1)
        self.blur_passes.set_title("Blur Passes")
        self.blur_passes.set_subtitle("Iterations (higher = smoother but slower)")
        blur_group.add(self.blur_passes)

        content.append(blur_group)

        # ─── Shadow ───
        shadow_group = Adw.PreferencesGroup(title="Shadow")

        self.shadow_toggle = Adw.SwitchRow(
            title="Enable Shadows",
            subtitle="Drop shadows behind windows"
        )
        shadow_group.add(self.shadow_toggle)

        self.shadow_range = Adw.SpinRow.new_with_range(1, 40, 1)
        self.shadow_range.set_title("Shadow Range")
        self.shadow_range.set_subtitle("Size of the shadow (pixels)")
        shadow_group.add(self.shadow_range)

        self.shadow_power = Adw.SpinRow.new_with_range(1, 5, 1)
        self.shadow_power.set_title("Render Power")
        self.shadow_power.set_subtitle("Falloff curve (higher = sharper edge)")
        shadow_group.add(self.shadow_power)

        content.append(shadow_group)

        # ─── Opacity ───
        opacity_group = Adw.PreferencesGroup(title="Window Opacity")

        self.active_opacity = Adw.SpinRow.new_with_range(0.1, 1.0, 0.05)
        self.active_opacity.set_title("Active Window")
        self.active_opacity.set_subtitle("Opacity of the focused window")
        self.active_opacity.set_digits(2)
        opacity_group.add(self.active_opacity)

        self.inactive_opacity = Adw.SpinRow.new_with_range(0.1, 1.0, 0.05)
        self.inactive_opacity.set_title("Inactive Windows")
        self.inactive_opacity.set_subtitle("Opacity of unfocused windows")
        self.inactive_opacity.set_digits(2)
        opacity_group.add(self.inactive_opacity)

        content.append(opacity_group)

        # ─── General ───
        general_group = Adw.PreferencesGroup(title="General")

        self.rounding = Adw.SpinRow.new_with_range(0, 24, 1)
        self.rounding.set_title("Corner Rounding")
        self.rounding.set_subtitle("Radius of window corner rounding (pixels)")
        general_group.add(self.rounding)

        content.append(general_group)

        # ─── Animations ───
        anim_group = Adw.PreferencesGroup(title="Animations")

        self.anim_combo = Adw.ComboRow(title="Animation Preset")
        self.anim_combo.set_subtitle("Select window animation style")
        anim_model = Gtk.StringList()
        self.anim_presets = self._discover_presets()
        for name in self.anim_presets:
            anim_model.append(name)
        self.anim_combo.set_model(anim_model)
        anim_group.add(self.anim_combo)

        content.append(anim_group)

        # ─── Screen Shaders ───
        shader_group = Adw.PreferencesGroup(title="Screen Shaders")

        self.shader_combo = Adw.ComboRow(title="Active Shader")
        self.shader_combo.set_subtitle("Apply a full-screen post-processing effect")
        shader_model = Gtk.StringList()
        self.shader_files = self._discover_shaders()
        for name in self.shader_files:
            shader_model.append(name)
        self.shader_combo.set_model(shader_model)

        # Set current selection
        current_shader = hyprctl_get('decoration:screen_shader')
        if current_shader and current_shader != '[[EMPTY]]':
            for i, name in enumerate(self.shader_files):
                if name != 'Off' and name in str(current_shader):
                    self.shader_combo.set_selected(i)
                    break

        self.shader_combo.connect('notify::selected', self._on_shader_changed)
        shader_group.add(self.shader_combo)

        content.append(shader_group)

        # ─── Quick Toggle Info ───
        toggle_group = Adw.PreferencesGroup(title="Quick Toggle")
        info_row = Adw.ActionRow(
            title="Toggle All Effects",
            subtitle="Super+Ctrl+E toggles blur + shadow + opacity on/off"
        )
        toggle_group.add(info_row)
        content.append(toggle_group)

        # ─── Apply ───
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)

        preview_btn = Gtk.Button(label="Preview")
        preview_btn.connect('clicked', self._on_preview)
        btn_box.append(preview_btn)

        self.apply_btn = Gtk.Button(label="Apply & Save", css_classes=['suggested-action', 'apply-btn'])
        self.apply_btn.connect('clicked', self._on_apply)
        btn_box.append(self.apply_btn)

        content.append(btn_box)

        clamp.set_child(content)
        scroll.set_child(clamp)
        self.append(scroll)

        # Load current values
        self._load_current()

    def _discover_shaders(self):
        shaders_dir = HYPR_DIR / 'shaders'
        names = ['Off']
        if shaders_dir.exists():
            for f in sorted(shaders_dir.iterdir()):
                if f.suffix == '.frag' and f.stem not in ('disable', 'custom', 'wallbash', 'oled-saver'):
                    # Pretty name: blue-light-filter → Blue Light Filter
                    pretty = f.stem.replace('-', ' ').replace('_', ' ').title()
                    names.append(pretty)
        return names

    def _shader_name_to_path(self, name):
        if name == 'Off':
            return str(HYPR_DIR / 'shaders' / 'disable.frag')
        slug = name.lower().replace(' ', '-')
        return str(HYPR_DIR / 'shaders' / f'{slug}.frag')

    def _on_shader_changed(self, row, pspec):
        idx = row.get_selected()
        if idx < len(self.shader_files):
            name = self.shader_files[idx]
            # Always clear first and restore damage tracking
            hyprctl_set('decoration:screen_shader', '[[EMPTY]]')
            hyprctl_set('debug:damage_tracking', '2')
            if name != 'Off':
                path = self._shader_name_to_path(name)
                hyprctl_set('decoration:screen_shader', path)

    def _discover_presets(self):
        presets = ["theme (default)"]
        if ANIMATIONS_DIR.exists():
            for f in sorted(ANIMATIONS_DIR.iterdir()):
                if f.suffix == '.conf' and f.stem != 'theme':
                    presets.append(f.stem)
        return presets

    def _load_current(self):
        # Blur
        v = hyprctl_get('decoration:blur:enabled')
        self.blur_toggle.set_active(bool(v) if v is not None else True)
        v = hyprctl_get('decoration:blur:size')
        self.blur_size.set_value(v if v is not None else 5)
        v = hyprctl_get('decoration:blur:passes')
        self.blur_passes.set_value(v if v is not None else 2)

        # Shadow
        v = hyprctl_get('decoration:shadow:enabled')
        self.shadow_toggle.set_active(bool(v) if v is not None else True)
        v = hyprctl_get('decoration:shadow:range')
        self.shadow_range.set_value(v if v is not None else 10)
        v = hyprctl_get('decoration:shadow:render_power')
        self.shadow_power.set_value(v if v is not None else 3)

        # Opacity
        v = hyprctl_get('decoration:active_opacity')
        self.active_opacity.set_value(v if v is not None else 1.0)
        v = hyprctl_get('decoration:inactive_opacity')
        self.inactive_opacity.set_value(v if v is not None else 1.0)

        # Rounding
        v = hyprctl_get('decoration:rounding')
        self.rounding.set_value(v if v is not None else 8)

    def _on_blur_toggled(self, row, pspec):
        sensitive = row.get_active()
        self.blur_size.set_sensitive(sensitive)
        self.blur_passes.set_sensitive(sensitive)

    def _apply_live(self):
        """Apply all settings live via hyprctl."""
        hyprctl_set('decoration:blur:enabled',
                    'true' if self.blur_toggle.get_active() else 'false')
        hyprctl_set('decoration:blur:size', int(self.blur_size.get_value()))
        hyprctl_set('decoration:blur:passes', int(self.blur_passes.get_value()))
        hyprctl_set('decoration:shadow:enabled',
                    'true' if self.shadow_toggle.get_active() else 'false')
        hyprctl_set('decoration:shadow:range', int(self.shadow_range.get_value()))
        hyprctl_set('decoration:shadow:render_power', int(self.shadow_power.get_value()))
        hyprctl_set('decoration:rounding', int(self.rounding.get_value()))
        hyprctl_set('decoration:active_opacity', f"{self.active_opacity.get_value():.2f}")
        hyprctl_set('decoration:inactive_opacity', f"{self.inactive_opacity.get_value():.2f}")

    def _on_preview(self, btn):
        self._apply_live()
        btn.set_label("Previewing...")
        btn.set_sensitive(False)
        GLib.timeout_add(1200, lambda: (btn.set_label("Preview"), btn.set_sensitive(True)))

    def _on_apply(self, btn):
        # Apply live
        self._apply_live()

        # Persist to config
        settings = {
            'blur_enabled': self.blur_toggle.get_active(),
            'blur_size': int(self.blur_size.get_value()),
            'blur_passes': int(self.blur_passes.get_value()),
            'shadow_enabled': self.shadow_toggle.get_active(),
            'shadow_range': int(self.shadow_range.get_value()),
            'shadow_render_power': int(self.shadow_power.get_value()),
            'rounding': int(self.rounding.get_value()),
            'active_opacity': self.active_opacity.get_value(),
            'inactive_opacity': self.inactive_opacity.get_value(),
        }
        persist_decoration(settings)

        # Re-apply the active shader (reload clears it)
        shader_idx = self.shader_combo.get_selected()
        if shader_idx > 0 and shader_idx < len(self.shader_files):
            shader_name = self.shader_files[shader_idx]
            shader_path = self._shader_name_to_path(shader_name)
            GLib.timeout_add(200, lambda: hyprctl_set('decoration:screen_shader', shader_path))

        btn.set_label("Saved \u2713")
        btn.set_sensitive(False)
        GLib.timeout_add(1500, lambda: (btn.set_label("Apply & Save"), btn.set_sensitive(True)))
