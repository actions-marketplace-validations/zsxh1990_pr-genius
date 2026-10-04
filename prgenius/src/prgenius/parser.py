"""Markdown frontmatter parsing — pure-stdlib YAML-subset.

Goals:
- Zero hard deps (no PyYAML) — package works after `pip install prgenius-core`
- Just enough fidelity for OKF v0.1 / rounds v0.5.0 / v0.7.0 frontmatter
- Honest: returns the AST we can parse; preserves raw text for the rest

Strategy: 2-pass indent-stack parser.
- Pass 1: collect (line, indent, raw_line)
- Pass 2: walk lines; push/pop stack based on indent depth

Limitations:
- top-level key: value (string/int/bool/null/list-inline)
- 2-space indent for nested mapping
- `- item` lists (with optional inline key: value on first line)
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Iterator


_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def extract_frontmatter_text(text: str) -> str | None:
    """Extract raw frontmatter text between --- delimiters.

    Returns the inner YAML text, or None if no frontmatter found.
    Handles both ``---\\n...\\n---`` and ``---\\r?\\n...\\r?\\n---``.
    """
    m = _FM_RE.match(text)
    return m.group(1) if m else None



_BLOCK_SCALAR = re.compile(r'^[|>][+-]?\d*$')


def _is_block_scalar(value: str) -> bool:
    """YAML block-scalar indicator: `|`, `|-`, `>`, `>+`, `|2` …"""
    return bool(_BLOCK_SCALAR.match(value.strip()))


def _split_key_value(line: str) -> tuple[str, str] | None:
    """Split `k: v`, refusing to split a URL scheme (`https://…`).

    `https://host` has a colon, so a naive `partition(":")` turns it into
    `{https: //host}`. The scheme colon is not a key/value separator.
    """
    if "://" in line:
        return None
    k, sep, v = line.partition(":")
    if not sep:
        return None
    return k, v


def _finish_scalar(current_value: list[str], in_list: bool):
    """Close out a key's accumulated value.

    Two things happen here, and both matter: the block-scalar fold wraps its
    body in quotes so the tokenizer treats it as one value, so those quotes are
    stripped; and a non-list value is joined with spaces, matching the simple
    parser's historical shape.
    """
    if in_list:
        return current_value
    joined = " ".join(current_value).strip()
    if len(joined) >= 2 and joined[0] == '"' and joined[-1] == '"':
        joined = joined[1:-1]
    return joined

def _parse_simple_frontmatter(text: str) -> dict:
    """Parse a simple key-value frontmatter block (evaluator-style).

    Handles: scalar values, inline ``[a, b]`` lists, and ``- item`` lists.
    Returns a dict of {key: value} where values are coerced via ``_coerce``.
    """
    fm: dict = {}
    current_key = None
    current_value: list[str] = []
    in_list = False

    # Fold block scalars first — same pre-pass parse_frontmatter uses. Without it
    # `symptom: |` keeps the indicator as the value, and this is the parser the
    # analyzer's load path calls (issue #89: a fix in the *other* parser left the
    # real path leaking).
    for line in _fold_block_scalars(text).splitlines():
        if re.match(r"^[a-zA-Z_]+:", line) and not line.startswith("  "):
            if current_key is not None:
                fm[current_key] = _finish_scalar(current_value, in_list)
            key, value = line.split(":", 1)
            current_key = key.strip()
            value = value.strip()
            if value == "":
                current_value = []
                in_list = True
            elif value.startswith("["):
                inner = value[1:-1].strip()
                current_value = [v.strip().strip('"') for v in inner.split(",")] if inner else []
                in_list = False
            else:
                current_value = [value]
                in_list = False
        elif line.startswith("  - ") and in_list:
            current_value.append(line[4:].strip().strip('"'))
        elif line.startswith("  ") and not in_list:
            current_value.append(line.strip())

    if current_key is not None:
        fm[current_key] = _finish_scalar(current_value, in_list)
    return fm


def load(path: str | Path) -> dict:
    """Load a markdown file: return {frontmatter, body, path}."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    fm_match = _FM_RE.match(text)
    if not fm_match:
        return {"frontmatter": {}, "body": text, "path": str(p)}
    fm_text = fm_match.group(1)
    body = text[fm_match.end():].lstrip("\n")
    return {
        "frontmatter": parse_frontmatter(fm_text),
        "body": body,
        "path": str(p),
    }


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _coerce(v: str):
    """Coerce a scalar string to a Python value."""
    # Strip inline YAML comments (e.g. "0.15  # comment" → "0.15")
    if isinstance(v, str) and "  #" in v:
        v = v[:v.index("  #")].strip()
    if v == "" or v in ("null", "~"):
        return None
    if v == "true":
        return True
    if v == "false":
        return False
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_coerce(x.strip()) for x in inner.split(",")]
    if re.match(r"^-?\d+$", v):
        return int(v)
    if re.match(r"^-?\d+\.\d+$", v):
        return float(v)
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    return v


