from __future__ import annotations

import argparse
from pathlib import Path

import build_newtaipei_festival_contact_sheets as builder
from audit_taoyuan_festival_assets import CITY, REGULAR_WEATHERS, all_day_weathers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("festival")
    args = parser.parse_args()

    # The rendering implementation is shared; only the exact city token differs.
    builder.CITY = CITY
    qa_dir = args.source_dir / "qa"
    for weather in REGULAR_WEATHERS:
        builder.build_regular_sheet(
            args.source_dir,
            args.festival,
            weather,
            qa_dir / f"{args.festival}_{CITY}_{weather}_6grid.png",
        )
    builder.all_day_weathers = all_day_weathers
    builder.build_all_day_sheet(
        args.source_dir,
        args.festival,
        qa_dir / f"{args.festival}_{CITY}_all_day_{len(all_day_weathers(args.festival))}grid.png",
    )


if __name__ == "__main__":
    main()
