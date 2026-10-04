#!/usr/bin/env python3
"""
PR Failure Harvester — 从被拒 PR 中提取反模式/lesson draft

Usage:
    python3 scripts/harvest.py https://github.com/org/repo/pull/123
    python3 scripts/harvest.py org/repo 123
    python3 scripts/harvest.py org/repo 123 --type lesson
    python3 scripts/harvest.py org/repo 123 --type anti-pattern

输出: Markdown 文件，可直接放入 anti-patterns/ 或 misakanet-50/
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional


def gh_api(url: str) -> Optional[dict]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        try:
            result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                token = result.stdout.strip()
        except Exception:
            pass
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API error {e.code}: {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def fetch_pr(repo: str, pr_number: int) -> Optional[dict]:
    return gh_api(f"https://api.github.com/repos/{repo}/pulls/{pr_number}")


def fetch_comments(repo: str, pr_number: int) -> list:
    data = gh_api(f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments")
    return data if data else []


def fetch_reviews(repo: str, pr_number: int) -> list:
    data = gh_api(f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews")
    return data if data else []


def fetch_labels(repo: str, pr_number: int) -> list:
    data = gh_api(f"https://api.github.com/repos/{repo}/issues/{pr_number}")
    if not data:
        return []
    return [l["name"] for l in data.get("labels", [])]


def fetch_events(repo: str, pr_number: int) -> list:
    data = gh_api(f"https://api.github.com/repos/{repo}/issues/{pr_number}/events")
    return data if data else []



def classify_outcome(pr: dict, close_reason: str, comments: list) -> str:
    """判定这次收割有没有真失败信号.

    为什么需要: 此前两个 draft 模板都**无条件**盖 `category: pr-failure` /
    `type: Anti-Pattern`, 于是"已合并 by @维护者、无 maintainer 评论"的成功 PR
    被收割成失败反模式 —— 2026-10-04 在 anti-patterns/ 里发现 4 条这样的空壳
    (Lesson/Solution/Verification 全是 TODO), 其中 3 条是成功合并的 PR。
    给不存在的失败编 Lesson, 比不写更糟。

    返回:
      "rejected"          PR 未合并即关闭 —— 有失败可记
      "merged-with-review" 已合并但有 maintainer 评论/改动要求 —— 可提炼教训
      "merged-clean"      已合并且无任何 maintainer 反馈 —— **没有反模式**
    """
    if not pr.get("merged_at"):
        return "rejected"
    # 只认 maintainer 评论, 与 _extract_key_comments 同一口径。
    # 否则一条 bot 评论(例如 DCO 检查)就会把合并的 PR 标成"有反馈可提炼",
    # 而 Root Cause 段会显示"无 maintainer 评论" —— 两段自相矛盾。
    for c in comments:
        if c.get("author_association", "") in ("OWNER", "MEMBER", "COLLABORATOR"):
            body = (c.get("body") or "").strip()
            if body and len(body) > 10:
                return "merged-with-review"
    return "merged-clean"


def extract_close_reason(pr: dict, comments: list, reviews: list, events: list = None) -> str:
    """从 PR 数据中提取关闭原因"""
    reasons = []
    if events is None:
        events = []

    # 检查是否已合并
    if pr.get("merged_at"):
        merged_by = pr.get("merged_by", {}).get("login", "unknown")
        return f"已合并 by @{merged_by}"

    # 检查是否作者自己关闭 (通过 events API)
    pr_author = pr.get("user", {}).get("login", "")
    for event in events:
        if event.get("event") == "closed":
            closer = event.get("actor", {}).get("login", "")
            if closer == pr_author:
                return f"作者 @{pr_author} 自己关闭了 PR"

    # 检查标签
    labels = [l["name"] for l in pr.get("labels", [])]
    label_reasons = {
        "ai-policy-violation": "AI 生成内容违反仓库 AI 使用政策",
        "missing-issue-link": "缺少 Issue 关联",
        "invalid": "PR 无效",
        "wontfix": "维护者不打算修复",
        "duplicate": "重复 PR",
        "stale": "长时间无活动被关闭",
        "spam": "垃圾内容",
    }
    for label in labels:
        if label in label_reasons:
            reasons.append(f"标签 `{label}`: {label_reasons[label]}")

    # 检查 maintainer 评论
    for comment in comments:
        body = (comment.get("body") or "").lower()
        author = comment.get("user", {}).get("login", "")
        assoc = comment.get("author_association", "")
        if assoc in ("OWNER", "MEMBER", "COLLABORATOR"):
            # 提取关键句子
            for line in (comment.get("body") or "").split("\n"):
                line = line.strip()
                if any(kw in line.lower() for kw in ["declined", "rejected", "closing", "won't merge", "not accepting", "already implemented"]):
                    reasons.append(f"维护者 @{author}: {line[:100]}")

    # 检查 review
    for review in reviews:
        if review.get("state") == "CHANGES_REQUESTED":
            body = review.get("body") or ""
            if body:
                reasons.append(f"Review 要求修改: {body[:100]}")

    return reasons[0] if reasons else "未明确"


def generate_anti_pattern_draft(repo: str, pr: dict, close_reason: str, comments: list) -> str:
    """生成反模式 draft"""
    pr_number = pr["number"]
    title = pr["title"]
    author = pr["user"]["login"]
    body = _redact_secrets((pr.get("body") or "")[:500])
    labels = [l["name"] for l in pr.get("labels", [])]

    # 从标题/描述中提取 key
    key_slug = re.sub(r'[^a-z0-9]+', '-', title.lower())[:50].strip('-')

    today = datetime.now().strftime("%Y-%m-%d")

    return f"""---
