"""HyprConfig — Wallpaper selector page."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf

import subprocess
import shlex
import shutil
from pathlib import Path

from .parser import hyprctl_monitors, get_theme
from .paths import WALLPAPER_DIR, WALLPAPERS_SH
from .safe_io import atomic_write_text

try:
    from . import theming as _theming
except Exception:
    _theming = None

WALLS_DIR = WALLPAPER_DIR
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
THUMB_SIZE = 180
MAX_THUMBS = 300


class WallpaperPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._images = []
        self._selected_path = None
        self._current_wallpapers = {}
        self._monitor_names = []
        self._collections = []
        self._categories = []
        self._thumb_index = 0
        self._loading = False
        self._navigating_to_current = False
        self._swww_available = shutil.which('swww') is not None

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp(maximum_size=900)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        # Header
        hdr = Gtk.Label(label="Wallpaper", css_classes=['page-header'])
        hdr.set_halign(Gtk.Align.START)
        content.append(hdr)
        sub = Gtk.Label(
            label="Browse and set wallpapers per monitor or for all.",
            css_classes=['page-subheader']
        )
        sub.set_halign(Gtk.Align.START)
        content.append(sub)

        # ─── Current Wallpaper ───
        self.current_group = Adw.PreferencesGroup(title="Currently Active")
        self.current_rows = {}
        content.append(self.current_group)

        # ─── Target Monitor ───
        target_group = Adw.PreferencesGroup(title="Target")
        self.target_combo = Adw.ComboRow(
            title="Apply to",
            subtitle="Set wallpaper for one monitor or all at once",
        )
        target_group.add(self.target_combo)
        content.append(target_group)

        # ─── Collection / Category ───
        browse_group = Adw.PreferencesGroup(title="Browse")
        self.collection_combo = Adw.ComboRow(title="Collection")
        self.collection_combo.connect('notify::selected', self._on_collection_changed)
        browse_group.add(self.collection_combo)

        self.category_combo = Adw.ComboRow(title="Category")
        self.category_combo.connect('notify::selected', self._on_category_changed)
        browse_group.add(self.category_combo)
        content.append(browse_group)

        # ─── Preview ───
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        preview_box.add_css_class('wallpaper-preview-box')

        self.preview_picture = Gtk.Picture()
        self.preview_picture.set_size_request(-1, 350)
        self.preview_picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.preview_picture.add_css_class('wallpaper-preview')
        preview_box.append(self.preview_picture)

        self.preview_name = Gtk.Label(label="Click a thumbnail to preview")
        self.preview_name.set_halign(Gtk.Align.START)
        self.preview_name.add_css_class('page-subheader')
        self.preview_name.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        preview_box.append(self.preview_name)

        content.append(preview_box)

        # ─── Thumbnail Grid ───
        self.grid_label = Gtk.Label(css_classes=['page-subheader'])
        self.grid_label.set_halign(Gtk.Align.START)
        content.append(self.grid_label)

        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_valign(Gtk.Align.START)
        self.flow_box.set_max_children_per_line(5)
        self.flow_box.set_min_children_per_line(2)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flow_box.set_homogeneous(True)
        self.flow_box.set_row_spacing(8)
        self.flow_box.set_column_spacing(8)
        self.flow_box.connect('selected-children-changed', self._on_selection_changed)
        content.append(self.flow_box)

        # ─── Buttons ───
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(12)

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect('clicked', lambda b: self._refresh())
        btn_box.append(refresh_btn)

        self.apply_btn = Gtk.Button(
            label="Apply",
            css_classes=['suggested-action', 'apply-btn']
        )
        self.apply_btn.connect('clicked', self._on_apply)
        self.apply_btn.set_sensitive(self._swww_available)
        if not self._swww_available:
            self.apply_btn.set_tooltip_text("Install swww to apply wallpapers")
        btn_box.append(self.apply_btn)

        self.save_btn = Gtk.Button(
            label="Save to Config",
            css_classes=['suggested-action', 'apply-btn']
        )
        self.save_btn.connect('clicked', self._on_save)
        self.save_btn.set_sensitive(self._swww_available)
        btn_box.append(self.save_btn)

        content.append(btn_box)

        clamp.set_child(content)
        scroll.set_child(clamp)
        self.append(scroll)

        GLib.idle_add(self._refresh)

    # ── Data Loading ──

    def _refresh(self):
        self._load_monitors()
        self._load_current_wallpapers()
        self._show_current_wallpapers()
        self._load_collections()
        self._navigate_to_current()
        return False

    def _load_monitors(self):
        monitors = hyprctl_monitors()
        model = Gtk.StringList()
        model.append("All Monitors")
        self._monitor_names = []
        for mon in sorted(monitors, key=lambda m: m.get('x', 0)):
            name = mon.get('name', '?')
            w = mon.get('width', 0)
            h = mon.get('height', 0)
            model.append(f"{name}  ({w}\u00d7{h})")
            self._monitor_names.append(name)
        self.target_combo.set_model(model)

    def _load_current_wallpapers(self):
        self._current_wallpapers = {}
        try:
            r = subprocess.run(
                ['swww', 'query'], capture_output=True, text=True, timeout=3
            )
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    if 'currently displaying: image:' not in line:
                        continue
                    img_path = line.split('currently displaying: image:')[1].strip()
                    # Parse monitor: ": eDP-1: 1920x1080, ..."
                    parts = line.split(':')
                    if len(parts) >= 3:
                        mon = parts[1].strip()
                        self._current_wallpapers[mon] = img_path
        except Exception:
            pass

    def _show_current_wallpapers(self):
        """Display current wallpaper info in the Current section."""
        # Clear old rows
        for name, row in list(self.current_rows.items()):
            self.current_group.remove(row)
        self.current_rows.clear()

        if not self._current_wallpapers:
            row = Adw.ActionRow(
                title="No wallpaper detected",
                subtitle="swww may not be running",
            )
            row.add_css_class('monitor-res')
            self.current_group.add(row)
            self.current_rows['_none'] = row
            return

        # Check if all monitors share the same wallpaper
        unique_paths = set(self._current_wallpapers.values())
        if len(unique_paths) == 1:
            wp_path = next(iter(unique_paths))
            wp_name = Path(wp_path).name
            # Figure out which category it's in
            rel = self._wallpaper_location(wp_path)
            row = Adw.ActionRow(
                title="All Monitors",
                subtitle=f"{rel}\n{wp_name}",
            )
            row.set_subtitle_lines(2)
            self.current_group.add(row)
            self.current_rows['_all'] = row
        else:
            for mon in sorted(self._current_wallpapers):
                wp_path = self._current_wallpapers[mon]
                wp_name = Path(wp_path).name
                rel = self._wallpaper_location(wp_path)
                row = Adw.ActionRow(
                    title=mon,
                    subtitle=f"{rel}\n{wp_name}",
                )
                row.set_subtitle_lines(2)
                self.current_group.add(row)
                self.current_rows[mon] = row

    def _wallpaper_location(self, wp_path):
        """Return a human-readable location like '1 / wave'."""
        try:
            rel = Path(wp_path).relative_to(WALLS_DIR)
            parts = rel.parts
            if len(parts) >= 2:
                return f"{parts[0]} / {parts[1]}"
            elif len(parts) >= 1:
                return parts[0]
        except ValueError:
            pass
        return str(Path(wp_path).parent)

    def _navigate_to_current(self):
        """Auto-select the collection/category containing the current wallpaper."""
        if not self._current_wallpapers:
            return

        # Use the leftmost reported monitor's wallpaper (or first available).
        wp_path = None
        preferred = self._monitor_names + sorted(self._current_wallpapers.keys())
        for mon in preferred:
            if mon in self._current_wallpapers:
                wp_path = self._current_wallpapers[mon]
                break
        if not wp_path:
            return

        try:
            rel = Path(wp_path).relative_to(WALLS_DIR)
            parts = rel.parts  # e.g. ('1', 'wave', 'filename.png')
        except ValueError:
            return

        if len(parts) < 2:
            return

        collection_name = parts[0]
        category_name = parts[1] if len(parts) >= 3 else None

        # Find and select the collection
        self._navigating_to_current = True
        for i, col_dir in enumerate(self._collections):
            if col_dir.name == collection_name:
                self.collection_combo.set_selected(i)
                # After collection changes, find the category
                if category_name:
                    GLib.idle_add(self._select_category, category_name)
                break
        if not category_name:
            self._navigating_to_current = False

    def _select_category(self, category_name):
        """Select a category by name after collection has loaded."""
        for i, cat_dir in enumerate(self._categories):
            if cat_dir.name == category_name:
                self.category_combo.set_selected(i)
                break
        self._navigating_to_current = False
        return False

    def _load_collections(self):
        model = Gtk.StringList()
        self._collections = []
        if WALLS_DIR.exists():
            for d in sorted(WALLS_DIR.iterdir()):
                if d.is_dir() and not d.name.startswith('.'):
                    model.append(d.name)
                    self._collections.append(d)
        self.collection_combo.set_model(model)
        if self._collections and not self._navigating_to_current:
            self.collection_combo.set_selected(0)

    # ── Collection / Category Navigation ──

    def _on_collection_changed(self, combo, pspec):
        idx = combo.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION or idx >= len(self._collections):
            return
        col_dir = self._collections[idx]
        model = Gtk.StringList()
        self._categories = []

        subdirs = sorted(
            d for d in col_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        )
        if subdirs:
            model.append("All")
            self._categories.append(col_dir)
            for d in subdirs:
                count = sum(
                    1 for f in d.iterdir()
                    if f.is_file() and f.suffix.lower() in IMAGE_EXTS
                )
                model.append(f"{d.name}  ({count})")
                self._categories.append(d)
        else:
            model.append("All")
            self._categories.append(col_dir)

        self.category_combo.set_model(model)
        self.category_combo.set_selected(0)

    def _on_category_changed(self, combo, pspec):
        idx = combo.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION or idx >= len(self._categories):
            return
        cat_dir = self._categories[idx]
        self._load_images(cat_dir, recursive=(idx == 0))

    # ── Image Grid ──

    def _load_images(self, directory, recursive=False):
        self._loading = False  # stop any in-progress batch load

        # Clear grid
        while True:
            child = self.flow_box.get_first_child()
            if child is None:
                break
            self.flow_box.remove(child)

        self._images = []
        iterator = directory.rglob('*') if recursive else directory.iterdir()
        for p in sorted(iterator):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                self._images.append(p)

        total = len(self._images)
        showing = min(total, MAX_THUMBS)
        if total > MAX_THUMBS:
            self.grid_label.set_text(f"Showing {showing} of {total} images")
        else:
            self.grid_label.set_text(f"{total} images")

        self._thumb_index = 0
        if self._images:
            self._loading = True
            GLib.idle_add(self._load_thumb_batch)

    def _load_thumb_batch(self):
        if not self._loading:
            return False

        batch = 15
        end = min(self._thumb_index + batch, len(self._images), MAX_THUMBS)

        for i in range(self._thumb_index, end):
            self._add_thumbnail(self._images[i])

        self._thumb_index = end
        if self._thumb_index < len(self._images) and self._thumb_index < MAX_THUMBS:
            return True  # keep calling
        self._loading = False
        return False

    def _add_thumbnail(self, path):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(path), THUMB_SIZE, int(THUMB_SIZE * 0.66), True
            )
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            picture = Gtk.Picture.new_for_paintable(texture)
            picture.set_size_request(THUMB_SIZE, int(THUMB_SIZE * 0.56))
            picture.set_content_fit(Gtk.ContentFit.COVER)
        except Exception:
            return  # skip broken images

        is_current = str(path) in self._current_wallpapers.values()

        frame = Gtk.Frame()
        frame.set_child(picture)
        frame.add_css_class('wallpaper-thumb-frame')
        if is_current:
            frame.add_css_class('wallpaper-thumb-current')

        frame._wp_path = str(path)
        self.flow_box.append(frame)

    # ── Selection & Preview ──

    def _on_selection_changed(self, flow_box):
        selected = flow_box.get_selected_children()
        if not selected:
            return
        child = selected[0]
        frame = child.get_child()
        if frame is None or not hasattr(frame, '_wp_path'):
            return

        self._selected_path = frame._wp_path
        self.preview_name.set_text(Path(self._selected_path).name)

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                self._selected_path, 850, 500, True
            )
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            self.preview_picture.set_paintable(texture)
        except Exception:
            pass

    # ── Apply & Save ──

    def _get_target_monitors(self):
        idx = self.target_combo.get_selected()
        if idx == 0 or idx == Gtk.INVALID_LIST_POSITION:
            return list(self._monitor_names)
        if idx - 1 < len(self._monitor_names):
            return [self._monitor_names[idx - 1]]
        return list(self._monitor_names)

    def _on_apply(self, btn):
        if not self._selected_path:
            return
        targets = self._get_target_monitors()
        for mon in targets:
            try:
                subprocess.run(
                    ['swww', 'img', self._selected_path, '-o', mon,
                     '--transition-type', 'fade', '--transition-duration', '2'],
                    capture_output=True, timeout=5
                )
                self._current_wallpapers[mon] = self._selected_path
            except Exception:
                pass

        # Refresh the "Currently Active" section
        self._show_current_wallpapers()

        # If Material You theming is on, regenerate the full theme from the
        # new wallpaper so waybar/fish/rofi/hypr colors track it live.
        if _theming is not None and get_theme('palette') == 'matugen':
            try:
                _theming.regenerate_theme_from_wallpaper()
            except Exception:
                pass

        btn.set_label("Applied \u2713")
        btn.set_sensitive(False)
        GLib.timeout_add(1500, lambda: (
            btn.set_label("Apply"), btn.set_sensitive(True)
        ))

    def _on_save(self, btn):
        """Persist current wallpaper state to wallpapers.sh."""
        if not self._current_wallpapers:
            return

        mons = sorted(self._current_wallpapers)
        lines = [
            '#!/bin/bash',
            '# Set wallpapers per monitor after swww-daemon starts',
            '# Managed by HyprConfig',
            'sleep 2',
            '',
            'TRANSITION="--transition-type fade --transition-duration 2"',
            '',
        ]
        for mon in mons:
            wp = self._current_wallpapers[mon]
            lines.append(
                f'swww img {shlex.quote(wp)} -o {shlex.quote(mon)} $TRANSITION'
            )
        lines.append('')

        # After persisting, refresh the theme from the saved wallpaper so a
        # reboot/login keeps waybar/fish/rofi/hypr in sync with matugen.
        if _theming is not None and get_theme('palette') == 'matugen':
            try:
                _theming.regenerate_theme_from_wallpaper()
            except Exception:
                pass

        atomic_write_text(WALLPAPERS_SH, '\n'.join(lines), mode=0o755)

        btn.set_label("Saved \u2713")
        btn.set_sensitive(False)
        GLib.timeout_add(1500, lambda: (
            btn.set_label("Save to Config"), btn.set_sensitive(True)
        ))
