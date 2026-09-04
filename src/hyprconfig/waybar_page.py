"""HyprConfig — Waybar style cycling page."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from .parser import WAYBAR_VARIANTS_DIR, load_state, save_state
from .theming import restart_waybar
from .paths import BUILTIN_VARIANTS_DIR
from .safe_io import UnsafeWriteError
from .waybar_profiles import apply_setup, list_profiles, profile_dir, save_profile

VARIANTS = {
    "powerline": {
        "name": "Powerline",
        "desc": "Ribbon-style bar with diagonal dividers between sections. "
                "Gold bookend buttons, per-section gradient backgrounds.",
        "preview": (
            "\u25c6\u276e \u276f \u25c6 \u2502 ws1 ws2 ws3 \u2502 title... "
            "      time \u2502 cpu mem gpu \u2502 vol \u2502 net \u2502 tray \u23fb"
        ),
    },
    "minimal": {
        "name": "Minimal",
        "desc": "Clean and slim. No dividers, flat colors, just the essentials. "
                "Text-focused with subtle gold highlights.",
        "preview": (
            "ws1 ws2 ws3  title...          "
            "12:30 PM  Mon Mar 17  cpu 12%  mem 34%  vol 80%  \u23fb"
        ),
    },
    "islands": {
        "name": "Floating Islands",
        "desc": "Modules grouped into separate floating pills with rounded corners "
                "and gaps between groups. Modern and spacious.",
        "preview": (
            "[ \u25c6 ws1 ws2 ws3 ]   [ title ]       "
            "[ 12:30 ]  [ cpu mem gpu ]  [ vol net ]  [ \u23fb ]"
        ),
    },
    "mechabar": {
        "name": "Mechabar",
        "desc": "Segmented powerline from sejjy/mechabar. Catppuccin Mocha colors "
                "with center-focused stats and halfblock arrow dividers.",
        "preview": (
            "\u258c\u25c6\u258c ws1 ws2 ws3 \u2590   "
            "\u258ctemp\u258cmem\u258ccpu\u258c \u25c6 \u2590 14:30 \u2590 19-03 \u2590 net gpu\u2590   "
            "\u25b6 title \u2014 artist   \u258cvol\u258c  tray \u23fb"
        ),
    },
    "synthwave": {
        "name": "Synthwave",
        "desc": "Retro-futuristic neon from ttpears/waybar. Magenta/cyan on deep "
                "purple with glowing pill modules. 80s outrun aesthetic.",
        "preview": (
            "[\u25c6] [ws1 ws2 ws3]  title   "
            "[12:30] [cpu] [mem] [temp] [vol] [net]  [\u23fb]"
        ),
    },
    "tokyonight": {
        "name": "Tokyo Night",
        "desc": "Soft blue-purple pastels from ttpears/waybar Tokyo Night theme. "
                "Grouped pills on dark navy with subtle blue glow.",
        "preview": (
            "[ \u25c6 ws1 ws2 ws3 ]   [ title ]       "
            "[ 12:30 ]  [ cpu mem gpu ]  [ vol net ]  [ \u23fb ]"
        ),
    },
    "bottom-dock": {
        "name": "Bottom Dock",
        "desc": "macOS dock-inspired bottom bar. Large centered app icons with "
                "compact status indicators. Floating dark rounded pill.",
        "preview": (
            "                    \u25c6 \u25cf\u25cf\u25cf   "
            "app app app \u00b7 12:30   gpu cpu mem \u266a \u25cf tray \u23fb"
        ),
    },
    "neon-circuit": {
        "name": "Neon Circuit",
        "desc": "Cyberpunk circuit-board look from JaKooLit (by Krautt). Asymmetric "
                "cut corners, colored borders per section, gradient workspace pills.",
        "preview": (
            "[\u25c6] [\u25cf ws1 ws2 ws3]  [title]   "
            "\u2502\u23f0\u2502  \u2502temp cpu mem gpu\u2502  \u2502vol\u2502  [tray] \u23fb"
        ),
    },
    "golden-noir": {
        "name": "Golden Noir",
        "desc": "Deep black luxury from JaKooLit (by Krautt). Solid #040406 bar "
                "with gold accents, center clock framed by gold borders.",
        "preview": (
            "\u25c6 ws1 ws2 ws3  title   "
            "\u2502 12:30 PM  Wed Mar 19 \u2502   gpu cpu mem  vol net  \u23fb"
        ),
    },
    "glass": {
        "name": "Crystal Glass",
        "desc": "True glassmorphism from JaKooLit (by Ahum Maitra). Frosted glass "
                "panels with inner-glow shadows. Adapts to any wallpaper.",
        "preview": (
            " \u25c6 ws1 ws2 ws3  title    "
            " 12:30 PM     cpu mem gpu  vol net tray \u23fb "
        ),
    },
    "monochrome": {
        "name": "Monochrome",
        "desc": "Pure black and white from JaKooLit. Three floating black panels "
                "with white text and thin white bottom borders.",
        "preview": (
            "|\u25c6 ws1 ws2 ws3|   |title...|   "
            "|cpu mem gpu  12:30  vol net  \u23fb|"
        ),
    },
    "half-moon": {
        "name": "Half-Moon",
        "desc": "Individual dark pills from JaKooLit (by TomekBobrowicz). Rainbow "
                "gradient workspace indicators, per-module accent colors.",
        "preview": (
            "(\u25c6) (\u25cf\u25cf\u25cf) (title)   "
            "(gpu) (cpu) (mem) (12:30) (vol) (net) (tray) (\u23fb)"
        ),
    },
}


class WaybarPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp(maximum_size=900)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(28)
        content.set_margin_bottom(28)

        # Header
        hdr = Gtk.Label(label="Waybar Styles", css_classes=['page-header'])
        hdr.set_halign(Gtk.Align.START)
        content.append(hdr)
        sub = Gtk.Label(
            label="Select a bar style. Waybar will restart automatically.",
            css_classes=['page-subheader']
        )
        sub.set_halign(Gtk.Align.START)
        content.append(sub)

        save_panel = Gtk.Expander(label="Save current setup as a profile")
        save_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.profile_name = Gtk.Entry(placeholder_text="Profile name", max_length=80)
        self.profile_description = Gtk.Entry(
            placeholder_text="Description (optional)", max_length=400)
        save_box.append(self.profile_name)
        save_box.append(self.profile_description)
        note = Gtk.Label(
            label="Saved on this device. Includes layout and styling; theme colors and "
                  "helper files remain shared.",
            wrap=True, xalign=0, css_classes=['page-subheader'])
        save_box.append(note)
        save_btn = Gtk.Button(label="Save profile", halign=Gtk.Align.START)
        save_btn.connect('clicked', self._on_save)
        save_box.append(save_btn)
        save_panel.set_child(save_box)
        content.append(save_panel)
        self.status = Gtk.Label(wrap=True, xalign=0, visible=False)
        content.append(self.status)

        # Cards
        state = load_state()
        self.current_style = state.get('waybar_style', 'powerline')

        self.card_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.append(self.card_container)
        self._rebuild_cards()

        clamp.set_child(content)
        scroll.set_child(clamp)
        self.append(scroll)

    def _rebuild_cards(self):
        while child := self.card_container.get_first_child():
            self.card_container.remove(child)
        self.cards = {}
        self.variants = {f"profile:{key}": info for key, info in list_profiles().items()}
        self.variants.update(VARIANTS)
        for variant_id, info in self.variants.items():
            card = self._create_card(variant_id, info)
            self.card_container.append(card)
            self.cards[variant_id] = card

    def _on_save(self, btn):
        try:
            profile_id = save_profile(self.profile_name.get_text(),
                                      self.profile_description.get_text())
            state = load_state()
            state['waybar_style'] = f"profile:{profile_id}"
            save_state(state)
            self.current_style = state['waybar_style']
        except (OSError, ValueError, UnsafeWriteError) as error:
            self._show_status(f"Could not save profile: {error}")
            return
        self._rebuild_cards()
        self.profile_name.set_text("")
        self.profile_description.set_text("")
        self._show_status("Profile saved on this device. Waybar is unchanged.")

    def _show_status(self, text):
        self.status.set_text(text)
        self.status.set_visible(True)

    def _create_card(self, variant_id, info):
        is_active = (variant_id == self.current_style)

        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
            css_classes=['waybar-card'] + (['waybar-card-active'] if is_active else [])
        )

        # Top row: title + status
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title = Gtk.Label(label=info['name'], css_classes=['waybar-card-title'])
        title.set_halign(Gtk.Align.START)
        top.append(title)

        spacer = Gtk.Box(hexpand=True)
        top.append(spacer)

        if is_active:
            check = Gtk.Label(label="\u2713 Active", css_classes=['active-check'])
            top.append(check)
        else:
            directory = self._variant_dir(variant_id)
            available = all((directory / name).is_file()
                            for name in ('config.jsonc', 'style.css'))
            apply_btn = Gtk.Button(
                label="Apply" if available else "Not available",
                css_classes=['suggested-action'] if available else [],
                sensitive=available,
            )
            apply_btn.connect('clicked', self._on_apply, variant_id)
            top.append(apply_btn)

        card.append(top)

        # Description
        desc = Gtk.Label(label=info['desc'], css_classes=['waybar-card-desc'])
        desc.set_halign(Gtk.Align.START)
        desc.set_wrap(True)
        desc.set_max_width_chars(80)
        card.append(desc)

        # Preview
        preview = Gtk.Label(label=info['preview'], css_classes=['waybar-card-preview'])
        preview.set_halign(Gtk.Align.FILL)
        card.append(preview)

        return card

    def _on_apply(self, btn, variant_id):
        try:
            apply_setup(self._variant_dir(variant_id))
        except (OSError, ValueError, UnsafeWriteError) as error:
            self._show_status(f"Could not apply style: {error}")
            return

        # Use the same serialized, all-process restart as the Theming page.
        restart_waybar()

        # Update state
        try:
            state = load_state()
            state['waybar_style'] = variant_id
            save_state(state)
        except (OSError, ValueError, UnsafeWriteError) as error:
            self._show_status(f"Style applied, but selection could not be saved: {error}")
            return
        self.current_style = variant_id

        self._rebuild_cards()
        self._show_status(f"Applied {self.variants[variant_id]['name']}.")

    @staticmethod
    def _variant_dir(variant_id):
        """Prefer a user-customized variant, falling back to the bundled one."""
        if variant_id.startswith('profile:'):
            return profile_dir(variant_id.removeprefix('profile:'))
        user_variant = WAYBAR_VARIANTS_DIR / variant_id
        if user_variant.exists():
            return user_variant
        return BUILTIN_VARIANTS_DIR / variant_id
