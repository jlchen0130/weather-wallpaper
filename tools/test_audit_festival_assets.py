from __future__ import annotations

import copy
import unittest
from pathlib import Path

import audit_festival_assets as audit


class FestivalAuditTests(unittest.TestCase):
    def test_taichung_ordinary_matrix_is_explicit_and_fail_closed(self) -> None:
        matrix = audit.load_eligibility()
        for festival in audit.FESTIVALS:
            with self.subTest(festival=festival):
                self.assertEqual(
                    audit.all_day_weathers("Taichung", festival, matrix),
                    audit.ORDINARY_ALL_DAY_WEATHERS,
                )
        self.assertEqual(
            audit.audit_festival(Path("Z:/nonexistent-festival-assets"), "Taichung", "new_year")
            ["expected_png_count"],
            15,
        )

    def test_unverified_city_or_festival_cannot_generate(self) -> None:
        with self.assertRaisesRegex(ValueError, "City eligibility is not verified"):
            audit.all_day_weathers("UnverifiedCity", "new_year")
        with self.assertRaisesRegex(ValueError, "Festival eligibility is not verified"):
            audit.all_day_weathers("Taichung", "dragon_boat")

    def test_hsinchu_city_ordinary_matrix_is_explicit_and_fail_closed(self) -> None:
        matrix = audit.load_eligibility()
        for festival in audit.FESTIVALS:
            with self.subTest(festival=festival):
                self.assertEqual(
                    audit.all_day_weathers("HsinchuCity", festival, matrix),
                    audit.ORDINARY_ALL_DAY_WEATHERS,
                )

    def test_incomplete_whitelist_fails_closed(self) -> None:
        matrix = copy.deepcopy(audit.load_eligibility())
        matrix["cities"]["Taichung"]["festivals"]["new_year"]["excluded_adverse"].remove("fog")
        with self.assertRaisesRegex(ValueError, "Adverse whitelist is incomplete"):
            audit.all_day_weathers("Taichung", "new_year", matrix)

    def test_adverse_requires_matching_official_evidence(self) -> None:
        matrix = copy.deepcopy(audit.load_eligibility())
        policy = matrix["cities"]["Taichung"]["festivals"]["new_year"]
        policy["excluded_adverse"].remove("cold_wave")
        policy["eligible_adverse"].append("cold_wave")
        with self.assertRaisesRegex(ValueError, "lacks historical evidence"):
            audit.all_day_weathers("Taichung", "new_year", matrix)

        policy["evidence"]["cold_wave"] = [{
            "date": "2025-12-25", "station_id": "467490", "station_name": "Taichung",
            "measurement": "8 C", "source_url": "https://codis.cwa.gov.tw/StationData",
        }]
        with self.assertRaisesRegex(ValueError, "does not match festival"):
            audit.all_day_weathers("Taichung", "new_year", matrix)

        policy["evidence"]["cold_wave"][0]["date"] = "2025-01-01"
        policy["evidence"]["cold_wave"][0]["source_url"] = "https://codis.cwa.gov.tw.evil.test/"
        with self.assertRaisesRegex(ValueError, "official CWA source"):
            audit.all_day_weathers("Taichung", "new_year", matrix)


if __name__ == "__main__":
    unittest.main()
