"""Tests for the gh CLI → curl + GITHUB_TOKEN fallback (issue #55).

Regression lock for commit 333ac8b, which was lost in v2.0.0: `status`,
`auto-ping` and `auto-rebase` must keep working when `gh` is missing or not
executable (WSL with a Windows gh.exe on PATH, containers without gh) as long
as a token is available.

Every test here uses a fake token. No real credential is read, and no token
value is ever printed.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import prgenius.status as st_mod

# Deliberately fake — never a real credential.
FAKE_TOKEN = "ghp_faketoken_for_unittest_only_not_a_real_credential"

GRAPHQL_OK = json.dumps({"data": {"search": {"nodes": []}}})


class _Proc:
    """Minimal stand-in for subprocess.CompletedProcess."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class _GhGone:
    """subprocess.run replacement that fails on `gh` and records curl calls."""

    def __init__(self, gh_error, curl_stdout=GRAPHQL_OK):
        self.gh_error = gh_error
        self.curl_stdout = curl_stdout
        self.curl_cmds = []

    def __call__(self, cmd, **kwargs):
        if cmd and cmd[0] == "gh":
            raise self.gh_error
        self.curl_cmds.append(list(cmd))
        return _Proc(stdout=self.curl_stdout)


def _auth_headers(cmd):
    return [a for a in cmd if isinstance(a, str) and a.startswith("Authorization:")]


class TestRunGhFallsBackToCurl(unittest.TestCase):
    """_run_gh must survive a missing / unexecutable gh binary."""

    def _fallback_call(self, gh_error, args):
        runner = _GhGone(gh_error)
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": FAKE_TOKEN}, clear=False):
            with mock.patch.object(st_mod.subprocess, "run", side_effect=runner):
                out = st_mod._run_gh(args)
        return out, runner

    def test_file_not_found_falls_back_to_curl(self):
        """Issue #55: gh absent → curl, and the GraphQL response comes back."""
        out, runner = self._fallback_call(
            FileNotFoundError("gh"), ["api", "graphql", "-f", "query=query { viewer { login } }"]
        )
        self.assertEqual(json.loads(out), {"data": {"search": {"nodes": []}}})
        self.assertEqual(len(runner.curl_cmds), 1)

    def test_permission_error_falls_back_to_curl(self):
        """The exact traceback in the issue is PermissionError, not FileNotFoundError."""
        out, runner = self._fallback_call(
            PermissionError(13, "Permission denied"), ["api", "graphql", "-f", "query=query {}"]
        )
        self.assertEqual(json.loads(out), {"data": {"search": {"nodes": []}}})
        self.assertEqual(len(runner.curl_cmds), 1)

    def test_curl_call_carries_authorization_bearer_header(self):
        """Lane requirement: assert the curl path is taken AND sends Authorization."""
        _out, runner = self._fallback_call(
            FileNotFoundError("gh"), ["api", "graphql", "-f", "query=query {}"]
        )
        cmd = runner.curl_cmds[0]
        self.assertEqual(cmd[0], "curl")
        auth = _auth_headers(cmd)
        self.assertEqual(len(auth), 1, "curl call must send exactly one Authorization header")
        self.assertTrue(auth[0].startswith("Authorization: Bearer "),
                        "Authorization header must use the Bearer scheme")
        self.assertIn(FAKE_TOKEN, auth[0], "curl must authenticate with the env token")

    def test_curl_call_targets_graphql_endpoint_with_post(self):
        _out, runner = self._fallback_call(
            FileNotFoundError("gh"), ["api", "graphql", "-f", "query=query {}"]
        )
        cmd = runner.curl_cmds[0]
        self.assertIn("https://api.github.com/graphql", cmd)
        self.assertIn("-X", cmd)
        self.assertEqual(cmd[cmd.index("-X") + 1], "POST")
        self.assertIn("--data-raw", cmd)

    def test_curl_payload_is_the_graphql_query(self):
        _out, runner = self._fallback_call(
            FileNotFoundError("gh"), ["api", "graphql", "-f", "query=query { viewer { login } }"]
        )
        cmd = runner.curl_cmds[0]
        payload = json.loads(cmd[cmd.index("--data-raw") + 1])
        self.assertEqual(payload["query"], "query { viewer { login } }")

    def test_gh_is_preferred_when_available(self):
        """No fallback when gh works — the curl path must not run."""
        def fake_run(cmd, **kwargs):
            self.assertEqual(cmd[0], "gh")
            return _Proc(stdout=GRAPHQL_OK)

        with mock.patch.object(st_mod.subprocess, "run", side_effect=fake_run):
            out = st_mod._run_gh(["api", "graphql", "-f", "query=query {}"])
        self.assertEqual(json.loads(out), {"data": {"search": {"nodes": []}}})

    def test_no_token_raises_without_echoing_a_token(self):
        """Missing gh and missing token → clear error, no credential in it."""
        with mock.patch.object(st_mod, "_read_token", return_value=None):
            with mock.patch.object(st_mod.subprocess, "run",
                                   side_effect=FileNotFoundError("gh")):
                with self.assertRaises(RuntimeError) as ctx:
                    st_mod._run_gh(["api", "graphql", "-f", "query=query {}"])
        message = str(ctx.exception)
        self.assertIn("GITHUB_TOKEN", message)
        self.assertNotIn(FAKE_TOKEN, message)
        self.assertNotIn("ghp_", message)

    def test_unsupported_gh_verb_is_rejected_by_fallback(self):
        """Only `gh api` is translated; other verbs fail loudly, not silently."""
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": FAKE_TOKEN}, clear=False):
            with mock.patch.object(st_mod.subprocess, "run",
                                   side_effect=FileNotFoundError("gh")):
                with self.assertRaises(RuntimeError):
                    st_mod._run_gh(["pr", "comment", "1"])


