#!/usr/bin/env python3
"""Measure anti-pattern / success-pattern trigger coverage on the real PR corpus.

Reproducible measurement for:
  issue #66 — how many anti-patterns actually fire on realistic PR text
  issue #67 — how generic the bundle is, with an explicit criterion

Corpus: review-cases/*.json (real harvested PRs). The case schema has `title`
and `body`; every current record has an empty body, so the effective matching
surface is the PR title only. The script reports that fact — it does not pad
or synthesize text.

Matching:
  * "matcher" numbers come from the shipped `check_anti_patterns()` unmodified
    (trigger_keywords substring match + symptom fallback + repo filter).
  * "reachability" numbers come from a raw substring pass over each pattern's
    `trigger_keywords` (anti-patterns) or `tags` (success-patterns, their only
    keyword-like field) against the corpus text.

Criteria (frozen — not tuned to make any number look better):
  * scope_generic        := frontmatter has no non-empty `repo` field.
                            Such a pattern is eligible to fire on any repo
                            (evaluator.check_anti_patterns repo filter).
  * scope_repo           := non-empty `repo` field; only fires on that repo.
  * with_trigger_kw      := anti-pattern has non-empty `trigger_keywords`
                            after dropping single generic tokens; success
                            pattern has ≥1 usable `tags` token.
  * reachable            := ≥1 of its keywords occurs (case-insensitive
                            substring) in the corpus text of ≥1 real case.
  * empirically_generic  := reachable AND the matching cases span ≥2 distinct
                            repos (fires across repos in practice, not just
                            claimed generic by missing `repo` metadata).

Usage:
    python3 scripts/measure_pattern_coverage.py          # human summary
    python3 scripts/measure_pattern_coverage.py --json   # machine JSON
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_SRC = REPO_ROOT / "prgenius" / "src"

# Prefer the local package over any installed prgenius-core. No sys.modules
# surgery here: this file is also imported by tests as a library.
if str(LOCAL_SRC) not in sys.path:
    sys.path.insert(0, str(LOCAL_SRC))

from prgenius.evaluator import (  # noqa: E402
    _ANTI_PATTERN_STOPWORDS,
    check_anti_patterns,
    load_anti_patterns,
    load_success_patterns,
)

# Success-pattern `tags` carry corpus-bucket meta-labels, not PR content.
# They are reported separately so they cannot inflate reachability numbers.
SUCCESS_TAG_META_TOKENS = frozenset({"generic", "success", "large-repo"})


def _load_corpus(repo_root: Path) -> list[dict]:
    cases = []
    for f in sorted((repo_root / "review-cases").glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - malformed input guard
            print(f"skip malformed case {f.name}: {exc}", file=sys.stderr)
            continue
        if isinstance(data, dict) and "title" in data:
            cases.append(data)
    return cases


def _case_text(case: dict) -> str:
    return f"{case.get('title', '')} {case.get('body', '')}".lower()


def _anti_keywords(pattern: dict) -> list[str]:
    kws = pattern.get("trigger_keywords") or []
    if not isinstance(kws, list):
        return []
    out = []
    for kw in kws:
        if not isinstance(kw, str):
            continue
        kw = kw.strip().lower()
        if len(kw) < 3 or kw in _ANTI_PATTERN_STOPWORDS:
            continue
        out.append(kw)
    return out


def _success_tag_tokens(pattern: dict) -> tuple[list[str], list[str]]:
    """Return (all_tokens, content_tokens) from a success pattern's tags field.

    tags may be a YAML list or a raw string like "generic success"; both occur.
    """
    raw = pattern.get("tags") or []
    if isinstance(raw, str):
        tokens = raw.replace(",", " ").split()
    elif isinstance(raw, list):
        tokens = [str(t) for t in raw]
    else:
        tokens = []
    tokens = [t.strip().lower() for t in tokens if str(t).strip()]
    content = [
        t for t in tokens
        if len(t) > 2 and t not in _ANTI_PATTERN_STOPWORDS and t not in SUCCESS_TAG_META_TOKENS
    ]
    return tokens, content


def _reachability(keywords: list[str], text_by_repo: dict) -> set:
    """Repos whose case text contains ≥1 keyword."""
    hit_repos = set()
    for repo, texts in text_by_repo.items():
        if any(kw in t for kw in keywords for t in texts):
            hit_repos.add(repo)
    return hit_repos


def measure(repo_root: Path) -> dict:
    cases = _load_corpus(repo_root)
    text_by_repo: dict = {}
    for c in cases:
        text_by_repo.setdefault(c.get("repo", "(unknown)"), []).append(_case_text(c))

    anti = load_anti_patterns(repo_root)
    succ = load_success_patterns(repo_root)

    # ---- anti-patterns ----
    anti_md = sum(1 for p in anti.values() if not p.get("_is_json_pattern"))
    anti_json = len(anti) - anti_md
    anti_with_kw = sum(1 for p in anti.values() if _anti_keywords(p))
    anti_scope_generic = sum(
        1 for p in anti.values() if not (p.get("repo") or "").strip()
    )
    anti_scope_repo = len(anti) - anti_scope_generic

    fired: Counter = Counter()
    cases_with_hit = 0
    for c in cases:
        hits = check_anti_patterns(
            c.get("title", ""), "", c.get("repo", ""), repo_root,
            body=c.get("body", "") or "",
        )
        if hits:
            cases_with_hit += 1
        for h in hits:
            fired[h["key"]] += 1

    anti_reachable = 0
    anti_empirically_generic = 0
    for p in anti.values():
        kws = _anti_keywords(p)
        if not kws:
            continue
        repos_hit = _reachability(kws, text_by_repo)
        if repos_hit:
            anti_reachable += 1
            if len(repos_hit) >= 2:
                anti_empirically_generic += 1

    # ---- success-patterns ----
    succ_with_kw = 0
    succ_with_meta_only = 0
    succ_scope_generic = sum(
        1 for p in succ.values() if not (p.get("repo") or "").strip()
    )
    succ_reachable = 0
    succ_empirically_generic = 0
    for p in succ.values():
        tokens, content = _success_tag_tokens(p)
        if content:
            succ_with_kw += 1
            repos_hit = _reachability(content, text_by_repo)
            if repos_hit:
                succ_reachable += 1
                if len(repos_hit) >= 2:
                    succ_empirically_generic += 1
        elif tokens:
            succ_with_meta_only += 1

    n_cases = len(cases) or 1
    n_anti = len(anti) or 1
    n_succ = len(succ) or 1

    return {
        "corpus": {
            "cases": len(cases),
            "cases_with_body": sum(1 for c in cases if (c.get("body") or "").strip()),
            "repos": len(text_by_repo),
            "effective_surface": "title+body (body empty on every current record)",
        },
        "anti_patterns": {
            "loaded_total": len(anti),
            "loaded_md": anti_md,
            "loaded_json": anti_json,
            "with_trigger_keywords": anti_with_kw,
            "without_trigger_keywords": len(anti) - anti_with_kw,
            "scope_generic_no_repo_field": anti_scope_generic,
            "scope_repo_specific": anti_scope_repo,
            "fired_by_shipped_matcher": len(fired),
            "pattern_fire_rate": round(len(fired) / n_anti, 4),
            "cases_with_hit": cases_with_hit,
            "case_hit_rate": round(cases_with_hit / n_cases, 4),
            "reachable_via_keywords": anti_reachable,
            "empirically_generic": anti_empirically_generic,
            "fired_keys": dict(fired.most_common()),
        },
        "success_patterns": {
            "loaded_total": len(succ),
            "with_content_tags": succ_with_kw,
            "with_meta_tags_only": succ_with_meta_only,
            "without_tags": n_succ - succ_with_kw - succ_with_meta_only,
            "scope_generic_no_repo_field": succ_scope_generic,
            "scope_repo_specific": len(succ) - succ_scope_generic,
            "with_trigger_keywords": 0,
            "reachable_via_content_tags": succ_reachable,
            "empirically_generic": succ_empirically_generic,
        },
        "criteria": {
            "scope_generic": "no non-empty `repo` field in frontmatter (fires on any repo)",
            "scope_repo": "non-empty `repo` field (only fires on that repo)",
            "with_trigger_keywords": "anti: non-empty trigger_keywords minus generic tokens (<3 chars / stopwords); success: ≥1 non-meta tags token",
            "reachable": "≥1 keyword occurs as case-insensitive substring in ≥1 real case text",
            "empirically_generic": "reachable AND matching cases span ≥2 distinct repos",
            "success_tag_meta_tokens": sorted(SUCCESS_TAG_META_TOKENS),
            "matcher": "prgenius.evaluator.check_anti_patterns (unmodified)",
        },
    }


def _human(m: dict) -> None:
    a = m["anti_patterns"]
    s = m["success_patterns"]
    c = m["corpus"]
    print(f"corpus: {c['cases']} real PRs / {c['repos']} repos "
          f"({c['cases_with_body']} with body) — surface: {c['effective_surface']}")
    print()
    print(f"anti-patterns: {a['loaded_total']} loaded "
          f"({a['loaded_md']} md + {a['loaded_json']} json)")
    print(f"  with trigger_keywords        : {a['with_trigger_keywords']}")
    print(f"  without trigger_keywords     : {a['without_trigger_keywords']}")
    print(f"  scope: generic (no repo:)    : {a['scope_generic_no_repo_field']}")
    print(f"  scope: repo-specific         : {a['scope_repo_specific']}")
    print(f"  fired by shipped matcher     : {a['fired_by_shipped_matcher']} "
          f"({a['pattern_fire_rate']:.1%} of patterns)")
    print(f"  cases with ≥1 hit            : {a['cases_with_hit']} "
          f"({a['case_hit_rate']:.1%} of cases)")
    print(f"  reachable via keywords       : {a['reachable_via_keywords']}")
    print(f"  empirically generic (≥2 repos): {a['empirically_generic']}")
    print()
    print(f"success-patterns: {s['loaded_total']} loaded")
    print(f"  with content tags            : {s['with_content_tags']}")
    print(f"  meta tags only (generic/success/large-repo): {s['with_meta_tags_only']}")
    print(f"  with trigger_keywords        : {s['with_trigger_keywords']}")
    print(f"  scope: generic (no repo:)    : {s['scope_generic_no_repo_field']}")
    print(f"  reachable via content tags   : {s['reachable_via_content_tags']}")
    print(f"  empirically generic (≥2 repos): {s['empirically_generic']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON")
    ap.add_argument("--root", default=str(REPO_ROOT), help="repo root (default: this repo)")
    args = ap.parse_args()
    m = measure(Path(args.root))
    if args.json:
        print(json.dumps(m, indent=2, ensure_ascii=False))
    else:
        _human(m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
