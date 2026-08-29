"""HyprConfig — Keybindings cheatsheet page with conflict detection and editing."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Pango

from .parser import parse_keybindings, find_conflicts, rewrite_bind, hyprctl_reload, HYPR_DIR


# Prettify key names
KEY_DISPLAY = {
    'Left': '\u2190', 'Right': '\u2192', 'Up': '\u2191', 'Down': '\u2193',
    'Return': '\u21b5', 'Tab': '\u21e5', 'Delete': 'Del', 'Escape': 'Esc',
    'space': 'Space', 'slash': '/', 'mouse:272': 'LMB', 'mouse:273': 'RMB',
    'mouse_down': 'Scroll\u2193', 'mouse_up': 'Scroll\u2191',
    'equal': '=', 'minus': '-', 'Print': 'PrtSc',
    'KP_Left': 'Num\u2190', 'KP_Right': 'Num\u2192',
    'KP_Up': 'Num\u2191', 'KP_Down': 'Num\u2193',
}

MOD_DISPLAY = {
    'Super': 'Super', 'Shift': 'Shift', 'Control': 'Ctrl', 'Alt': 'Alt',
    'ALT': 'Alt', 'Alt_R': 'RAlt', 'Control_R': 'RCtrl',
    '$mainMod': 'Super',
}

# Reverse map for writing back
MOD_WRITE = {'Super': '$mainMod', 'Shift': 'Shift', 'Ctrl': 'Control',
             'Control': 'Control', 'Alt': 'Alt'}
KEY_WRITE = {v: k for k, v in KEY_DISPLAY.items()}


class KeybindingsPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.search_text = ""
        self.show_conflicts_only = False

        # ─── Header bar ───
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                         css_classes=['filter-row'])

        self.search = Gtk.SearchEntry(
            placeholder_text="Search keybindings...",
            css_classes=['search-entry'],
            hexpand=True,
        )
        self.search.connect('search-changed', self.on_search)
        header.append(self.search)

        self.conflict_btn = Gtk.Button(css_classes=['conflict-badge'])
        self.conflict_btn.connect('clicked', self.toggle_conflict_filter)
        header.append(self.conflict_btn)

        self.append(header)

        # ─── Hint ───
        hint = Gtk.Label(
            label="Click any keybind to edit it",
            css_classes=['page-subheader'],
        )
        hint.set_margin_start(16)
        hint.set_margin_top(4)
        hint.set_halign(Gtk.Align.START)
        self.append(hint)

        # ─── Scrollable content ───
        scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_homogeneous(False)
        self.flowbox.set_max_children_per_line(8)
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_row_spacing(10)
        self.flowbox.set_column_spacing(10)
        self.flowbox.set_margin_start(16)
        self.flowbox.set_margin_end(16)
        self.flowbox.set_margin_top(8)
        self.flowbox.set_margin_bottom(16)

        self.flowbox.set_filter_func(self.filter_func)

        scroll.set_child(self.flowbox)
        self.append(scroll)

        # Load
        self.load_keybindings()

    def load_keybindings(self):
        self.binds = parse_keybindings()
        self.conflicts = find_conflicts(self.binds)

        # Conflict badge
        n = len(self.conflicts)
        if n > 0:
            self.conflict_btn.set_label(f"\u26a0 {n} conflict{'s' if n != 1 else ''}")
            self.conflict_btn.remove_css_class('no-conflicts')
        else:
            self.conflict_btn.set_label("\u2713 No conflicts")
            self.conflict_btn.add_css_class('no-conflicts')

        # Group binds by category
        groups = {}
        for bind in self.binds:
            if bind.subgroup:
                key = f"{bind.group} > {bind.subgroup}"
            else:
                key = bind.group or "Other"
            if key not in groups:
                groups[key] = []
            groups[key].append(bind)

        # Sort categories: prioritize Window Management and Tiling near the top
        GROUP_ORDER = [
            'Window Management', 'Tiling',
        ]
        def sort_key(name):
            base = name.split(' > ')[0]
            if base in GROUP_ORDER:
                return (GROUP_ORDER.index(base), name)
            return (len(GROUP_ORDER), name)

        sorted_groups = sorted(groups.items(), key=lambda kv: sort_key(kv[0]))

        # Create category cards
        for group_name, binds in sorted_groups:
            card = self._create_card(group_name, binds)
            self.flowbox.append(card)

    def _create_card(self, group_name, binds):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=['category-card'])
        card.set_size_request(286, -1)

        # Title
        title = Gtk.Label(label=group_name.upper(), css_classes=['category-title'])
        title.set_halign(Gtk.Align.START)
        card.append(title)

        sep = Gtk.Box(css_classes=['category-sep'])
        card.append(sep)

        # Bind rows
        bind_rows = []
        for bind in binds:
            row = self._create_bind_row(bind)
            card.append(row)
            bind_rows.append((bind, row))

        card._bind_rows = bind_rows
        card._group_name = group_name
        return card

    def _create_bind_row(self, bind):
        # Wrap in a clickable button-like container
        row_btn = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row_btn.set_cursor_from_name('pointer')

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_margin_top(3)
        row.set_margin_bottom(3)

        # Click handler
        click = Gtk.GestureClick()
        click.connect('released', self._on_bind_clicked, bind)
        row.add_controller(click)

        # Key combo area
        combo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        combo_box.set_size_request(150, -1)
        combo_box.set_halign(Gtk.Align.START)

        mods = bind.mods.split() if bind.mods else []
        first = True
        for mod in mods:
            if mod.startswith('$') or mod == '':
                continue
            if not first:
                plus = Gtk.Label(label="+", css_classes=['keycap-plus'])
                combo_box.append(plus)
            display_mod = MOD_DISPLAY.get(mod, mod)
            keycap = Gtk.Label(label=display_mod, css_classes=['keycap', 'keycap-mod'])
            combo_box.append(keycap)
            first = False

        if mods and not first:
            plus = Gtk.Label(label="+", css_classes=['keycap-plus'])
            combo_box.append(plus)

        key_display = KEY_DISPLAY.get(bind.key, bind.key)
        keycap = Gtk.Label(label=key_display, css_classes=['keycap'])
        combo_box.append(keycap)

        row.append(combo_box)

        # Description
        desc = bind.description or bind.dispatcher
        desc_label = Gtk.Label(label=desc, css_classes=['keybind-desc'])
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_hexpand(True)
        desc_label.set_ellipsize(Pango.EllipsizeMode.END)
        desc_label.set_max_width_chars(35)
        row.append(desc_label)

        # Source file indicator
        source = Gtk.Label(label=bind.source_file.replace('.conf', ''),
                          css_classes=['source-tag'])
        row.append(source)

        # Conflict indicator
        if bind.combo_key in self.conflicts:
            dot = Gtk.Label(label="\u25cf", css_classes=['conflict-dot'])
            dot.set_tooltip_text(
                f"Conflict: {bind.combo}\n"
                + "\n".join(f"  {b.source_file}:{b.line_num} ({b.dispatcher})"
                           for b in self.conflicts[bind.combo_key])
            )
            row.append(dot)

        row._bind = bind
        row_btn.append(row)
        row_btn._bind = bind
        return row_btn

    def _on_bind_clicked(self, gesture, n_press, x, y, bind):
        """Open edit dialog for the clicked keybind."""
        win = self.get_root()
        dialog = KeybindEditDialog(win, bind, self._on_bind_saved)
        dialog.present()

    def _on_bind_saved(self):
        """Reload keybindings after an edit."""
        # Clear flowbox
        while True:
            child = self.flowbox.get_first_child()
            if child is None:
                break
            self.flowbox.remove(child)
        # Reload
        self.load_keybindings()

    def filter_func(self, child):
        card = child.get_child()
        if not hasattr(card, '_bind_rows'):
            return True

        has_visible = False
        for bind, row_btn in card._bind_rows:
            visible = True

            if self.show_conflicts_only and bind.combo_key not in self.conflicts:
                visible = False

            if visible and self.search_text:
                searchable = (
                    bind.description.lower() + " " +
                    bind.combo.lower() + " " +
                    bind.dispatcher.lower() + " " +
                    bind.args.lower() + " " +
                    (card._group_name or "").lower()
                )
                visible = self.search_text in searchable

            row_btn.set_visible(visible)
            if visible:
                has_visible = True

        return has_visible

    def on_search(self, entry):
        self.search_text = entry.get_text().lower().strip()
        self.flowbox.invalidate_filter()

    def toggle_conflict_filter(self, button):
        self.show_conflicts_only = not self.show_conflicts_only
        if self.show_conflicts_only:
            button.set_label("\u26a0 Showing conflicts only")
        else:
            n = len(self.conflicts)
            if n > 0:
                button.set_label(f"\u26a0 {n} conflict{'s' if n != 1 else ''}")
            else:
                button.set_label("\u2713 No conflicts")
        self.flowbox.invalidate_filter()


class KeybindEditDialog(Adw.Window):
    """Dialog to edit a keybind's key combo."""

    def __init__(self, parent, bind, on_save_cb):
        super().__init__(
            title=f"Edit: {bind.description or bind.dispatcher}",
            transient_for=parent,
            modal=True,
            default_width=420,
            default_height=320,
        )
        self.bind = bind
        self.on_save_cb = on_save_cb
        self.captured_mods = set()
        self.captured_key = ""

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)

        # Current binding info
        info_group = Adw.PreferencesGroup(title="Current Binding")

        current_row = Adw.ActionRow(
            title="Key Combo",
            subtitle=bind.combo,
        )
        info_group.add(current_row)

        desc_row = Adw.ActionRow(
            title="Action",
            subtitle=f"{bind.dispatcher} {bind.args}".strip(),
        )
        info_group.add(desc_row)

        file_row = Adw.ActionRow(
            title="Source",
            subtitle=f"{bind.source_file} line {bind.line_num}",
        )
        info_group.add(file_row)

        content.append(info_group)

        # New binding
        new_group = Adw.PreferencesGroup(title="New Key Combo")

        # Modifier toggles
        mod_row = Adw.ActionRow(title="Modifiers")
        mod_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mod_box.set_valign(Gtk.Align.CENTER)

        current_mods = bind.mods.split() if bind.mods else []
        self.mod_checks = {}
        for mod_name in ['Super', 'Shift', 'Control', 'Alt']:
            check = Gtk.CheckButton(label=mod_name)
            # Check if currently active
            active = any(m in current_mods or
                        (mod_name == 'Super' and m in ('$mainMod', 'Super'))
                        for m in current_mods)
            check.set_active(active)
            mod_box.append(check)
            self.mod_checks[mod_name] = check

        mod_row.add_suffix(mod_box)
        new_group.add(mod_row)

        # Key entry
        self.key_entry = Adw.EntryRow(title="Key")
        self.key_entry.set_text(bind.key)
        new_group.add(self.key_entry)

        # Key capture button
        capture_row = Adw.ActionRow(
            title="Or press a key",
            subtitle="Click Capture, then press the desired key"
        )
        self.capture_btn = Gtk.Button(label="Capture")
        self.capture_btn.set_valign(Gtk.Align.CENTER)
        self.capture_btn.connect('clicked', self._on_capture)
        capture_row.add_suffix(self.capture_btn)
        new_group.add(capture_row)

        content.append(new_group)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect('clicked', lambda b: self.close())
        btn_box.append(cancel_btn)

        save_btn = Gtk.Button(label="Save", css_classes=['suggested-action'])
        save_btn.connect('clicked', self._on_save)
        btn_box.append(save_btn)

        content.append(btn_box)

        toolbar.set_content(content)
        self.set_content(toolbar)

    def _on_capture(self, btn):
        """Start key capture mode."""
        btn.set_label("Press a key...")
        btn.set_sensitive(False)

        # Add key event controller
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect('key-pressed', self._on_key_captured)
        self.add_controller(key_ctrl)
        self._capture_controller = key_ctrl

    def _on_key_captured(self, controller, keyval, keycode, state):
        """Capture the pressed key."""
        key_name = Gdk.keyval_name(keyval)
        if not key_name:
            return True

        # Skip pure modifier keys
        if key_name in ('Super_L', 'Super_R', 'Shift_L', 'Shift_R',
                        'Control_L', 'Control_R', 'Alt_L', 'Alt_R',
                        'Meta_L', 'Meta_R', 'Hyper_L', 'Hyper_R'):
            return True

        # Detect modifiers from state
        if state & Gdk.ModifierType.SUPER_MASK:
            self.mod_checks['Super'].set_active(True)
        if state & Gdk.ModifierType.SHIFT_MASK:
            self.mod_checks['Shift'].set_active(True)
        if state & Gdk.ModifierType.CONTROL_MASK:
            self.mod_checks['Control'].set_active(True)
        if state & Gdk.ModifierType.ALT_MASK:
            self.mod_checks['Alt'].set_active(True)

        # Map key name to Hyprland key name
        self.key_entry.set_text(key_name)

        # Reset capture button
        self.capture_btn.set_label("Capture")
        self.capture_btn.set_sensitive(True)
        self.remove_controller(self._capture_controller)

        return True

    def _on_save(self, btn):
        """Save the new keybind."""
        # Build new mods string
        mods = []
        if self.mod_checks['Super'].get_active():
            mods.append('$mainMod')
        if self.mod_checks['Shift'].get_active():
            mods.append('Shift')
        if self.mod_checks['Control'].get_active():
            mods.append('Control')
        if self.mod_checks['Alt'].get_active():
            mods.append('Alt')

        new_mods = ' '.join(mods)
        new_key = self.key_entry.get_text().strip()

        if not new_key:
            return

        # Rewrite the config file
        success = rewrite_bind(self.bind, new_mods, new_key)

        if success:
            hyprctl_reload()
            btn.set_label("Saved \u2713")
            btn.set_sensitive(False)
            GLib.timeout_add(800, self.close)
            if self.on_save_cb:
                GLib.timeout_add(900, self.on_save_cb)
        else:
            btn.set_label("Error")
            GLib.timeout_add(1500, lambda: (btn.set_label("Save"), btn.set_sensitive(True)))
