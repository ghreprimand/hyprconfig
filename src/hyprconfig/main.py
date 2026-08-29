#!/usr/bin/env python3
"""HyprConfig — a GTK4 configuration companion for Hyprland."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Pango

from . import __version__
from .keybindings import KeybindingsPage
from .effects import EffectsPage
from .waybar_page import WaybarPage
from .theming import ThemingPage
from .display import DisplayPage
from .wallpaper import WallpaperPage

APP_CSS = """
/* ─── Global ─── */
window {
    background: rgba(12, 12, 24, 0.85);
}

/* ─── Sidebar ─── */
.sidebar {
    background: rgba(14, 14, 28, 0.9);
}
.sidebar-title {
    color: #ffd700;
    font-weight: bold;
    font-size: 20px;
    letter-spacing: 4px;
}
.sidebar-subtitle {
    color: rgba(255, 215, 0, 0.5);
    font-size: 11px;
    letter-spacing: 1px;
}
.sidebar-sep {
    background: rgba(255, 140, 0, 0.15);
    min-height: 1px;
}
.sidebar-list {
    background: transparent;
}
.sidebar-list row {
    padding: 0;
    border-radius: 0;
    transition: background 200ms;
}
.sidebar-list row:selected {
    background: rgba(255, 140, 0, 0.12);
    border-left: 3px solid #ff8c00;
}
.sidebar-list row:hover:not(:selected) {
    background: rgba(255, 255, 255, 0.03);
}
.sidebar-icon {
    font-size: 20px;
    min-width: 28px;
    color: #888;
}
.sidebar-list row:selected .sidebar-icon {
    color: #ffd700;
}
.sidebar-label {
    font-size: 14px;
    font-weight: 500;
    color: #aaa;
}
.sidebar-list row:selected .sidebar-label {
    color: #ffd700;
}
.sidebar-version {
    color: rgba(255, 255, 255, 0.2);
    font-size: 10px;
}
.sidebar-divider {
    background: rgba(255, 140, 0, 0.12);
    min-width: 1px;
}

