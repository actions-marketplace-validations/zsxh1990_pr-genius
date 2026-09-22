#!/usr/bin/env python3
"""Sync version from prgenius/pyproject.toml to all downstream files.

Eliminates version drift between pyproject.toml (canonical source) and:
  - server.json (MCP server manifest)
  - glama.json (Glama directory listing)
  - package.json (npm/DSH metadata)
  - Dockerfile (LABEL + comment header)

Usage:
    python3 scripts/sync_version.py            # dry-run (print diffs; exit 1 on drift)
    python3 scripts/sync_version.py --apply    # write changes to disk
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_version() -> str:
    """Read canonical version from prgenius/pyproject.toml."""
    pyproject = ROOT / "prgenius" / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"(.+?)"', text, re.MULTILINE)
    if not match:
        print("ERROR: cannot read version from prgenius/pyproject.toml", file=sys.stderr)
        sys.exit(1)
    return match.group(1)


def _check_json(path: Path, version: str) -> list[str]:
    """Check a JSON file's version field. Returns list of drift messages."""
    if not path.exists():
        return [f"{path.name}: file not found"]
    data = json.loads(path.read_text(encoding="utf-8"))
    old = data.get("version", "???")
    drifts = []
    if old != version:
        drifts.append(f"{path.name}: version {old} -> {version}")
    return drifts


def _check_server_json(path: Path, version: str) -> list[str]:
    """Check server.json: top-level version AND packages[0].version."""
    if not path.exists():
        return ["server.json: file not found"]
    data = json.loads(path.read_text(encoding="utf-8"))
    drifts = []
    old_top = data.get("version", "???")
    if old_top != version:
        drifts.append(f"server.json: version {old_top} -> {version}")
    pkgs = data.get("packages", [])
    if pkgs:
        old_pkg = pkgs[0].get("version", "???")
        if old_pkg != version:
            drifts.append(f"server.json: packages[0].version {old_pkg} -> {version}")
    return drifts


def _check_dockerfile(path: Path, version: str) -> list[str]:
    """Check Dockerfile: LABEL version= line."""
    if not path.exists():
        return ["Dockerfile: file not found"]
    text = path.read_text(encoding="utf-8")
    m = re.search(r'^LABEL\s+version="(.*?)"', text, re.MULTILINE)
    old = m.group(1) if m else "???"
    if old != version:
        return [f"Dockerfile: LABEL version {old} -> {version}"]
    return []



def _apply_server_json(path: Path, version: str) -> tuple[bool, str]:
    """Update server.json: top-level version AND packages[0].version."""
    data = json.loads(path.read_text(encoding="utf-8"))
    changes = []
    old_top = data.get("version", "")
    if old_top != version:
        data["version"] = version
        changes.append(f"version {old_top} -> {version}")
    pkgs = data.get("packages", [])
    if pkgs:
        old_pkg = pkgs[0].get("version", "")
        if old_pkg != version:
            pkgs[0]["version"] = version
            changes.append(f"packages[0].version {old_pkg} -> {version}")
    if not changes:
        return False, f"{path.name}: already {version}"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True, f"{path.name}: {'; '.join(changes)}"


def _apply_json_simple(path: Path, version: str) -> tuple[bool, str]:
    """Update a top-level version key in a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    old = data.get("version", "")
    if old == version:
        return False, f"{path.name}: already {version}"
    data["version"] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True, f"{path.name}: {old} -> {version}"


def _apply_dockerfile(path: Path, version: str) -> tuple[bool, str]:
    """Update Dockerfile: LABEL version= line and top-comment version reference."""
    text = path.read_text(encoding="utf-8")
    original = text
    text = re.sub(
        r'^(LABEL\s+version=)".*?"',
        rf'\g<1>"{version}"',
        text, count=1, flags=re.MULTILINE,
    )
    text = re.sub(
        r'(# Dockerfile for .+? —\s*)v[\d.]+',
        rf'\g<1>v{version}',
        text, count=1,
    )
    if text == original:
        return False, "Dockerfile: already in sync"
    path.write_text(text, encoding="utf-8")
    return True, f"Dockerfile: updated to v{version}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync version from pyproject.toml to downstream files")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default: dry-run)")
    args = parser.parse_args()

    version = _read_version()
    print(f"Canonical version (prgenius/pyproject.toml): {version}\n")

    if args.apply:
        any_changed = False
        for fn in [
            lambda: _apply_server_json(ROOT / "server.json", version),
            lambda: _apply_json_simple(ROOT / "glama.json", version),
            lambda: _apply_json_simple(ROOT / "package.json", version),
            lambda: _apply_dockerfile(ROOT / "Dockerfile", version),
        ]:
            changed, msg = fn()
            print(f"  [{'UPDATED' if changed else 'OK'}] {msg}")
            if changed:
                any_changed = True
        print(f"\n{'All files synced.' if any_changed else 'All files already in sync.'}")
        return 0

    # Dry-run: check for drift, exit 1 if any
    all_drifts: list[str] = []
    all_drifts.extend(_check_server_json(ROOT / "server.json", version))
    all_drifts.extend(_check_json(ROOT / "glama.json", version))
    all_drifts.extend(_check_json(ROOT / "package.json", version))
    all_drifts.extend(_check_dockerfile(ROOT / "Dockerfile", version))

    if all_drifts:
        print("DRIFT DETECTED:")
        for d in all_drifts:
            print(f"  {d}")
        print("\nRun with --apply to fix.")
        return 1

    print("All files in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