type: Anti-Pattern
key: {key_slug}
description: "{title[:80]}"
symptom: "{close_reason[:100]}"
trigger_keywords:
  - "{title.split(':')[0].strip().lower() if ':' in title else title.split(' ')[0].lower()}"
fix_action: "参见下方 Maintainer 关键评论"
source_pr: "{repo}#{pr_number}"
severity: medium
evidence:
  - "{repo}#{pr_number}: {close_reason[:80]}"
learned_at: {today}
---

## 反模式说明

**PR**: [{repo}#{pr_number}]({pr["html_url"]})
**作者**: @{author}
**标签**: {', '.join(labels) or '无'}
**关闭原因**: {close_reason}

### PR 描述

{body}

### Maintainer 关键评论

{_extract_key_comments(comments)}

### 如何避免

> 根据上方 Maintainer 关键评论，提炼出以下避免步骤：
> - 检查 PR 标题是否符合仓库规范
> - 确认改动范围在仓库接受范围内
> - 提交前验证 CI 通过
> - 如有 Issue 先关联再提 PR

### 历史案例

- {repo}#{pr_number}: {close_reason[:60]}
"""


def generate_lesson_draft(repo: str, pr: dict, close_reason: str, comments: list) -> str:
    """生成 lesson draft (MisakaNet 风格)"""
    pr_number = pr["number"]
    title = pr["title"]
    author = pr["user"]["login"]
    body = _redact_secrets((pr.get("body") or "")[:500])

    today = datetime.now().strftime("%Y-%m-%d")
    lesson_slug = re.sub(r'[^a-z0-9]+', '-', title.lower())[:40].strip('-')

    outcome = classify_outcome(pr, close_reason, comments)
    # 分类必须反映真实结果。合并 + 零反馈的 PR 没有失败可记 —— 盖 pr-failure
    # 就是凭空造一个教训出来。severity 同理: 没有信号就不该是 medium。
    outcome_category = {
        "rejected": "pr-failure",
        "merged-with-review": "pr-review-feedback",
        "merged-clean": "merged-reference",
    }[outcome]
    outcome_severity = "medium" if outcome == "rejected" else "info"
    if outcome == "merged-clean":
        # 三段都留白并说清原因。给"没有失败的 PR"写教训指引, 等于邀请别人
        # 编造一个没发生过的失败 —— 那比空着更糟。
        lesson_block = (
            "\n> **没有失败信号，此处有意留空。** 这个 PR 已合并、且没有任何 "
            "maintainer 评论或改动要求，不存在可提炼的反模式或教训。保留本记录仅作"
            "已收割标记。**不要往这里填 Lesson** —— 那会制造一条声称发生了实际并"
            "未发生的失败。\n"
        )
        solution_block = "\n> 无 —— 没有失败需要修复。\n"
        verification_block = "\n> 无。\n"
    else:
        lesson_block = (
            "\n> 根据上述信息，提炼以下可复用教训：\n"
            "> - 理解仓库的 PR 接受标准（标题、范围、关联 Issue）\n"
            "> - 提交前自查 CI 状态和代码质量\n"
            "> - 关注 maintainer 的反馈模式，避免重复同类错误\n"
        )
        solution_block = "\n> 如有明确修复方案，在此补充。否则标记为\"需人工审查\"。\n"
        verification_block = (
            "\n> 如何验证教训已内化：\n"
            "> - 下次提 PR 前用 `python3 -m prgenius coach` 检查\n"
            "> - 对照本 lesson 的 Root Cause 逐项自查\n"
        )

    return f"""---
type: Lesson
title: "{title[:80]}"
source: "{repo}#{pr_number}"
source_url: "{pr['html_url']}"
category: {outcome_category}
severity: {outcome_severity}
learned_at: {today}
---

## Problem

PR [{repo}#{pr_number}]({pr["html_url"]}) {close_reason}。

**标题**: {title}
**作者**: @{author}
**状态**: {close_reason}

## Root Cause

{_extract_key_comments(comments)}

## What Happened

{body}

## Lesson

{lesson_block}

## Solution

{solution_block}

## Verification

{verification_block}
"""


def _redact_secrets(text: str) -> str:
    """脱敏处理：移除或替换敏感信息"""
    if not text:
        return text

    # GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_, github_pat_)
    text = re.sub(r'ghp_[A-Za-z0-9]{36}', 'ghp_***REDACTED***', text)
    text = re.sub(r'gho_[A-Za-z0-9]{36}', 'gho_***REDACTED***', text)
    text = re.sub(r'ghu_[A-Za-z0-9]{36}', 'ghu_***REDACTED***', text)
    text = re.sub(r'ghs_[A-Za-z0-9]{36}', 'ghs_***REDACTED***', text)
    text = re.sub(r'ghr_[A-Za-z0-9]{36}', 'ghr_***REDACTED***', text)
    text = re.sub(r'github_pat_[A-Za-z0-9_]{82}', 'github_pat_***REDACTED***', text)

    # Generic API keys and tokens
    text = re.sub(r'(?i)(api[_-]?key|token|secret|password|credential)["\s:=]+["\']?[A-Za-z0-9_\-]{20,}["\']?',
                  r'\1: ***REDACTED***', text)

    # AWS keys
    text = re.sub(r'AKIA[0-9A-Z]{16}', 'AKIA***REDACTED***', text)
    text = re.sub(r'(?i)aws[_-]?secret[_-]?access[_-]?key["\s:=]+["\']?[A-Za-z0-9/+=]{40}["\']?',
                  r'aws_secret_access_key: ***REDACTED***', text)

    # Private keys
    text = re.sub(r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----[\s\S]*?-----END (RSA |EC |DSA )?PRIVATE KEY-----',
                  '-----BEGIN PRIVATE KEY-----\n***REDACTED***\n-----END PRIVATE KEY-----', text)

    # Email addresses (optional - only if they look like real emails)
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '***@***.***', text)

    # Internal URLs (mi.feishu.cn, internal domains)
    text = re.sub(r'https?://mi\.feishu\.cn/[^\s"\']+', 'https://***FEISHU_INTERNAL***', text)
    text = re.sub(r'https?://[a-z0-9\-]+\.internal\.[^\s"\']+', 'https://***INTERNAL***', text)

    return text


def _extract_key_comments(comments: list) -> str:
    """提取 maintainer 的关键评论"""
    lines = []
    for comment in comments:
        assoc = comment.get("author_association", "")
        if assoc in ("OWNER", "MEMBER", "COLLABORATOR"):
            author = comment["user"]["login"]
            body = (comment.get("body") or "").strip()
            if body and len(body) > 10:
                # 只取前3行
                preview = "\n".join(body.split("\n")[:3])
                if len(preview) > 200:
                    preview = preview[:200] + "..."
                # 脱敏处理
                preview = _redact_secrets(preview)
                lines.append(f"> @{author}: {preview}")
    return "\n\n".join(lines) if lines else "无 maintainer 评论"


def main():
    parser = argparse.ArgumentParser(description="PR Failure Harvester")
    parser.add_argument("url_or_repo", help="PR URL 或 org/repo")
    parser.add_argument("number", nargs="?", type=int, help="PR number (如果第一个参数是 org/repo)")
    parser.add_argument("--type", "-t", choices=["anti-pattern", "lesson"], default="anti-pattern",
                        help="输出类型")
    parser.add_argument("--output", "-o", help="输出文件路径 (默认打印到 stdout)")
    args = parser.parse_args()

    # 解析 repo 和 pr_number
    if args.number:
        repo = args.url_or_repo
        pr_number = args.number
    else:
        # 从 URL 解析
        m = re.match(r'https?://github\.com/([^/]+/[^/]+)/pull/(\d+)', args.url_or_repo)
        if not m:
            print(f"无法解析: {args.url_or_repo}", file=sys.stderr)
            return 1
        repo = m.group(1)
        pr_number = int(m.group(2))

    print(f"🔍 获取 {repo}#{pr_number}...", file=sys.stderr)

    pr = fetch_pr(repo, pr_number)
    if not pr:
        print(f"无法获取 PR 数据", file=sys.stderr)
        return 1

    comments = fetch_comments(repo, pr_number)
    reviews = fetch_reviews(repo, pr_number)
    labels = fetch_labels(repo, pr_number)
    events = fetch_events(repo, pr_number)

    # 补充 labels 到 pr
    pr["labels"] = [{"name": l} for l in labels]

    close_reason = extract_close_reason(pr, comments, reviews, events)

    print(f"📋 关闭原因: {close_reason}", file=sys.stderr)

    if args.type == "anti-pattern":
        content = generate_anti_pattern_draft(repo, pr, close_reason, comments)
        default_name = f"anti-patterns/{repo.replace('/', '-')}-pr-{pr_number}.md"
    else:
        content = generate_lesson_draft(repo, pr, close_reason, comments)
        default_name = f"misakanet-50/lesson-draft-{repo.replace('/', '-')}-pr-{pr_number}.md"

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"✅ 已保存到 {out_path}", file=sys.stderr)
    else:
        print(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
