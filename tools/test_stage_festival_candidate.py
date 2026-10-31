from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from stage_festival_candidate import preview_native_mae, stage, stage_gpt
from audit_festival_assets import valid_png


class PreviewNativeMatchTests(unittest.TestCase):
    def test_gpt_native_full_screen_png_is_staged_without_resize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "generated.png"
            Image.new("RGB", (937, 1678), (40, 80, 120)).save(source)
            record = stage_gpt(source, "new_year_Tainan_person_sunset_sunny.png",
                               root / "staging", "Full-size visual QA passed", "gpt-attempt")
            output = root / "staging" / record["filename"]
            self.assertTrue(valid_png(output))
            self.assertEqual(source.read_bytes(), output.read_bytes())
            self.assertEqual(record["native_source_size"], [937, 1678])
            Image.new("RGB", (937, 1678), (120, 80, 40)).save(output)
            self.assertFalse(valid_png(output))

    def test_gpt_preview_size_and_wrong_aspect_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "generated.png"
            for size in ((572, 1024), (1000, 1000)):
                Image.new("RGB", size, (40, 80, 120)).save(source)
                with self.subTest(size=size), self.assertRaisesRegex(ValueError, "full-screen"):
                    stage_gpt(source, "new_year_Tainan_person_sunset_sunny.png",
                              root / "staging", "QA passed", "gpt-attempt")
    def test_matching_preview_is_accepted(self) -> None:
        pixels = Image.new("RGB", (1536, 2752), (45, 80, 120))
        with tempfile.TemporaryDirectory() as directory:
            preview = Path(directory) / "preview.png"
            pixels.resize((363, 649), Image.Resampling.LANCZOS).save(preview)
            self.assertLess(preview_native_mae(preview, pixels), 1)

    def test_unrelated_native_image_is_rejected_by_score(self) -> None:
        pixels = Image.new("RGB", (1536, 2752), (200, 130, 60))
        with tempfile.TemporaryDirectory() as directory:
            preview = Path(directory) / "preview.png"
            Image.new("RGB", (363, 649), (20, 30, 90)).save(preview)
            self.assertGreater(preview_native_mae(preview, pixels), 20)

    def test_jpeg_encoded_browser_screenshot_is_accepted(self) -> None:
        pixels = Image.new("RGB", (1536, 2752), (45, 80, 120))
        with tempfile.TemporaryDirectory() as directory:
            preview = Path(directory) / "preview.png"
            pixels.resize((363, 649), Image.Resampling.LANCZOS).save(
                preview, format="JPEG"
            )
            self.assertLess(preview_native_mae(preview, pixels), 1)

    def test_wrong_aspect_ratio_is_rejected(self) -> None:
        pixels = Image.new("RGB", (1536, 2752), (45, 80, 120))
        with tempfile.TemporaryDirectory() as directory:
            preview = Path(directory) / "preview.png"
            Image.new("RGB", (600, 600), (45, 80, 120)).save(preview)
            with self.assertRaisesRegex(ValueError, "aspect ratio"):
                preview_native_mae(preview, pixels)

    def test_mismatch_requires_independent_native_qa(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jpg"
            preview = root / "preview.png"
            Image.new("RGB", (1536, 2752), (200, 130, 60)).save(source, "JPEG")
            Image.new("RGB", (363, 649), (20, 30, 90)).save(preview)
            with self.assertRaisesRegex(ValueError, "independent native visual QA"):
                stage(source, preview, "halloween_Taichung_person_all_day_light_rain.png",
                      root / "staging", "Preview passed", "https://gemini.google.com/app/test", "attempt")

    def test_documented_native_qa_can_accept_preview_variation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jpg"
            preview = root / "preview.png"
            Image.new("RGB", (1536, 2752), (200, 130, 60)).save(source, "JPEG")
            Image.new("RGB", (363, 649), (20, 30, 90)).save(preview)
            record = stage(source, preview, "halloween_Taichung_person_all_day_light_rain.png",
                           root / "staging", "Preview passed", "https://gemini.google.com/app/test",
                           "attempt", native_qa="Independently inspected the full-size native image")
            self.assertTrue(record["native_preview_variation_accepted"])
            self.assertIn("Independently", record["independent_native_visual_qa"])
            self.assertTrue((root / "staging" / record["filename"]).is_file())


if __name__ == "__main__":
    unittest.main()
