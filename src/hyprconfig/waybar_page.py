"""HyprConfig — Waybar style cycling page."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

import subprocess
from pathlib import Path

from .parser import WAYBAR_DIR, WAYBAR_VARIANTS_DIR, load_state, save_state
from .theming import restart_waybar
from .paths import BUILTIN_VARIANTS_DIR
from .safe_io import atomic_copy
from .jsonc import loads as load_jsonc

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

        # Cards
        state = load_state()
        self.current_style = state.get('waybar_style', 'powerline')

        self.cards = {}
        for variant_id, info in VARIANTS.items():
            card = self._create_card(variant_id, info)
            content.append(card)
            self.cards[variant_id] = card

        clamp.set_child(content)
        scroll.set_child(clamp)
        self.append(scroll)

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
            available = self._variant_dir(variant_id).exists()
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
        variant_dir = self._variant_dir(variant_id)
        if not variant_dir.exists():
            return

        config_src = variant_dir / 'config.jsonc'
        style_src = variant_dir / 'style.css'
        config_dst = WAYBAR_DIR / 'config.jsonc'
        style_dst = WAYBAR_DIR / 'style.css'

        # Copy variant files
        WAYBAR_DIR.mkdir(parents=True, exist_ok=True)
        if config_src.exists():
            load_jsonc(config_src.read_text())
            atomic_copy(config_src, config_dst)
        if style_src.exists():
            atomic_copy(style_src, style_dst)

        # Use the same serialized, all-process restart as the Theming page.
        restart_waybar()

        # Update state
        state = load_state()
        state['waybar_style'] = variant_id
        save_state(state)
        self.current_style = variant_id

        # Update card visuals
        self._refresh_cards()

        btn.set_label("Applied \u2713")
        btn.set_sensitive(False)
        GLib.timeout_add(1500, lambda: (btn.set_label("Apply"), btn.set_sensitive(True)))

    @staticmethod
    def _variant_dir(variant_id):
        """Prefer a user-customized variant, falling back to the bundled one."""
        user_variant = WAYBAR_VARIANTS_DIR / variant_id
        if user_variant.exists():
            return user_variant
        return BUILTIN_VARIANTS_DIR / variant_id

    def _refresh_cards(self):
        """Rebuild card active states."""
        for vid, card in self.cards.items():
            if vid == self.current_style:
                card.add_css_class('waybar-card-active')
            else:
                card.remove_css_class('waybar-card-active')
