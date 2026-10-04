"""harvest 结果分类 —— 防止把成功 PR 收割成失败反模式.

背景: 2026-10-04 在 anti-patterns/ 里发现 4 条空壳, 其中 3 条是**已合并**的 PR
("已合并 by @维护者"、"Root Cause: 无 maintainer 评论"), 却被盖上
`category: pr-failure` 且 Lesson/Solution/Verification 全是 TODO。
根因是 harvest 的 draft 模板无条件写死 pr-failure。

这里的判据是"有没有真失败信号", 不是"这个 PR 有没有被收割过"。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from harvest import classify_outcome, generate_lesson_draft  # noqa: E402


def _pr(merged: bool = True, number: int = 1) -> dict:
    return {
        "number": number,
        "title": "feat: some change",
        "html_url": f"https://example.com/pull/{number}",
        "user": {"login": "someone"},
        "body": "does a thing",
        "merged_at": "2026-08-13" if merged else None,
    }


BOT = [{"author_association": "NONE", "user": {"login": "dco-bot"},
        "body": "## DCO Sign-off Required\nPlease add Signed-off-by to your commits"}]
MAINTAINER = [{"author_association": "MEMBER", "user": {"login": "maintainer"},
               "body": "Please split this into smaller PRs before we can take it"}]


class TestClassifyOutcome:
    def test_unmerged_pr_is_a_failure(self):
        assert classify_outcome(_pr(merged=False), "Closed without merge", []) == "rejected"

    def test_merged_with_no_comments_has_no_signal(self):
        assert classify_outcome(_pr(merged=True), "已合并 by @maintainer", []) == "merged-clean"

    def test_bot_comment_is_not_a_failure_signal(self):
        # DCO / CI bot 评论不是 maintainer 反馈 —— 与 _extract_key_comments 同口径。
        # 若这里判成 merged-with-review, Root Cause 段会显示"无 maintainer 评论",
        # 两段自相矛盾。
        assert classify_outcome(_pr(merged=True), "已合并 by @maintainer", BOT) == "merged-clean"

    def test_maintainer_comment_on_merged_pr_is_feedback(self):
        assert classify_outcome(_pr(merged=True), "已合并 by @maintainer", MAINTAINER) == "merged-with-review"

    def test_tiny_comment_is_not_feedback(self):
        # _extract_key_comments 要求 body 长度 > 10; 分类必须同此门槛。
        tiny = [{"author_association": "MEMBER", "user": {"login": "m"}, "body": "ok"}]
        assert classify_outcome(_pr(merged=True), "已合并", tiny) == "merged-clean"


class TestLessonDraftIsHonest:
    def test_merged_clean_pr_is_not_labeled_pr_failure(self):
        out = generate_lesson_draft("example/repo", _pr(merged=True), "已合并 by @m", [])
        assert "category: pr-failure" not in out
        assert "category: merged-reference" in out
        assert "severity: info" in out

    def test_merged_clean_pr_does_not_prompt_you_to_write_a_lesson(self):
        # 邀请别人给"没有失败的 PR"写教训 = 邀请编造。
        out = generate_lesson_draft("example/repo", _pr(merged=True), "已合并 by @m", [])
        assert "没有失败信号" in out
        assert "不要往这里填 Lesson" in out
        assert "提炼以下可复用教训" not in out

    def test_rejected_pr_still_gets_lesson_guidance(self):
        out = generate_lesson_draft("example/repo", _pr(merged=False), "Closed without merge", MAINTAINER)
        assert "category: pr-failure" in out
        assert "提炼以下可复用教训" in out
        assert "没有失败信号" not in out

    def test_root_cause_matches_the_classification(self):
        # 两段不能互相矛盾: 说"无 maintainer 评论"就不能同时判成"有反馈可提炼"。
        out = generate_lesson_draft("example/repo", _pr(merged=True), "已合并 by @m", BOT)
        assert "无 maintainer 评论" in out
        assert "category: merged-reference" in out
