from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from audit_taoyuan_festival_assets import CITY, FESTIVALS, all_day_weathers


def ensure_within(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    return resolved


def write_json_atomic(path: Path, data: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def reconcile(root: Path, apply: bool) -> dict[str, object]:
    root = root.resolve()
    manifest_path = root / "qa" / "qualified_assets.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    quarantine = root / "qa" / "rejected" / "historical_weather_ineligible" / stamp
    expected = {festival: set(all_day_weathers(festival)) for festival in FESTIVALS}

    moves: list[tuple[Path, Path]] = []
    for festival in FESTIVALS:
        prefix = f"{festival}_{CITY}_person_all_day_"
        for source in root.glob(f"{prefix}*.png"):
            weather = source.stem.removeprefix(prefix)
            if weather not in expected[festival]:
                moves.append((source, quarantine / festival / source.name))
        expected_sheet = f"{festival}_{CITY}_all_day_{len(expected[festival])}grid.png"
        for source in (root / "qa").glob(f"{festival}_{CITY}_all_day_*grid.png"):
            if source.name != expected_sheet:
                moves.append((source, quarantine / festival / "qa" / source.name))

    retained = []
    removed = []
    for record in manifest.get("qualified_all_day", []):
        festival = record.get("festival")
        if record.get("city") == CITY and festival in expected and record.get("weather") not in expected[festival]:
            removed.append(record)
        else:
            retained.append(record)

    report = {
        "mode": "apply" if apply else "dry-run",
        "quarantine": str(quarantine),
        "moves": [str(source.relative_to(root)) for source, _ in moves],
        "manifest_records_removed": [
            {"festival": row.get("festival"), "weather": row.get("weather"), "asset_file": row.get("asset_file")}
            for row in removed
        ],
    }
    if not apply:
        return report

    backup = manifest_path.with_name(f"qualified_assets.before_history_{CITY}_{stamp}.json")
    shutil.copy2(manifest_path, backup)
    for source, destination in moves:
        ensure_within(source, root)
        ensure_within(destination, root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite quarantine file: {destination}")
        source.replace(destination)
    manifest["qualified_all_day"] = retained
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
