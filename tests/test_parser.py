import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hyprconfig import parser
from hyprconfig import safe_io
from hyprconfig.jsonc import loads as load_jsonc


class ParserTests(unittest.TestCase):
    def test_resolve_nested_variables(self):
        variables = {"mainMod": "Super", "combo": "$mainMod Shift"}
        self.assertEqual(parser.resolve_vars("$combo Q", variables), "Super Shift Q")

    def test_parse_described_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "keybindings.conf"
            conf.write_text(
                "$mainMod = SUPER\n"
                "$d=[Windows|Focus]\n"
                "bindd = $mainMod SHIFT, H, focus left, movefocus, l\n"
            )
            binds = parser.parse_keybindings([conf])

        self.assertEqual(len(binds), 1)
        self.assertEqual(binds[0].mods, "SUPER SHIFT")
        self.assertEqual(binds[0].key, "H")
        self.assertEqual(binds[0].description, "focus left")
        self.assertEqual(binds[0].dispatcher, "movefocus")
        self.assertEqual(binds[0].args, "l")
        self.assertEqual(binds[0].group, "Windows")
        self.assertEqual(binds[0].subgroup, "Focus")

    def test_discovers_stock_source_graph_and_rewrites_with_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main = root / "hyprland.conf"
            included = root / "conf.d" / "keys.conf"
            included.parent.mkdir()
            main.write_text("source = conf.d/*.conf\n")
            included.write_text("bind = SUPER, Q, exec, foot\n")
            backups = root / "backups"

            with (
                patch.object(parser, "HYPRLAND_CONF", main),
                patch.object(parser, "HYPR_DIR", root),
                patch.object(safe_io, "BACKUP_DIR", backups),
                patch.object(safe_io, "HOME", root),
            ):
                binds = parser.parse_keybindings()
                changed = parser.rewrite_bind(binds[0], "SUPER SHIFT", "Q")

            self.assertTrue(changed)
            self.assertIn("bind = SUPER SHIFT, Q, exec, foot", included.read_text())
            self.assertTrue(any(backups.rglob("keys.conf")))

    def test_conflicts_ignore_consecutive_chains(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "keybindings.conf"
            conf.write_text(
                "bindd = SUPER, H, first, movefocus, l\n"
                "bindd = SUPER, H, second, bringactivetotop\n"
            )
            binds = parser.parse_keybindings([conf])
        self.assertEqual(parser.find_conflicts(binds), {})

    def test_state_migrates_from_old_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            new_state = root / "hyprconfig" / "state.json"
            old_state = root / "hyperconfig" / "state.json"
            old_state.parent.mkdir(parents=True)
            old_state.write_text(json.dumps({"matugen_enabled": False}))

            with (
                patch.object(parser, "STATE_FILE", new_state),
                patch.object(parser, "LEGACY_STATE_FILE", old_state),
            ):
                state = parser.load_state()

            self.assertEqual(state["theme"]["palette"], "gold")
            self.assertTrue(new_state.exists())

    def test_state_drops_retired_wallpaper_selector(self):
        state = {
            "matugen_enabled": False,
            "theme": {
                **parser.DEFAULT_THEME,
                "wallpaper": "matrix-" + "rain",
            },
        }

        migrated, changed = parser._migrate_theme(state)

        self.assertTrue(changed)
        self.assertNotIn("wallpaper", migrated["theme"])

    def test_managed_config_is_sourced_and_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main = root / "hyprland.conf"
            managed = root / "hyprconfig.conf"
            backups = root / "backups"
            main.write_text("# existing configuration\n")

            settings = {
                "rounding": 8,
                "active_opacity": 1.0,
                "inactive_opacity": 0.9,
                "blur_enabled": True,
                "blur_size": 5,
                "blur_passes": 2,
                "shadow_enabled": True,
                "shadow_range": 10,
                "shadow_render_power": 3,
            }
            with (
                patch.object(parser, "HYPR_DIR", root),
                patch.object(parser, "HYPRLAND_CONF", main),
                patch.object(parser, "MANAGED_CONF", managed),
                patch.object(safe_io, "BACKUP_DIR", backups),
                patch.object(safe_io, "HOME", root),
            ):
                parser.persist_decoration(settings)
                parser.persist_borders("rgba(ffffffff)", "rgba(000000ff)")

            self.assertIn(f"source = {managed}", main.read_text())
            managed_text = managed.read_text()
            self.assertIn("# BEGIN HyprConfig: decoration", managed_text)
            self.assertIn("# BEGIN HyprConfig: borders", managed_text)
            self.assertTrue(any(backups.rglob("hyprland.conf")))
            self.assertTrue(any(backups.rglob("hyprconfig.conf")))

    def test_atomic_write_failure_preserves_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "settings.conf"
            target.write_text("original\n")
            with patch.object(safe_io.os, "replace", side_effect=OSError("interrupted")):
                with self.assertRaisesRegex(OSError, "interrupted"):
                    safe_io.atomic_write_text(target, "replacement\n", backup=False)

            self.assertEqual(target.read_text(), "original\n")
            self.assertEqual(list(target.parent.glob(".settings.conf.*")), [])

    def test_atomic_write_refuses_symbolic_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "original.conf"
            link = root / "settings.conf"
            original.write_text("original\n")
            link.symlink_to(original)

            with self.assertRaises(safe_io.UnsafeWriteError):
                safe_io.atomic_write_text(link, "replacement\n")

            self.assertEqual(original.read_text(), "original\n")

    def test_bundled_waybar_configs_have_no_machine_specific_helpers(self):
        variants = Path(__file__).parents[1] / "src" / "hyprconfig" / "data" / "waybar"
        forbidden = ("custom/gpu", "gpu.sh", "nvidia-smi", "calendar-popup.sh")
        for path in variants.rglob("config.jsonc"):
            text = path.read_text()
            self.assertIsInstance(load_jsonc(text), dict)
            for value in forbidden:
                self.assertNotIn(value, text, path)

    def test_repository_has_no_retired_wallpaper_assets(self):
        asset_dir = Path(__file__).parents[1] / "src" / "hyprconfig" / "data" / "matrix-assets"
        self.assertFalse(asset_dir.exists())

    def test_repository_has_no_old_product_spelling_or_absolute_home(self):
        root = Path(__file__).parents[1]
        text_extensions = {
            ".py", ".md", ".sh", ".toml", ".yml", ".yaml", ".json", ".jsonc",
            ".css", ".desktop", ".txt", ".frag", ".hook",
        }
        for path in root.rglob("*"):
            if {".git", ".venv", "build", "dist"}.intersection(path.parts):
                continue
            if not path.is_file() or path.suffix not in text_extensions:
                continue
            text = path.read_text(errors="replace")
            self.assertNotIn("Hyper" + "Config", text, path)
            self.assertNotIn("/ho" + "me/", text, path)


if __name__ == "__main__":
    unittest.main()
