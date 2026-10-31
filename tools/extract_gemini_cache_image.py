from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image


EXPECTED_SIZE = (1536, 2752)


@dataclass(frozen=True)
class CacheEntry:
    size: int
    mtime_ns: int


def cache_entries(cache_dir: Path) -> dict[str, CacheEntry]:
    return {
        path.name: CacheEntry(path.stat().st_size, path.stat().st_mtime_ns)
        for path in cache_dir.glob("f_*")
        if path.is_file()
    }


def write_snapshot(cache_dir: Path, output: Path) -> None:
    entries = cache_entries(cache_dir)
    payload = {
        "cache_dir": str(cache_dir.resolve()),
        "created_ns": time.time_ns(),
        "entries": {name: asdict(entry) for name, entry in entries.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_snapshot(path: Path, cache_dir: Path) -> dict[str, CacheEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    recorded_dir = Path(payload["cache_dir"])
    if recorded_dir.resolve() != cache_dir.resolve():
        raise ValueError("Snapshot belongs to a different cache directory")
    return {
        name: CacheEntry(int(value["size"]), int(value["mtime_ns"]))
        for name, value in payload["entries"].items()
    }


def is_original_jpeg(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.load()
            return image.format == "JPEG" and image.size == EXPECTED_SIZE
    except (OSError, ValueError):
        return False


def is_valid_png(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.load()
            return image.format == "PNG" and image.size == EXPECTED_SIZE
    except (OSError, ValueError):
        return False


def changed_candidates(
    cache_dir: Path, baseline: dict[str, CacheEntry]
) -> list[Path]:
    current = cache_entries(cache_dir)
    changed = [
        cache_dir / name
        for name, entry in current.items()
        if baseline.get(name) != entry and is_original_jpeg(cache_dir / name)
    ]
    return sorted(changed, key=lambda path: path.stat().st_mtime_ns, reverse=True)


def wait_for_candidate(
    cache_dir: Path,
    baseline: dict[str, CacheEntry],
    timeout_seconds: float,
    poll_seconds: float,
    stability_seconds: float,
) -> Path:
    deadline = time.monotonic() + timeout_seconds
    stable_path: Path | None = None
    stable_entry: CacheEntry | None = None
    stable_since = 0.0

    while time.monotonic() < deadline:
        candidates = changed_candidates(cache_dir, baseline)
        if len(candidates) > 1:
            names = ", ".join(path.name for path in candidates)
            raise RuntimeError(f"Ambiguous original-size cache candidates: {names}")
        if candidates:
            candidate = candidates[0]
            stat = candidate.stat()
            entry = CacheEntry(stat.st_size, stat.st_mtime_ns)
            now = time.monotonic()
            if candidate == stable_path and entry == stable_entry:
                if now - stable_since >= stability_seconds:
                    return candidate
            else:
                stable_path = candidate
                stable_entry = entry
                stable_since = now
        time.sleep(poll_seconds)

    raise TimeoutError("No new stable 1536x2752 JPEG appeared in the cache")


def convert_atomically(source: Path, destination: Path) -> None:
    if destination.exists():
        if is_valid_png(destination):
            return
        raise FileExistsError(f"Destination exists but is not a valid wallpaper: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        with Image.open(source) as image:
            image.load()
            if image.format != "JPEG" or image.size != EXPECTED_SIZE:
                raise ValueError(
                    f"Invalid source image: format={image.format} size={image.size}"
                )
            image.convert("RGB").save(temporary, "PNG", optimize=True)
        if not is_valid_png(temporary):
            raise ValueError("Converted PNG failed validation")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely extract a Gemini original image from the Codex browser cache."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("cache_dir", type=Path)
    snapshot_parser.add_argument("snapshot", type=Path)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("cache_dir", type=Path)
    extract_parser.add_argument("snapshot", type=Path)
    extract_parser.add_argument("destination", type=Path)
    extract_parser.add_argument("--timeout", type=float, default=180.0)
    extract_parser.add_argument("--poll", type=float, default=1.0)
    extract_parser.add_argument("--stability", type=float, default=2.0)

    args = parser.parse_args()
    if args.command == "snapshot":
        write_snapshot(args.cache_dir, args.snapshot)
        print(json.dumps({"status": "snapshot_created", "path": str(args.snapshot)}))
        return

    if is_valid_png(args.destination):
        print(json.dumps({"status": "already_valid", "path": str(args.destination)}))
        return
    baseline = read_snapshot(args.snapshot, args.cache_dir)
    source = wait_for_candidate(
        args.cache_dir, baseline, args.timeout, args.poll, args.stability
    )
    convert_atomically(source, args.destination)
    print(
        json.dumps(
            {
                "status": "converted",
                "source": str(source),
                "destination": str(args.destination),
                "size": list(EXPECTED_SIZE),
            }
        )
    )


if __name__ == "__main__":
    main()
