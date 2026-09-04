import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hyprconfig import safe_io
from hyprconfig import waybar_profiles as profiles


class WaybarProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.waybar = self.root / "waybar"
        self.waybar.mkdir()
        self.saved = self.root / "profiles"
        self.backups = self.root / "backups"
        for obj, name, value in (
            (profiles, "WAYBAR_DIR", self.waybar),
            (profiles, "WAYBAR_PROFILES_DIR", self.saved),
            (safe_io, "BACKUP_DIR", self.backups),
            (safe_io, "HOME", self.root),
        ):
            patcher = patch.object(obj, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # Synthetic multi-monitor data only; never copy a real user's dotfiles.
        self.config = b'[\n{"height":24}, // full bar\n{"height":3}\n]\n'
        self.css = b'@import "theme.css";\n* { font-size: 14px; }\n'
        (self.waybar / "config.jsonc").write_bytes(self.config)
        (self.waybar / "style.css").write_bytes(self.css)

    def test_save_discover_and_restore_preserves_bytes_and_shared_files(self):
        (self.waybar / "theme.css").write_text("/* shared palette */")
        (self.waybar / "helper.sh").write_text("exit 0\n")
        key = profiles.save_profile("Compact strips", "One full bar and thin indicators")
        self.assertEqual(profiles.list_profiles()[key]["name"], "Compact strips")
        saved = profiles.profile_dir(key)
        self.assertEqual({p.name for p in saved.iterdir()},
                         {"config.jsonc", "style.css", "profile.json"})
        self.assertEqual((saved.stat().st_mode & 0o777), 0o700)
        self.assertEqual((saved / "config.jsonc").stat().st_mode & 0o777, 0o600)
        (self.waybar / "config.jsonc").write_text('{"height":40}')
        (self.waybar / "style.css").write_text("/* different style */")
        profiles.apply_setup(saved)
        self.assertEqual((self.waybar / "config.jsonc").read_bytes(), self.config)
        self.assertEqual((self.waybar / "style.css").read_bytes(), self.css)
        self.assertEqual((self.waybar / "theme.css").read_text(), "/* shared palette */")
        self.assertEqual((self.waybar / "helper.sh").read_text(), "exit 0\n")
        self.assertTrue(any(self.backups.rglob("config.jsonc")))
        self.assertTrue(any(self.backups.rglob("style.css")))

    def test_missing_stylesheet_does_not_partially_replace_active_config(self):
        key = profiles.save_profile("Saved")
        saved = profiles.profile_dir(key)
        (saved / "style.css").unlink()
        (self.waybar / "config.jsonc").write_text('{}')
        with self.assertRaises(ValueError):
            profiles.apply_setup(saved)
        self.assertEqual((self.waybar / "config.jsonc").read_text(), '{}')

    def test_failed_second_write_rolls_back_both_files(self):
        key = profiles.save_profile("Saved")
        (self.waybar / "config.jsonc").write_text('{}')
        (self.waybar / "style.css").write_text("/* before */")
        real_write = profiles.atomic_write_bytes
        calls = 0

        def fail_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated write failure")
            return real_write(*args, **kwargs)

        with patch.object(profiles, "atomic_write_bytes", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "simulated"):
                profiles.apply_setup(profiles.profile_dir(key))
        self.assertEqual((self.waybar / "config.jsonc").read_text(), '{}')
        self.assertEqual((self.waybar / "style.css").read_text(), "/* before */")

    def test_invalid_json_or_config_shape_is_not_saved(self):
        for text in ('{broken', 'null', '[]', '[1]', '"string"'):
            with self.subTest(text=text):
                (self.waybar / "config.jsonc").write_text(text)
                with self.assertRaises(ValueError):
                    profiles.save_profile("Invalid")
                self.assertEqual(profiles.list_profiles(), {})

    def test_save_accepts_extensionless_config(self):
        (self.waybar / "config.jsonc").rename(self.waybar / "config")
        key = profiles.save_profile("Extensionless")
        self.assertEqual((profiles.profile_dir(key) / "config.jsonc").read_bytes(), self.config)

    def test_duplicate_names_create_distinct_snapshots_and_names_are_not_paths(self):
        first = profiles.save_profile("../display setup")
        second = profiles.save_profile("../display setup")
        self.assertNotEqual(first, second)
        self.assertEqual(len(profiles.list_profiles()), 2)
        with self.assertRaises(ValueError):
            profiles.profile_dir("../outside")

    def test_destination_symlink_is_rejected_before_any_writes(self):
        key = profiles.save_profile("Saved")
        outside = self.root / "outside.css"
        outside.write_text("untouched")
        (self.waybar / "style.css").unlink()
        (self.waybar / "style.css").symlink_to(outside)
        (self.waybar / "config.jsonc").write_text('{}')
        with self.assertRaises(safe_io.UnsafeWriteError):
            profiles.apply_setup(profiles.profile_dir(key))
        self.assertEqual((self.waybar / "config.jsonc").read_text(), '{}')
        self.assertEqual(outside.read_text(), "untouched")

    def test_symlinked_profile_and_damaged_metadata_are_ignored(self):
        key = profiles.save_profile("Saved")
        (self.saved / ("a" * 32)).symlink_to(profiles.profile_dir(key), target_is_directory=True)
        self.assertEqual(len(profiles.list_profiles()), 1)
        metadata = profiles.profile_dir(key) / "profile.json"
        for data in ('{broken', '[]', json.dumps({"name": 2, "version": 1})):
            metadata.write_text(data)
            self.assertEqual(profiles.list_profiles(), {})

    def test_failed_save_leaves_no_discoverable_partial_profile(self):
        with patch.object(profiles, "atomic_write_bytes", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                profiles.save_profile("Not saved")
        self.assertEqual(list(self.saved.iterdir()), [])

    def test_blank_name_and_large_files_are_rejected(self):
        with self.assertRaises(ValueError):
            profiles.save_profile("   ")
        with patch.object(profiles, "MAX_FILE_SIZE", 1):
            with self.assertRaises(ValueError):
                profiles.save_profile("Too large")


if __name__ == "__main__":
    unittest.main()