/* ─── Keybindings Page ─── */
.search-entry {
    font-size: 14px;
    border-radius: 8px;
    min-height: 36px;
}
.conflict-badge {
    background: #e74c3c;
    color: white;
    border-radius: 12px;
    padding: 4px 14px;
    font-size: 12px;
    font-weight: bold;
}
.conflict-badge.no-conflicts {
    background: rgba(46, 204, 113, 0.2);
    color: #2ecc71;
}
.category-card {
    background: rgba(18, 18, 32, 0.95);
    border: 1px solid rgba(255, 140, 0, 0.1);
    border-radius: 12px;
    padding: 16px;
}
.category-title {
    color: #ff8c00;
    font-weight: bold;
    font-size: 12px;
    letter-spacing: 1.5px;
}
.category-sep {
    background: rgba(255, 140, 0, 0.15);
    min-height: 1px;
    margin-top: 6px;
    margin-bottom: 8px;
}
.keycap {
    background: linear-gradient(180deg, #3e3e56, #2e2e46);
    border: 1px solid #555;
    border-bottom-width: 3px;
    border-bottom-color: #333;
    border-radius: 5px;
    padding: 2px 8px;
    font-family: "JetBrainsMono Nerd Font", monospace;
    font-size: 11px;
    font-weight: bold;
    color: #e0e0e0;
    min-width: 16px;
    min-height: 18px;
}
.keycap-mod {
    background: linear-gradient(180deg, #4a3a1e, #3a2a0e);
    border-color: rgba(255, 140, 0, 0.4);
    border-bottom-color: rgba(255, 140, 0, 0.25);
    color: #ffd700;
}
.keycap-plus {
    color: #555;
    font-size: 10px;
    min-width: 8px;
}
.keybind-desc {
    color: #ccc;
    font-size: 12px;
}
.keybind-dispatcher {
    color: #666;
    font-size: 10px;
    font-family: "JetBrainsMono Nerd Font", monospace;
}
.conflict-dot {
    color: #e74c3c;
    font-size: 14px;
}
.source-tag {
    color: #555;
    font-size: 9px;
    font-family: "JetBrainsMono Nerd Font", monospace;
}
.filter-row {
    background: rgba(18, 18, 32, 0.7);
    border-bottom: 1px solid rgba(255, 140, 0, 0.08);
    padding: 8px 16px;
}
.filter-chip {
    background: rgba(255, 140, 0, 0.08);
    border: 1px solid rgba(255, 140, 0, 0.15);
    border-radius: 16px;
    padding: 4px 12px;
    font-size: 11px;
    color: #aaa;
    min-height: 24px;
}
.filter-chip:checked {
    background: rgba(255, 140, 0, 0.2);
    border-color: #ff8c00;
    color: #ffd700;
}

/* ─── Settings Pages ─── */
.page-header {
    color: #ffd700;
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 1px;
}
.page-subheader {
    color: rgba(255, 255, 255, 0.4);
    font-size: 12px;
}
.apply-btn {
    min-width: 120px;
    min-height: 36px;
    border-radius: 8px;
}

/* ─── Waybar Page ─── */
.waybar-card {
    background: rgba(18, 18, 32, 0.95);
    border: 1px solid rgba(255, 140, 0, 0.1);
    border-radius: 14px;
    padding: 20px;
    transition: border-color 200ms;
}
.waybar-card:hover {
    border-color: rgba(255, 140, 0, 0.3);
}
.waybar-card-active {
    border-color: #ff8c00;
    border-width: 2px;
}
.waybar-card-title {
    color: #ffd700;
    font-size: 16px;
    font-weight: bold;
}
.waybar-card-desc {
    color: #999;
    font-size: 12px;
}
.waybar-card-preview {
    background: rgba(10, 10, 20, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 8px;
    font-family: "JetBrainsMono Nerd Font", monospace;
    font-size: 10px;
    color: #777;
}
.active-check {
    color: #2ecc71;
    font-size: 18px;
    font-weight: bold;
}

/* ─── Theming Page ─── */
.color-swatch {
    border-radius: 8px;
    min-width: 48px;
    min-height: 48px;
    border: 2px solid rgba(255, 255, 255, 0.1);
}
.palette-row {
    margin: 2px 0;
}
.install-btn {
    background: rgba(255, 140, 0, 0.15);
    color: #ffd700;
    border: 1px solid rgba(255, 140, 0, 0.3);
    border-radius: 8px;
    padding: 8px 16px;
}

/* ─── Display Page ─── */
.monitor-card {
    background: rgba(18, 18, 32, 0.95);
    border: 1px solid rgba(255, 140, 0, 0.1);
    border-radius: 12px;
    padding: 16px;
}
.monitor-name {
    color: #ffd700;
    font-size: 14px;
    font-weight: bold;
    font-family: "JetBrainsMono Nerd Font", monospace;
}
.monitor-res {
    color: #888;
    font-size: 12px;
}
.monitor-active {
    border-color: rgba(255, 140, 0, 0.3);
}

/* ─── Wallpaper Page ─── */
.wallpaper-preview-box {
    background: rgba(18, 18, 32, 0.95);
    border: 1px solid rgba(255, 140, 0, 0.1);
    border-radius: 12px;
    padding: 16px;
}
.wallpaper-preview {
    background: rgba(10, 10, 20, 0.8);
    border-radius: 8px;
    min-height: 300px;
}
.wallpaper-thumb-frame {
    border-radius: 8px;
    border: 2px solid rgba(255, 255, 255, 0.06);
    background: rgba(10, 10, 20, 0.6);
    transition: border-color 200ms;
}
.wallpaper-thumb-frame:hover {
    border-color: rgba(255, 215, 0, 0.4);
}
flowboxchild:selected .wallpaper-thumb-frame {
    border-color: #ff8c00;
    border-width: 2px;
}
.wallpaper-thumb-current {
    border-color: #2ecc71;
}

/* ─── HyprConfig dark palette ───
 * Soft green typography with warm orange accents.
 */
window {
    background: rgba(14, 19, 21, 0.88);
    color: #94cdb3;
}
.sidebar {
    background: rgba(8, 12, 14, 0.92);
}
.sidebar-title,
.page-header,
.category-title,
.waybar-card-title,
.monitor-name,
.sidebar-list row:selected .sidebar-icon,
.sidebar-list row:selected .sidebar-label {
    color: #94cdb3;
    text-shadow: 0 0 7px rgba(148, 205, 179, 0.42);
}
.sidebar-title {
    font-size: 16px;
    letter-spacing: 2px;
}
.sidebar-subtitle {
    color: rgba(148, 205, 179, 0.56);
}
.sidebar-label,
.keybind-desc {
    color: #94cdb3;
}
.page-subheader,
.sidebar-version,
.waybar-card-desc,
.monitor-res,
.keybind-dispatcher,
.source-tag {
    color: #527363;
}
.sidebar-sep,
.sidebar-divider,
.category-sep {
    background: rgba(195, 117, 46, 0.22);
}
.sidebar-list row:selected {
    background: rgba(25, 31, 35, 0.90);
    border-left-color: #c3752e;
}
.sidebar-list row:hover:not(:selected) {
    background: rgba(148, 205, 179, 0.06);
}
.category-card,
.waybar-card,
.monitor-card,
.wallpaper-preview-box {
    background: rgba(25, 31, 35, 0.82);
    border-color: rgba(148, 205, 179, 0.20);
}
.filter-row {
    background: rgba(25, 31, 35, 0.72);
    border-bottom-color: rgba(148, 205, 179, 0.14);
}
.filter-chip,
.install-btn {
    background: rgba(148, 205, 179, 0.10);
    border-color: rgba(148, 205, 179, 0.25);
    color: #94cdb3;
}
.filter-chip:checked,
.waybar-card-active {
    background: rgba(195, 117, 46, 0.18);
    border-color: #c3752e;
    color: #94cdb3;
}
.keycap {
    background: linear-gradient(180deg, #282e2d, #191f23);
    border-color: #527363;
    border-bottom-color: #0e1315;
    color: #94cdb3;
}
.keycap-mod {
    background: linear-gradient(180deg, #4b3722, #191f23);
    border-color: rgba(195, 117, 46, 0.48);
    border-bottom-color: rgba(195, 117, 46, 0.28);
    color: #94cdb3;
}
.waybar-card-preview,
.wallpaper-preview,
.wallpaper-thumb-frame {
    background: rgba(14, 19, 21, 0.78);
    border-color: rgba(148, 205, 179, 0.10);
}
.waybar-card:hover,
.monitor-active,
.wallpaper-thumb-frame:hover {
    border-color: rgba(148, 205, 179, 0.46);
}
flowboxchild:selected .wallpaper-thumb-frame {
    border-color: #c3752e;
}
.wallpaper-thumb-current,
.active-check,
.conflict-badge.no-conflicts {
    color: #86d98e;
    border-color: #7dd083;
}
button.suggested-action,
switch:checked {
    background: #c3752e;
    color: #0e1315;
}
preferencesgroup list {
    background: rgba(25, 31, 35, 0.84);
    border: 1px solid rgba(148, 205, 179, 0.16);
}
preferencesgroup row {
    color: #94cdb3;
}
"""


class HyprConfigWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("HyprConfig")
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(APP_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Start compact and let every page scroll instead of imposing a large
        # desktop-oriented minimum size.
        self.set_default_size(760, 600)

        # Escape to close
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect('key-pressed', self.on_key_pressed)
        self.add_controller(key_ctrl)

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_content(main_box)

        # ─── Sidebar ───
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=['sidebar'])
        sidebar.set_size_request(176, -1)

        # Title area
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_box.set_margin_top(16)
        title_box.set_margin_bottom(12)
        title_box.set_margin_start(14)
        title_box.set_margin_end(12)

        title = Gtk.Label(label="HYPRCONFIG", css_classes=['sidebar-title'])
        title.set_halign(Gtk.Align.START)
        title_box.append(title)

        subtitle = Gtk.Label(label="Hyprland settings", css_classes=['sidebar-subtitle'])
        subtitle.set_halign(Gtk.Align.START)
        title_box.append(subtitle)

        sidebar.append(title_box)
        sidebar.append(Gtk.Separator(css_classes=['sidebar-sep']))

        # Navigation list
        self.sidebar_list = Gtk.ListBox(css_classes=['sidebar-list'])
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.connect('row-selected', self.on_row_selected)

        # Stack for pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.stack.set_hhomogeneous(False)
        self.stack.set_vhomogeneous(False)

        pages = [
            ("keybindings", "\u2328", "Keybindings", "View & search all shortcuts"),
            ("effects", "\u2728", "Effects", "Blur, shadows, opacity"),
            ("waybar", "\u2261", "Waybar", "Switch bar styles"),
            ("theming", "\U0001f3a8", "Theming", "Material You colors"),
            ("display", "\U0001f5b5", "Display", "Monitor scaling"),
            ("wallpaper", "\U0001f5bc", "Wallpaper", "Per-monitor backgrounds"),
        ]

        self.page_widgets = {}
        for page_id, icon, label, desc in pages:
            # Create sidebar row
            row = Gtk.ListBoxRow()
            row.page_id = page_id
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            box.set_margin_start(12)
            box.set_margin_end(10)
            box.set_margin_top(9)
            box.set_margin_bottom(9)

            icon_label = Gtk.Label(label=icon, css_classes=['sidebar-icon'])
            box.append(icon_label)

            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            name_label = Gtk.Label(label=label, css_classes=['sidebar-label'])
            name_label.set_halign(Gtk.Align.START)
            name_label.set_ellipsize(Pango.EllipsizeMode.END)
            text_box.append(name_label)

            desc_label = Gtk.Label(label=desc)
            desc_label.set_halign(Gtk.Align.START)
            desc_label.set_ellipsize(Pango.EllipsizeMode.END)
            desc_label.set_max_width_chars(18)
            desc_label.set_single_line_mode(True)
            desc_label.add_css_class('sidebar-version')
            text_box.append(desc_label)

            box.append(text_box)
            row.set_child(box)
            self.sidebar_list.append(row)

        sidebar.append(self.sidebar_list)

        # Spacer + version at bottom
        spacer = Gtk.Box(vexpand=True)
        sidebar.append(spacer)

        ver_label = Gtk.Label(
            label=f"HyprConfig {__version__}  |  Esc to close",
            css_classes=['sidebar-version'],
        )
        ver_label.set_margin_bottom(12)
        sidebar.append(ver_label)

        main_box.append(sidebar)
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL, css_classes=['sidebar-divider']))

        # Create pages (deferred to avoid slow startup)
        self.page_classes = {
            "keybindings": KeybindingsPage,
            "effects": EffectsPage,
            "waybar": WaybarPage,
            "theming": ThemingPage,
            "display": DisplayPage,
            "wallpaper": WallpaperPage,
        }
        for page_id, _, _, _ in pages:
            # Create placeholder
            placeholder = Gtk.Box()
            self.stack.add_named(placeholder, page_id)

        main_box.append(self.stack)

        # Select first row
        first_row = self.sidebar_list.get_row_at_index(0)
        if first_row:
            self.sidebar_list.select_row(first_row)

    def on_row_selected(self, listbox, row):
        if row is None:
            return
        page_id = row.page_id

        # Lazy-load page
        if page_id not in self.page_widgets:
            page_class = self.page_classes[page_id]
            page = page_class()
            self.page_widgets[page_id] = page
            # Replace placeholder
            old = self.stack.get_child_by_name(page_id)
            if old:
                self.stack.remove(old)
            self.stack.add_named(page, page_id)

        self.stack.set_visible_child_name(page_id)

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False


class HyprConfigApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.ghreprimand.hyprconfig',
                         flags=0)

    def do_activate(self):
        win = self.get_active_window()
        if win is None:
            win = HyprConfigWindow(application=self)
        win.present()


def main():
    app = HyprConfigApp()
    app.run(None)


if __name__ == '__main__':
    main()