class TestFetchOpenPrsViaToken(unittest.TestCase):
    """fetch_open_prs_via_token: the gh-vs-curl choice is internal (issue #55)."""

    def test_returns_parsed_prs_when_gh_is_unavailable(self):
        raw = json.dumps({
            "data": {"search": {"nodes": [{
                "number": 7,
                "title": "fallback works",
                "url": "https://github.com/org/repo/pull/7",
                "repository": {"nameWithOwner": "org/repo"},
                "author": {"login": "alice"},
                "createdAt": "2026-09-01T00:00:00Z",
                "updatedAt": "2026-09-02T00:00:00Z",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN",
                "reviewDecision": None,
                "commits": {"nodes": [{"commit": {"committedDate": "2026-09-01T12:00:00Z"}}]},
                "reviews": {"nodes": []},
                "statusCheckRollup": {"state": "SUCCESS"},
            }]}}
        })
        runner = _GhGone(FileNotFoundError("gh"), curl_stdout=raw)
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": FAKE_TOKEN}, clear=False):
            with mock.patch.object(st_mod.subprocess, "run", side_effect=runner):
                prs = st_mod.fetch_open_prs_via_token(author="alice")
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0].number, 7)
        self.assertEqual(prs[0].repo, "org/repo")
        self.assertEqual(prs[0].checks_status, "success")
        self.assertEqual(len(runner.curl_cmds), 1, "must have gone through the curl fallback")

    def test_fetch_open_prs_delegates_to_via_token(self):
        with mock.patch.object(st_mod, "fetch_open_prs_via_token", return_value=[]) as spy:
            self.assertEqual(st_mod.fetch_open_prs(author="bob"), [])
        spy.assert_called_once_with(author="bob", repo=None)


class TestGhApiRequestRestFallback(unittest.TestCase):
    """auto-rebase / auto-ping write paths must survive a missing gh too."""

    def test_update_branch_put_falls_back_to_rest(self):
        runner = _GhGone(PermissionError(13, "Permission denied"), curl_stdout="{}")
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": FAKE_TOKEN}, clear=False):
            with mock.patch.object(st_mod.subprocess, "run", side_effect=runner):
                st_mod.gh_api_request("repos/org/repo/pulls/3/update-branch", method="PUT")
        self.assertEqual(len(runner.curl_cmds), 1)
        cmd = runner.curl_cmds[0]
        self.assertIn("https://api.github.com/repos/org/repo/pulls/3/update-branch", cmd)
        self.assertEqual(cmd[cmd.index("-X") + 1], "PUT")
        self.assertTrue(_auth_headers(cmd), "REST fallback must authenticate")

    def test_comment_post_sends_body_field(self):
        runner = _GhGone(FileNotFoundError("gh"), curl_stdout="{}")
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": FAKE_TOKEN}, clear=False):
            with mock.patch.object(st_mod.subprocess, "run", side_effect=runner):
                st_mod.gh_api_request(
                    "repos/org/repo/issues/3/comments",
                    method="POST",
                    fields={"body": "friendly ping"},
                )
        cmd = runner.curl_cmds[0]
        payload = json.loads(cmd[cmd.index("--data-raw") + 1])
        self.assertEqual(payload, {"body": "friendly ping"})
        self.assertEqual(cmd[cmd.index("-X") + 1], "POST")

    def test_token_is_never_written_to_stderr_by_the_fallback(self):
        """Guard: no path may echo the credential (issue note: never log tokens)."""
        import io
        import contextlib
        runner = _GhGone(FileNotFoundError("gh"))
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": FAKE_TOKEN}, clear=False):
            with mock.patch.object(st_mod.subprocess, "run", side_effect=runner):
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    st_mod._run_gh(["api", "graphql", "-f", "query=query {}"])
        self.assertNotIn(FAKE_TOKEN, err.getvalue())


class TestReadToken(unittest.TestCase):
    """Token resolution order: GITHUB_TOKEN → GH_TOKEN → ~/.git-credentials."""

    def test_github_token_env_wins(self):
        with mock.patch.dict(os.environ,
                             {"GITHUB_TOKEN": FAKE_TOKEN, "GH_TOKEN": "other_fake_value"},
                             clear=False):
            self.assertEqual(st_mod._read_token(), FAKE_TOKEN)

    def test_gh_token_used_when_github_token_absent(self):
        env = {"GH_TOKEN": FAKE_TOKEN}
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            self.assertEqual(st_mod._read_token(), FAKE_TOKEN)

    def test_git_credentials_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            creds = Path(tmp) / ".git-credentials"
            creds.write_text(
                "https://alice:" + FAKE_TOKEN + "@github.com\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GITHUB_TOKEN", None)
                os.environ.pop("GH_TOKEN", None)
                with mock.patch.object(st_mod.Path, "home", classmethod(lambda cls: Path(tmp))):
                    self.assertEqual(st_mod._read_token(), FAKE_TOKEN)

    def test_returns_none_when_nothing_available(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.pop("GH_TOKEN", None)
            with mock.patch.object(st_mod.Path, "home",
                                   classmethod(lambda cls: Path("/nonexistent-home-55"))):
                self.assertIsNone(st_mod._read_token())


if __name__ == "__main__":
    unittest.main()
