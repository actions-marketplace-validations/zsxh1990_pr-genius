#!/usr/bin/env python3
"""Print the README Data Scale table from actual repo contents.

Run from the repo root:
    python3 scripts/print_data_scale.py

Copied output into README.md § Data Scale. Update the README whenever
this script's output changes (profile / case / pattern counts).
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "prgenius" / "src"))

from prgenius.parser import iter_case_studies, iter_profiles
from prgenius.evaluator import load_anti_patterns, load_success_patterns


def count_files(directory: Path, suffix: str, exclude_readme: bool = True) -> int:
    n = 0
    for p in directory.rglob(f"*.{suffix}"):
        if exclude_readme and p.name == "README.md":
            continue
        n += 1
    return n


def main() -> None:
    profiles = len(list(iter_profiles(str(REPO_ROOT))))
    cases = len(list(iter_case_studies(str(REPO_ROOT))))
    anti = len(load_anti_patterns(str(REPO_ROOT)))
    success = len(load_success_patterns(str(REPO_ROOT)))

    success_md = count_files(REPO_ROOT / "success-patterns", "md")
    success_json = count_files(REPO_ROOT / "success-patterns", "json")
    anti_md = count_files(REPO_ROOT / "anti-patterns", "md")
    anti_json = count_files(REPO_ROOT / "anti-patterns", "json")

    total = anti + success

    print(f"Repo profiles:     {profiles}")
    print(f"Case studies:      {cases}")
    print(f"Success patterns:  {success} ({success_md} .md + {success_json} .json)")
    print(f"Anti-patterns:     {anti} ({anti_md} .md + {anti_json} .json)")
    print(f"Total patterns:    {total} (all loaded)")
    print(f"Covered repos:     {profiles}")


if __name__ == "__main__":
    main()
