from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from audit_taipei_festival_assets import CITY, FESTIVALS, all_day_weathers


def ensure_within(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    return resolved


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, data: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def reconcile(root: Path, apply: bool) -> dict[str, object]:
    root = root.resolve()
    manifest_path = root / "qa" / "qualified_assets.json"
    manifest = load_json(manifest_path)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    quarantine = root / "qa" / "rejected" / "historical_weather_ineligible" / stamp

    expected = {festival: set(all_day_weathers(festival)) for festival in FESTIVALS}
    files_to_move: list[tuple[Path, Path]] = []
    old_sheets_to_move: list[tuple[Path, Path]] = []

    for festival in FESTIVALS:
        prefix = f"{festival}_{CITY}_person_all_day_"
        for source in root.glob(f"{prefix}*.png"):
            weather = source.stem.removeprefix(prefix)
            if weather not in expected[festival]:
                destination = quarantine / festival / source.name
                files_to_move.append((source, destination))

        expected_sheet = f"{festival}_{CITY}_all_day_{len(expected[festival])}grid.png"
        for source in (root / "qa").glob(f"{festival}_{CITY}_all_day_*grid.png"):
            if source.name != expected_sheet:
                destination = quarantine / festival / "qa" / source.name
                old_sheets_to_move.append((source, destination))

    original_all_day = list(manifest.get("qualified_all_day", []))
    retained_all_day = []
    removed_records = []
    updated_records = 0
    for record in original_all_day:
        festival = record.get("festival")
        if record.get("city") != CITY or festival not in expected:
            retained_all_day.append(record)
            continue
        if record.get("weather") not in expected[festival]:
            removed_records.append(record)
            continue
        expected_qa = f"{festival}_{CITY}_all_day_{len(expected[festival])}grid.png"
        if record.get("qa_file") != expected_qa:
            record = dict(record)
            record["qa_file"] = expected_qa
            record["historical_weather_policy"] = (
                "adverse weather retained only with CWA historical evidence"
            )
            updated_records += 1
        retained_all_day.append(record)

    report = {
        "mode": "apply" if apply else "dry-run",
        "quarantine": str(quarantine),
        "asset_moves": [str(source.relative_to(root)) for source, _ in files_to_move],
        "qa_moves": [str(source.relative_to(root)) for source, _ in old_sheets_to_move],
        "manifest_records_removed": [
            {
                "festival": record.get("festival"),
                "weather": record.get("weather"),
                "asset_file": record.get("asset_file"),
            }
            for record in removed_records
        ],
        "manifest_records_updated": updated_records,
    }
    if not apply:
        return report

    backup = manifest_path.with_name(f"qualified_assets.before_history_{stamp}.json")
    shutil.copy2(manifest_path, backup)
    for source, destination in files_to_move + old_sheets_to_move:
        ensure_within(source, root)
        ensure_within(destination, root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite quarantine file: {destination}")
        source.replace(destination)

    manifest["qualified_all_day"] = retained_all_day
    write_json_atomic(manifest_path, manifest)
    report["manifest_backup"] = str(backup)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(reconcile(args.root, args.apply), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
