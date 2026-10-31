from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import audit_taipei_festival_assets as audit
import audit_newtaipei_festival_assets as newtaipei_audit
import audit_taoyuan_festival_assets as taoyuan_audit
import audit_festival_assets as festival_audit


class FestivalWeatherEligibilityTests(unittest.TestCase):
    def test_tainan_ordinary_weather_only(self) -> None:
        for festival in festival_audit.FESTIVALS:
            with self.subTest(festival=festival):
                self.assertEqual(
                    festival_audit.all_day_weathers("Tainan", festival),
                    ("cloudy", "overcast", "light_rain"),
                )

    def test_kaohsiung_ordinary_weather_only_and_incomplete_policy_fails_closed(self) -> None:
        for festival in festival_audit.FESTIVALS:
            with self.subTest(festival=festival):
                self.assertEqual(
                    festival_audit.all_day_weathers("Kaohsiung", festival),
                    ("cloudy", "overcast", "light_rain"),
                )
        matrix = copy.deepcopy(festival_audit.load_eligibility())
        matrix["cities"]["Kaohsiung"]["festivals"]["new_year"]["excluded_adverse"].remove("fog")
        with self.assertRaisesRegex(ValueError, "whitelist is incomplete"):
            festival_audit.all_day_weathers("Kaohsiung", "new_year", matrix)

    def test_keelung_ordinary_only_and_unverified_city_fails_closed(self) -> None:
        for festival in festival_audit.FESTIVALS:
            with self.subTest(festival=festival):
                self.assertEqual(
                    festival_audit.all_day_weathers("Keelung", festival),
                    ("cloudy", "overcast", "light_rain"),
                )
        with self.assertRaisesRegex(ValueError, "City eligibility is not verified"):
            festival_audit.all_day_weathers("HsinchuCity", "new_year")

    def test_taipei_matrix_uses_only_verified_adverse_weather(self) -> None:
        expected = {
            "new_year": ("cloudy", "overcast", "light_rain", "cold_wave"),
            "valentines_day": ("cloudy", "overcast", "light_rain", "cold_wave"),
            "national_day": (
                "cloudy",
                "overcast",
                "light_rain",
                "heavy_rain",
                "typhoon",
                "strong_wind",
            ),
            "halloween": (
                "cloudy",
                "overcast",
                "light_rain",
                "heavy_rain",
                "typhoon",
                "strong_wind",
            ),
            "constitution_day": (
                "cloudy",
                "overcast",
                "light_rain",
                "cold_wave",
            ),
        }
        for festival, weathers in expected.items():
            with self.subTest(festival=festival):
                self.assertEqual(audit.all_day_weathers(festival), weathers)

    def test_missing_evidence_fails_closed(self) -> None:
        matrix = copy.deepcopy(audit.load_eligibility())
        del matrix["cities"]["Taipei"]["festivals"]["new_year"]["evidence"][
            "cold_wave"
        ]
        with patch.object(audit, "load_eligibility", return_value=matrix):
            with self.assertRaisesRegex(ValueError, "lacks historical evidence"):
                audit.all_day_weathers("new_year")

    def test_unverified_festival_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "not verified"):
            audit.all_day_weathers("dragon_boat")

    def test_newtaipei_matrix_uses_only_verified_adverse_weather(self) -> None:
        expected = {
            "new_year": ("cloudy", "overcast", "light_rain", "cold_wave"),
            "valentines_day": ("cloudy", "overcast", "light_rain", "cold_wave"),
            "national_day": (
                "cloudy",
                "overcast",
                "light_rain",
                "heavy_rain",
                "typhoon",
                "strong_wind",
            ),
            "halloween": (
                "cloudy",
                "overcast",
                "light_rain",
                "heavy_rain",
                "typhoon",
                "strong_wind",
            ),
            "constitution_day": (
                "cloudy",
                "overcast",
                "light_rain",
                "cold_wave",
            ),
        }
        for festival, weathers in expected.items():
            with self.subTest(festival=festival):
                self.assertEqual(newtaipei_audit.all_day_weathers(festival), weathers)

    def test_newtaipei_missing_evidence_fails_closed(self) -> None:
        matrix = copy.deepcopy(newtaipei_audit.load_eligibility())
        del matrix["cities"]["NewTaipei"]["festivals"]["halloween"]["evidence"][
            "typhoon"
        ]
        with patch.object(newtaipei_audit, "load_eligibility", return_value=matrix):
            with self.assertRaisesRegex(ValueError, "lacks historical evidence"):
                newtaipei_audit.all_day_weathers("halloween")

    def test_newtaipei_unverified_festival_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "not verified"):
            newtaipei_audit.all_day_weathers("dragon_boat")

    def test_taoyuan_matrix_uses_only_verified_adverse_weather(self) -> None:
        expected = {
            "new_year": ("cloudy", "overcast", "light_rain", "cold_wave"),
            "valentines_day": ("cloudy", "overcast", "light_rain", "cold_wave"),
            "national_day": ("cloudy", "overcast", "light_rain", "typhoon"),
            "halloween": (
                "cloudy", "overcast", "light_rain", "heavy_rain", "typhoon", "strong_wind"
            ),
            "constitution_day": ("cloudy", "overcast", "light_rain", "cold_wave"),
        }
        for festival, weathers in expected.items():
            with self.subTest(festival=festival):
                self.assertEqual(taoyuan_audit.all_day_weathers(festival), weathers)

    def test_taoyuan_missing_local_typhoon_observation_fails_closed(self) -> None:
        matrix = copy.deepcopy(taoyuan_audit.load_eligibility())
        evidence = matrix["cities"]["Taoyuan"]["festivals"]["national_day"]["evidence"]["typhoon"]
        matrix["cities"]["Taoyuan"]["festivals"]["national_day"]["evidence"]["typhoon"] = [
            record for record in evidence if "official_event" in record
        ]
        with patch.object(taoyuan_audit, "load_eligibility", return_value=matrix):
            with self.assertRaisesRegex(ValueError, "lacks local observation"):
                taoyuan_audit.all_day_weathers("national_day")

    def test_taoyuan_non_official_source_fails_closed(self) -> None:
        matrix = copy.deepcopy(taoyuan_audit.load_eligibility())
        record = matrix["cities"]["Taoyuan"]["festivals"]["new_year"]["evidence"]["cold_wave"][0]
        record["source_url"] = "https://archive-api.open-meteo.com/v1/archive"
        with patch.object(taoyuan_audit, "load_eligibility", return_value=matrix):
            with self.assertRaisesRegex(ValueError, "official CWA source URL"):
                taoyuan_audit.all_day_weathers("new_year")

    def test_taoyuan_incomplete_exclusion_list_fails_closed(self) -> None:
        matrix = copy.deepcopy(taoyuan_audit.load_eligibility())
        matrix["cities"]["Taoyuan"]["festivals"]["new_year"]["excluded_adverse"].remove("fog")
        with patch.object(taoyuan_audit, "load_eligibility", return_value=matrix):
            with self.assertRaisesRegex(ValueError, "whitelist is incomplete"):
                taoyuan_audit.all_day_weathers("new_year")


if __name__ == "__main__":
    unittest.main()
