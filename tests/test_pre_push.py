"""Tests for scripts/hooks/pre_push.sh guards (standard library only).

Each test builds a throwaway git repo and runs the script with
CHIMERA_PRE_PUSH_GUARDS_ONLY=1, so only the guard section runs (no recursion into
the real suite). Not simulated: `git grep -P` being unavailable.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "pre_push.sh"
HOME_LINE = "see /" + "home/someone/project\n"  # split so the repo guard ignores this file


def _env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_") and not k.startswith("PRE_COMMIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
               CHIMERA_PRE_PUSH_GUARDS_ONLY="1")
    env.update(extra)
    return env


class PrePushGuards(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self.git("init", "-q")
        self.commit({"README.md": "hello\n"}, "base")

    def git(self, *args):
        r = subprocess.run(["git", *args], cwd=self.repo, env=_env(),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def commit(self, files, msg):
        for name, content in files.items():
            p = self.repo / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def remove(self, name, msg):
        self.git("rm", "-q", name)
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def run_hook(self, **extra):
        return subprocess.run(["bash", str(SCRIPT)], cwd=self.repo, env=_env(**extra),
                              capture_output=True, text=True).returncode

    def run_range(self, base):
        return self.run_hook(PRE_COMMIT_FROM_REF=base,
                             PRE_COMMIT_TO_REF=self.git("rev-parse", "HEAD"))

    # checkout checks (no range variables)
    def test_clean(self):
        self.assertEqual(self.run_hook(), 0)

    def test_tracked_env(self):
        self.commit({".env": "X=1\n"}, "env")
        self.assertEqual(self.run_hook(), 1)

    def test_nested_env_local(self):
        self.commit({"sub/.env.local": "X=1\n"}, "env")
        self.assertEqual(self.run_hook(), 1)

    def test_lookalike_names_pass(self):
        self.commit({"envoy.md": "x\n", "config.env.md": "x\n"}, "ok")
        self.assertEqual(self.run_hook(), 0)

    def test_non_ascii_dir_env(self):
        self.commit({"données/.env": "X=1\n"}, "env")
        self.assertEqual(self.run_hook(), 1)

    def test_root_context_md_tracked(self):
        self.commit({"CONTEXT.md": "x\n"}, "ctx")
        self.assertEqual(self.run_hook(), 1)

    def test_nested_context_md_passes(self):
        self.commit({"docs/CONTEXT.md": "x\n"}, "ctx")
        self.assertEqual(self.run_hook(), 0)

    def test_root_context_md_added_then_removed_in_range(self):
        base = self.git("rev-parse", "HEAD")
        self.commit({"CONTEXT.md": "x\n"}, "add")
        self.remove("CONTEXT.md", "rm")
        self.assertEqual(self.run_hook(), 0)
        self.assertEqual(self.run_range(base), 1)

    def test_url_path_passes(self):
        self.commit({"a.md": "https://host/home/x\n"}, "url")
        self.assertEqual(self.run_hook(), 0)

    def test_home_path_in_checkout(self):
        self.commit({"a.md": HOME_LINE}, "home")
        self.assertEqual(self.run_hook(), 1)

    # pushed-range checks
    def test_range_clean(self):
        base = self.git("rev-parse", "HEAD")
        self.commit({"b.md": "fine\n"}, "b")
        self.assertEqual(self.run_range(base), 0)

    def test_env_added_then_removed_in_range(self):
        base = self.git("rev-parse", "HEAD")
        self.commit({".env": "X=1\n"}, "add env")
        self.remove(".env", "rm env")
        self.assertEqual(self.run_hook(), 0)  # checkout alone is clean
        self.assertEqual(self.run_range(base), 1)

    def test_non_ascii_env_added_then_removed_in_range(self):
        base = self.git("rev-parse", "HEAD")
        self.commit({"données/.env": "X=1\n"}, "add env")
        self.remove("données/.env", "rm env")
        self.assertEqual(self.run_range(base), 1)

    def test_home_path_added_then_removed_in_range(self):
        base = self.git("rev-parse", "HEAD")
        self.commit({"a.md": HOME_LINE}, "add")
        self.remove("a.md", "rm")
        self.assertEqual(self.run_hook(), 0)
        self.assertEqual(self.run_range(base), 1)

    def test_url_in_range_passes(self):
        base = self.git("rev-parse", "HEAD")
        self.commit({"a.md": "https://host/home/x\n"}, "url")
        self.assertEqual(self.run_range(base), 0)

    def test_bad_commit_before_range_is_ignored(self):
        self.commit({".env": "X=1\n"}, "add env")
        self.remove(".env", "rm env")
        base = self.git("rev-parse", "HEAD")
        self.commit({"b.md": "fine\n"}, "b")
        self.assertEqual(self.run_range(base), 0)

    def test_new_branch_uses_commits_not_on_remotes(self):
        # Zero from-ref (new branch): range is everything not reachable from a remote ref.
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.commit({".env": "X=1\n"}, "add env")
        self.remove(".env", "rm env")
        self.assertEqual(self.run_hook(PRE_COMMIT_FROM_REF="0" * 40,
                                       PRE_COMMIT_TO_REF=self.git("rev-parse", "HEAD")), 1)

    def test_new_branch_ignores_commits_already_on_remote(self):
        self.commit({".env": "X=1\n"}, "add env")
        self.remove(".env", "rm env")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.commit({"b.md": "fine\n"}, "b")
        self.assertEqual(self.run_hook(PRE_COMMIT_FROM_REF="0" * 40,
                                       PRE_COMMIT_TO_REF=self.git("rev-parse", "HEAD")), 0)


if __name__ == "__main__":
    unittest.main()