def _last_list_key(d: dict):
    for k in reversed(d.keys()):
        if isinstance(d[k], list):
            return k
    return None


def _normalize_lists(node):
    """Recursively replace `{'_': [items]}` or `{'_items': [items]}` (parser quirk)
    with the bare list.
    """
    if isinstance(node, dict):
        keys = list(node.keys())
        if (
            len(keys) == 1
            and keys[0] in ("_", "_items")
            and isinstance(node[keys[0]], list)
        ):
            return [_normalize_lists(x) for x in node[keys[0]]]
        return {k: _normalize_lists(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_normalize_lists(x) for x in node]
    return node



def _fold_block_scalars(text: str) -> str:
    """Collapse YAML block scalars into single-line quoted values.

    `key: |` (or `>`, with optional chomping/indent indicators) means the
    indented lines that follow ARE the value. The tokenizer downstream flattens
    indented lines into the same list, so the block has to be folded first —
    otherwise the `|` survives as a literal character (issue #51).
    """
    out: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(\s*[A-Za-z_][\w.-]*\s*:\s*)([|>][+-]?\d*)\s*$', line)
        if not m:
            out.append(line)
            i += 1
            continue
        head, _ind = m.group(1), m.group(2)
        i += 1
        body: list[str] = []
        while i < len(lines):
            nxt = lines[i]
            if nxt.strip() == "":
                body.append("")
                i += 1
                continue
            if not nxt.startswith("  "):
                break
            body.append(nxt[2:])
            i += 1
        while body and body[-1] == "":
            body.pop()
        joined = "\\n".join(body)
        out.append(f'{head}"{joined}"')
    return "\n".join(out)


def parse_frontmatter(text: str) -> dict:
    """Parse a YAML-subset frontmatter block.

    Strategy: walk lines, push/pop an indent-aware stack. Lists get attached
    to the most recent dict-key (the "current list"). After the walk we
    normalize any `{'_': [...]}` quirk wrappers to plain lists.
    """
    tokens = []
    for raw in _fold_block_scalars(text).splitlines():
        if not raw.strip():
            continue
        if raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        tokens.append((indent, raw.strip()))

    root: dict = {}
    # stack of (indent_level, container); root container indent = -1
    stack = [(-1, root)]

    for indent, line in tokens:
        # pop until stack top has smaller indent than current
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        parent_indent, parent = stack[-1]

        if line.startswith("- "):
            content = line[2:].strip()
            if not isinstance(parent, dict):
                # shouldn't happen in our schema
                continue
            last_key = _last_list_key(parent)
            if last_key is None:
                parent["_items"] = []
                current_list = parent["_items"]
                last_key = "_items"
            else:
                current_list = parent[last_key]

            # A list item that is a URL (`- https://…`) has a colon but no
            # key/value split — the scheme colon is not a separator. Without this
            # it becomes {"https": "//…"} instead of a plain string (issue #60).
            item_kv = _split_key_value(content) if not content.startswith(('"', "'")) else None
            if item_kv is not None:
                k, v = item_kv
                k = _unquote(k.strip())
                v = v.strip()
                item: dict = {k: _coerce(v)}
                current_list.append(item)
                stack.append((indent, item))
            else:
                current_list.append(_coerce(content))
            continue

        # Block scalar (`symptom: |` …): the indicator is not a value — it means
        # the indented lines that follow ARE the value. Keeping the `|` leaked it
        # into CLI/MCP output as a literal prefix (issue #51).
        kv = _split_key_value(line)
        if kv is None:
            continue
        k, v = kv
        k = _unquote(k.strip())
        v = v.strip()

        if not isinstance(parent, dict):
            continue

        if v == "":
            new = {}
            parent[k] = new
            stack.append((indent, new))
        else:
            parent[k] = _coerce(v)

    return _normalize_lists(root)


# ---------- higher-level iterators ----------

def _iter_dir(path: Path) -> list[Path]:
    """列出目录条目; 目录不存在或不可读时返回空表, 不抛.

    为什么: `--repo-root` 传了不存在的路径时, `root.iterdir()` 直接
    FileNotFoundError 冒成 traceback —— 用户只想要一句"这个路径不对"。
    取数函数不该因为输入不存在就崩; 它们返回空, 由调用方决定怎么报
    (doctor 会说 knowledge base not readable, 这才是用户该看到的)。
    """
    try:
        return sorted(path.iterdir())
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return []



def iter_profiles(repo_root: str | Path) -> Iterator[dict]:
    """Yield each Repo Profile dict under `<repo_root>/<folder>/index.md` or `<repo_root>/profiles/<folder>/index.md`."""
    root = Path(repo_root)
    skip = {
        "anti-patterns", "misakanet-50", ".github", "docs",
        "scripts", "prgenius", "__pycache__", ".git",
        "federation.yaml", "profiles", "archive", "validate_checks",
        # agent/session scratch — may contain full copies of the corpus (worktrees),
        # which would be double-counted and would resurrect stale profiles.
        ".claude",
    }

    # Scan root-level profile dirs
    for sub in _iter_dir(root):
        if not sub.is_dir() or sub.name in skip or sub.name.startswith("."):
            continue
        idx = sub / "index.md"
        if not idx.exists():
            continue
        loaded = load(idx)
        if loaded["frontmatter"].get("type") == "Repo Profile":
            loaded["folder"] = sub.name
            yield loaded

    # Scan profiles/ subdirectory
    profiles_dir = root / "profiles"
    if profiles_dir.is_dir():
        for sub in _iter_dir(profiles_dir):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            idx = sub / "index.md"
            if not idx.exists():
                continue
            loaded = load(idx)
            if loaded["frontmatter"].get("type") == "Repo Profile":
                loaded["folder"] = sub.name
                yield loaded


def iter_case_studies(repo_root: str | Path) -> Iterator[dict]:
    """Yield each PR Case Study dict under repo root."""
    root = Path(repo_root)
    try:
        _case_paths = sorted(root.rglob("pr-*.md"))
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        _case_paths = []
    for path in _case_paths:
        try:
            loaded = load(path)
        except Exception:
            continue
        if loaded["frontmatter"].get("type") == "PR Case Study":
            loaded["folder"] = path.parent.name
            loaded["pr_file"] = path.name
            yield loaded


_profile_index_cache: dict[str, dict[str, dict]] = {}


def clear_profile_cache(repo_root: str | Path | None = None) -> None:
    """Clear the profile index cache. Pass repo_root for a specific tree, or None for all."""
    if repo_root is None:
        _profile_index_cache.clear()
    else:
        _profile_index_cache.pop(str(Path(repo_root).resolve()), None)


def _build_profile_index(repo_root: str | Path) -> dict[str, dict]:
    """Build an O(1) lookup index keyed by lowered folder name and repo path."""
    root_str = str(Path(repo_root).resolve())
    if root_str in _profile_index_cache:
        return _profile_index_cache[root_str]
    idx: dict[str, dict] = {}
    for profile in iter_profiles(repo_root):
        folder_key = profile["folder"].lower()
        idx[folder_key] = profile
        repo_key = profile["frontmatter"].get("repo", "").strip("/").lower()
        if repo_key and repo_key not in idx:
            idx[repo_key] = profile
    _profile_index_cache[root_str] = idx
    return idx


def profile_get(repo_root: str | Path, repo: str) -> dict | None:
    """Look up a Repo Profile by `org/name`. None if missing. O(1) via index."""
    target = repo.strip("/").lower()
    target_folder = target.replace("/", "-")
    idx = _build_profile_index(repo_root)
    return idx.get(target_folder) or idx.get(target)


def schema_info() -> dict:
    return {
        "schema_versions": ["rounds v0.5.0", "rounds v0.7.0 (BC over v0.5.0)"],
        "delta_kinds": ["code_change", "no_code_change", "unknown"],
        "close_decision_status": ["pending", "close", "keep_open", "merged", "superseded"],
        "evidence_fields_round_level": ["verified_at", "evidence_urls", "confidence"],
        "evidence_fields_case_level": ["verified_at", "evidence_urls", "confidence"],
        "confidence_values": ["high", "medium", "low"],
        "action_enum": [
            "open", "amend", "bot_review", "human_review",
            "check_in", "bump", "close", "merge", "decision",
        ],
    }
