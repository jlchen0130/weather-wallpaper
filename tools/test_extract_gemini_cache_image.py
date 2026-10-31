from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from extract_gemini_cache_image import (
    CacheEntry,
    changed_candidates,
    convert_atomically,
    is_valid_png,
)


class ExtractGeminiCacheImageTests(unittest.TestCase):
    def make_jpeg(self, path: Path, color: str) -> None:
        Image.new("RGB", (1536, 2752), color).save(path, "JPEG", quality=90)

    def test_extracts_one_changed_original(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "f_000001"
            self.make_jpeg(source, "red")
            candidates = changed_candidates(root, {})
            self.assertEqual(candidates, [source])

            destination = root / "wallpaper.png"
            convert_atomically(source, destination)
            self.assertTrue(is_valid_png(destination))

    def test_ignores_unchanged_cache_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "f_000001"
            self.make_jpeg(source, "blue")
            stat = source.stat()
            baseline = {
                source.name: CacheEntry(stat.st_size, stat.st_mtime_ns),
            }
            self.assertEqual(changed_candidates(root, baseline), [])

    def test_reports_multiple_changed_originals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "f_000001"
            second = root / "f_000002"
            self.make_jpeg(first, "green")
            self.make_jpeg(second, "yellow")
            self.assertEqual(len(changed_candidates(root, {})), 2)


if __name__ == "__main__":
    unittest.main()
