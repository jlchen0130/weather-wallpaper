from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from PIL import Image


EXPECTED_SIZE = (1536, 2752)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--no-optimize", action="store_true")
    args = parser.parse_args()

    if args.dest.exists() and not args.replace:
        raise FileExistsError(f"Destination already exists: {args.dest}")

    with Image.open(args.source) as image:
        if image.format not in {"JPEG", "PNG"} or image.size != EXPECTED_SIZE:
            raise ValueError(f"Invalid source: {image.format} {image.size}")
        rgb = image.convert("RGB")

    args.dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{args.dest.stem}.",
        suffix=".tmp.png",
        dir=args.dest.parent,
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        save_options = {"optimize": True}
        if args.no_optimize:
            save_options = {"optimize": False, "compress_level": 1}
        rgb.save(tmp_path, "PNG", **save_options)
        with Image.open(tmp_path) as check:
            if check.format != "PNG" or check.size != EXPECTED_SIZE:
                raise ValueError(f"Invalid output: {check.format} {check.size}")
        os.replace(tmp_path, args.dest)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    with Image.open(args.dest) as final:
        print(f"{args.dest}")
        print(f"{final.format} {final.size} {args.dest.stat().st_size}")


if __name__ == "__main__":
    main()
