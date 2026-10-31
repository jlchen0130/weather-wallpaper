import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import reqa_kaohsiung_weather as workflow


class KaohsiungWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary_parent = Path(__file__).resolve().parent / ".test-tmp"
        temporary_parent.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_parent)
        self.root = Path(self.temporary.name)
        checkpoint = {
            "city": workflow.CITY,
            "scope": workflow.SCOPE,
            "status": "in_progress",
            "finalized": False,
            "accepted_replacements": {},
            "rejected_candidates": [],
            "failed_quarantined": {},
        }
        path = workflow.paths(self.root)["checkpoint"]
        workflow.atomic_json(path, checkpoint)
        self.target = workflow.regular_name("partly_cloudy", "sunrise")
        self.prompt = "unique test prompt"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def image(self, name: str, size: tuple[int, int], image_format: str) -> Path:
        path = self.root / name
        Image.new("RGB", size, "navy").save(path, image_format)
        return path

    def checkpoint(self) -> dict[str, object]:
        return json.loads(
            workflow.paths(self.root)["checkpoint"].read_text(encoding="utf-8")
        )

    def test_browser_screenshot_cannot_be_preview_rejected(self) -> None:
        workflow.begin_attempt(self.root, "attempt-1", self.target, self.prompt)
        screenshot = self.image("viewport.png", (1280, 720), "PNG")

        with self.assertRaisesRegex(ValueError, "browser viewport screenshots"):
            workflow.preview_reject(self.root, screenshot, "attempt-1", "not enough subjects")

        checkpoint = self.checkpoint()
        self.assertEqual([], checkpoint["rejected_candidates"])
        self.assertEqual("started", checkpoint["candidate_attempts"]["attempt-1"]["status"])

    def test_ingest_requires_preview_pass(self) -> None:
        workflow.begin_attempt(self.root, "attempt-2", self.target, self.prompt)
        native = self.image("native.jpg", workflow.SIZE, "JPEG")

        with self.assertRaisesRegex(RuntimeError, "preview-passed"):
            workflow.ingest(
                self.root, native, self.target, "looks good", self.prompt, "attempt-2"
            )

    def test_quota_block_does_not_create_visual_rejection(self) -> None:
        workflow.begin_attempt(self.root, "attempt-3", self.target, self.prompt)
        workflow.quota_blocked(self.root, "attempt-3", "Gemini explicitly reported quota")

        checkpoint = self.checkpoint()
        self.assertEqual([], checkpoint["rejected_candidates"])
        self.assertEqual(
            "quota_blocked", checkpoint["candidate_attempts"]["attempt-3"]["status"]
        )

    def test_generation_failure_keeps_evidence_and_allows_new_attempt(self) -> None:
        workflow.begin_attempt(self.root, "stopped", self.target, self.prompt)
        screenshot = self.image("stopped-page.jpg", (1280, 720), "JPEG")

        workflow.generation_failed(
            self.root, "stopped", "Gemini stopped without an image", screenshot
        )
        workflow.begin_attempt(self.root, "retry", self.target, "new unique prompt")

        checkpoint = self.checkpoint()
        failure = checkpoint["candidate_attempts"]["stopped"]
        self.assertEqual("generation_failed", failure["status"])
        self.assertEqual([], checkpoint["rejected_candidates"])
        self.assertEqual("started", checkpoint["candidate_attempts"]["retry"]["status"])
        evidence = self.root / failure["generation_failure"]["evidence_file"]
        self.assertTrue(evidence.is_file())
        self.assertEqual(workflow.sha256(screenshot), workflow.sha256(evidence))

    def test_full_preview_allows_native_ingest(self) -> None:
        workflow.begin_attempt(self.root, "attempt-4", self.target, self.prompt)
        preview = self.image("preview.jpg", (572, 1024), "JPEG")
        native = self.image("native.jpg", workflow.SIZE, "JPEG")

        workflow.preview_pass(self.root, preview, "attempt-4", "full candidate passed")
        workflow.ingest(
            self.root, native, self.target, "native candidate passed", self.prompt, "attempt-4"
        )

        checkpoint = self.checkpoint()
        accepted = checkpoint["accepted_replacements"][self.target]
        self.assertEqual("attempt-4", accepted["attempt_id"])
        self.assertEqual("accepted", checkpoint["candidate_attempts"]["attempt-4"]["status"])
        staged = workflow.stage_path(workflow.paths(self.root)["stage"], self.target)
        workflow.validate_png(staged)

    def test_complete_element_crop_is_valid_preview_evidence(self) -> None:
        workflow.begin_attempt(self.root, "attempt-5", self.target, self.prompt)
        preview = self.image("element-crop.png", (265, 474), "PNG")

        workflow.preview_reject(
            self.root, preview, "attempt-5", "animals are oversized in the full image"
        )

        checkpoint = self.checkpoint()
        record = checkpoint["rejected_candidates"][0]
        self.assertEqual("attempt-5", record["attempt_id"])
        self.assertTrue(record["file"].endswith("attempt-5.png"))


if __name__ == "__main__":
    unittest.main()
