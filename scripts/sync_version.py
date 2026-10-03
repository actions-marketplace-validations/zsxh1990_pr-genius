#!/usr/bin/env python3
"""Sync version from prgenius/pyproject.toml to all downstream files.

Eliminates version drift between pyproject.toml (canonical source) and:
  - server.json (MCP server manifest)
  - glama.json (Glama directory listing)
  - package.json (npm/DSH metadata)
  - Dockerfile (LABEL + comment header)
  - prgenius/src/prgenius/__init__.py (__version__)
  - CHANGELOG.md (latest release heading must lead)

CLAUDE.md's release process names `prgenius/__init__.py` as a file to bump by
hand, which is exactly how it drifted out of the automated check: the runtime
value (`python -c "import prgenius; print(prgenius.__version__)"`, also printed
by the publish-pypi smoke step) came from a file no checker read.

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


def _check_init_version(path: Path, version: str) -> list[str]:
    """Check prgenius __init__.py __version__ — the value the wheel actually reports."""
    if not path.exists():
        return [f"{path.relative_to(ROOT)}: file not found"]
    text = path.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\'](.+?)["\']', text, re.MULTILINE)
    old = m.group(1) if m else "???"
    if old != version:
        return [f"{path.relative_to(ROOT)}: __version__ {old} -> {version}"]
    return []


def _check_changelog_leads(path: Path, version: str) -> list[str]:
    """Check the newest release heading in CHANGELOG.md.

    Only the newest heading must match: older entries are history and are never
    rewritten. `## [Unreleased]` is allowed to sit above it as a staging area.
    """
    if not path.exists():
        return [f"{path.name}: file not found"]
    text = path.read_text(encoding="utf-8")
    headings = re.findall(r'^## \[(.+?)\]', text, re.MULTILINE)
    released = [h for h in headings if h.lower() != "unreleased"]
    if not released:
        return [f"{path.name}: no release heading found"]
    newest = released[0]
    if newest != version:
        return [f"{path.name}: newest release heading is [{newest}], expected [{version}]"]
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


def _apply_init_version(path: Path, version: str) -> tuple[bool, str]:
    """Update prgenius __init__.py __version__."""
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(
        r'^(__version__\s*=\s*)["\'](.+?)["\']',
        rf'\g<1>"{version}"',
        text, count=1, flags=re.MULTILINE,
    )
    if n == 0:
        return False, f"{path.relative_to(ROOT)}: no __version__ assignment found (not auto-inserted)"
    if new == text:
        return False, f"{path.relative_to(ROOT)}: already {version}"
    path.write_text(new, encoding="utf-8")
    return True, f"{path.relative_to(ROOT)}: __version__ -> {version}"


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
            lambda: _apply_init_version(
                ROOT / "prgenius" / "src" / "prgenius" / "__init__.py", version
            ),
        ]:
            changed, msg = fn()
            print(f"  [{'UPDATED' if changed else 'OK'}] {msg}")
            if changed:
                any_changed = True
        # CHANGELOG is check-only under --apply too: a missing release heading
        # means the entry was never written, and inventing one would be a false
        # record. Human writes the entry; this tool only points at the gap.
        for d in _check_changelog_leads(ROOT / "CHANGELOG.md", version):
            print(f"  [NEEDS-HUMAN] {d}")
        print(f"\n{'All files synced.' if any_changed else 'All files already in sync.'}")
        return 0

    # Dry-run: check for drift, exit 1 if any
    all_drifts: list[str] = []
    all_drifts.extend(_check_server_json(ROOT / "server.json", version))
    all_drifts.extend(_check_json(ROOT / "glama.json", version))
    all_drifts.extend(_check_json(ROOT / "package.json", version))
    all_drifts.extend(_check_dockerfile(ROOT / "Dockerfile", version))
    all_drifts.extend(_check_init_version(
        ROOT / "prgenius" / "src" / "prgenius" / "__init__.py", version
    ))
    all_drifts.extend(_check_changelog_leads(ROOT / "CHANGELOG.md", version))

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
