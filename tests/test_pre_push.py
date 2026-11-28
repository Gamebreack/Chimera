"""Tests for scripts/hooks/pre_push.sh guards (standard library only).

Each test builds a throwaway git repo and runs the script with
CHIMERA_PRE_PUSH_GUARDS_ONLY=1, so only the guard section runs (no recursion into
the real suite). The hook must not depend on PCRE or GNU grep (see PortabilityTests).
"""
import atexit
import functools
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "pre_push.sh"
HELPER = SCRIPT.with_name("guard_scan.py")
HOME_LINE = "see /" + "home/someone/project\n"  # split so the repo guard ignores this file


# Isolated HOME/XDG so user config is never read, even by git older than 2.32
# (which ignores GIT_CONFIG_GLOBAL).
_HOME = tempfile.mkdtemp(prefix="chimera-home-")
atexit.register(shutil.rmtree, _HOME, ignore_errors=True)


# A python3 that is the interpreter running these tests, first on PATH: a version-manager shim
# (asdf, mise, pyenv) cannot find its config under the isolated HOME and would make the
# hook's `python3` calls fail.
_BIN = tempfile.mkdtemp(prefix="chimera-bin-")
atexit.register(shutil.rmtree, _BIN, ignore_errors=True)
os.symlink(sys.executable, os.path.join(_BIN, "python3"))


def _env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_") and not k.startswith("PRE_COMMIT_")}
    env.update(HOME=_HOME, XDG_CONFIG_HOME=_HOME, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
               CHIMERA_PRE_PUSH_GUARDS_ONLY="1")
    env["PATH"] = _BIN + os.pathsep + env.get("PATH", "")
    env.update(extra)
    return env


def _configure_ssh_signing(repo, workdir):
    """Configure ssh commit signing in repo with a throwaway key; returns False on failure."""
    key = Path(workdir) / "key"
    r = subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                       capture_output=True)
    if r.returncode != 0:
        return False
    pub = key.with_suffix(".pub").read_text().split()
    allowed = Path(workdir) / "allowed"
    allowed.write_text("t@example.invalid " + pub[0] + " " + pub[1] + "\n")
    for k, v in (("gpg.format", "ssh"), ("user.signingkey", str(key)),
                 ("commit.gpgSign", "true"), ("gpg.ssh.allowedSignersFile", str(allowed))):
        if subprocess.run(["git", "config", k, v], cwd=repo, env=_env(),
                          capture_output=True).returncode != 0:
            return False
    return True


@functools.lru_cache(maxsize=None)
def ssh_signing_available():
    """True if this machine can make an ssh-signed commit (needs ssh-keygen and git >= 2.34)."""
    if not shutil.which("ssh-keygen"):
        return False
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d) / "r"
        repo.mkdir()
        try:
            def run(*a):
                return subprocess.run(["git", *a], cwd=repo, env=_env(), capture_output=True)
            if run("init", "-q").returncode != 0 or not _configure_ssh_signing(repo, d):
                return False
            (repo / "f").write_text("x\n")
            return (run("add", "f").returncode == 0
                    and run("commit", "-q", "-m", "probe").returncode == 0)
        except OSError:
            return False


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

    def run_hook(self, script=SCRIPT, cwd=None, **extra):
        return self.run_hook_full(script, cwd, **extra).returncode

    def run_hook_full(self, script=SCRIPT, cwd=None, **extra):
        return subprocess.run(["bash", str(script)], cwd=cwd or self.repo, env=_env(**extra),
                              capture_output=True, text=True)

    def run_range(self, base):
        return self.run_hook(PRE_COMMIT_FROM_REF=base,
                             PRE_COMMIT_TO_REF=self.git("rev-parse", "HEAD"))

    # checkout checks (no range variables)
    def test_clean(self):
        self.assertEqual(self.run_hook(), 0)

    def test_tracked_env(self):
        self.commit({".env": "X=1\n"}, "env")
        r = self.run_hook_full()
        self.assertEqual(r.returncode, 1)
        self.assertIn("must not be tracked", r.stderr)

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
        r = self.run_hook_full()
        self.assertEqual(r.returncode, 1)
        self.assertIn("absolute home paths found", r.stderr)
        self.assertNotIn("failed", r.stderr)

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
        r = self.run_hook_full(PRE_COMMIT_FROM_REF=base,
                               PRE_COMMIT_TO_REF=self.git("rev-parse", "HEAD"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("must not be pushed", r.stderr)
        self.assertNotIn("failed", r.stderr)

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

    def test_cleanup_push_deleting_remote_bad_content_is_allowed(self):
        self.commit({".env": "X=1\n", "a.md": HOME_LINE}, "bad, already on the remote")
        remote = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", remote)
        self.git("rm", "-q", ".env")
        self.commit({"a.md": "clean\n"}, "cleanup")
        self.assertEqual(self.run_range(remote), 0)

    def test_home_path_introduced_by_merge_resolution_then_removed(self):
        self.commit({"a.md": "base\n"}, "a")
        base = self.git("rev-parse", "HEAD")
        branch = self.git("rev-parse", "--abbrev-ref", "HEAD")
        self.git("checkout", "-q", "-b", "side")
        self.commit({"a.md": "side\n"}, "side")
        self.git("checkout", "-q", branch)
        self.commit({"a.md": "main\n"}, "main")
        merge = subprocess.run(["git", "merge", "side"], cwd=self.repo, env=_env(),
                               capture_output=True, text=True)
        self.assertNotEqual(merge.returncode, 0)  # conflict
        (self.repo / "a.md").write_text(HOME_LINE)
        self.git("add", "a.md")
        self.git("commit", "-q", "-m", "merge with bad resolution")
        self.commit({"a.md": "clean\n"}, "fix after merge")
        self.assertEqual(self.run_hook(), 0)
        self.assertEqual(self.run_range(base), 1)

    def test_merge_bringing_in_lines_is_not_reflagged(self):
        # New branch (zero from-ref). A remote-only parent carries a home-path line; a clean
        # merge of it must not be attributed to the merge commit (-m would flag it).
        branch = self.git("rev-parse", "--abbrev-ref", "HEAD")
        self.git("checkout", "-q", "-b", "remote-only")
        self.commit({"legacy.md": HOME_LINE}, "legacy, already on the remote")
        self.git("update-ref", "refs/remotes/origin/remote-only", "HEAD")
        self.git("checkout", "-q", branch)
        self.commit({"c.md": "main\n"}, "main")
        self.git("merge", "-q", "--no-edit", "remote-only")
        # The merged file is tracked, so the checkout scan would flag it; deleting it from the
        # working tree only (git grep skips missing files) isolates the pushed-range scan.
        (self.repo / "legacy.md").unlink()
        self.assertEqual(self.run_hook(PRE_COMMIT_FROM_REF="0" * 40,
                                       PRE_COMMIT_TO_REF=self.git("rev-parse", "HEAD")), 0)

    def test_forced_colour_does_not_hide_home_path(self):
        self.git("config", "color.ui", "always")
        self.git("config", "color.grep", "always")
        base = self.git("rev-parse", "HEAD")
        self.commit({"a.md": HOME_LINE}, "home")
        self.assertEqual(self.run_hook(), 1)
        self.remove("a.md", "rm")
        self.assertEqual(self.run_hook(), 0)
        self.assertEqual(self.run_range(base), 1)

    def test_forced_colour_does_not_hide_env_in_range(self):
        self.git("config", "color.ui", "always")
        base = self.git("rev-parse", "HEAD")
        self.commit({".env": "X=1\n"}, "env")
        self.remove(".env", "rm")
        self.assertEqual(self.run_range(base), 1)

    def _hook_copy(self, helper_text=None):
        d = Path(self._tmp.name + "-hook")
        d.mkdir()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        shutil.copy(SCRIPT, d / "pre_push.sh")
        if helper_text is not None:
            (d / "guard_scan.py").write_text(helper_text)
        return d / "pre_push.sh"

    def test_helper_crash_fails_closed(self):
        text = HELPER.read_text().replace(
            "def forbidden_paths(data):", "def forbidden_paths(data):\n    raise RuntimeError('boom')")
        r = self.run_hook_full(self._hook_copy(text))
        self.assertEqual(r.returncode, 1)
        self.assertIn("failed", r.stderr)

    def test_missing_helper_fails_closed(self):
        r = self.run_hook_full(self._hook_copy())
        self.assertEqual(r.returncode, 1)
        self.assertIn("failed", r.stderr)

    def test_run_from_subdirectory_with_relative_path(self):
        # The hook and helper are copied into the repo, so a helper path resolved after the
        # cd (relative to the repo top level) would not be found from the subdirectory.
        hooks = self.repo / "scripts" / "hooks"
        hooks.mkdir(parents=True)
        shutil.copy(SCRIPT, hooks / "pre_push.sh")
        shutil.copy(HELPER, hooks / "guard_scan.py")
        sub = self.repo / "sub" / "dir"
        sub.mkdir(parents=True)
        rel = os.path.relpath(hooks / "pre_push.sh", sub)
        self.assertEqual(self.run_hook(script=rel, cwd=sub), 0)
        self.commit({".env": "X=1\n"}, "env")
        self.assertEqual(self.run_hook(script=rel, cwd=sub), 1)

    def test_cdpath_does_not_break_helper_lookup(self):
        # A decoy directory on CDPATH has scripts/hooks/ but no helper; a plain `cd` to the
        # relative hook directory would land there.
        hooks = self.repo / "scripts" / "hooks"
        hooks.mkdir(parents=True)
        shutil.copy(SCRIPT, hooks / "pre_push.sh")
        shutil.copy(HELPER, hooks / "guard_scan.py")
        decoy = Path(self._tmp.name + "-decoy")
        (decoy / "scripts" / "hooks").mkdir(parents=True)
        self.addCleanup(shutil.rmtree, decoy, ignore_errors=True)
        self.assertEqual(self.run_hook(script="scripts/hooks/pre_push.sh", CDPATH=str(decoy)), 0)

    def test_root_commit_env_added_then_removed(self):
        # --root: a root commit in the range must be scanned (no remote refs, zero from-ref).
        self.git("checkout", "-q", "--orphan", "fresh")
        self.git("rm", "-rq", "--cached", ".")
        (self.repo / "README.md").unlink()
        self.commit({".env": "X=1\n"}, "root adds env")
        self.remove(".env", "rm env")
        self.assertEqual(self.run_hook(), 0)
        self.assertEqual(self.run_hook(PRE_COMMIT_FROM_REF="0" * 40,
                                       PRE_COMMIT_TO_REF=self.git("rev-parse", "HEAD")), 1)

    def test_root_commit_home_path_added_then_removed(self):
        self.git("checkout", "-q", "--orphan", "fresh")
        self.git("rm", "-rq", "--cached", ".")
        (self.repo / "README.md").unlink()
        self.commit({"a.md": HOME_LINE}, "root adds home path")
        self.remove("a.md", "rm")
        self.assertEqual(self.run_hook(PRE_COMMIT_FROM_REF="0" * 40,
                                       PRE_COMMIT_TO_REF=self.git("rev-parse", "HEAD")), 1)

    def test_symlink_env_changed_to_file_then_deleted(self):
        os.symlink("target", self.repo / ".env")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "env symlink, already on the remote")
        remote = self.git("rev-parse", "HEAD")
        (self.repo / ".env").unlink()
        self.commit({".env": "X=1\n"}, "symlink becomes a regular file (type change)")
        self.remove(".env", "rm env")
        self.assertEqual(self.run_range(remote), 1)

    def test_hook_python_is_the_test_interpreter_not_a_shim(self):
        path = _env()["PATH"].split(os.pathsep)
        self.assertEqual(os.path.realpath(os.path.join(path[0], "python3")),
                         os.path.realpath(sys.executable))
        # A stand-in shim later on PATH that fails without a tool-versions file in HOME.
        fake = Path(self._tmp.name + "-shim")
        fake.mkdir()
        self.addCleanup(shutil.rmtree, fake, ignore_errors=True)
        (fake / "python3").write_text('#!/bin/sh\n[ -f "$HOME/.tool-versions" ] || exit 3\n')
        (fake / "python3").chmod(0o755)
        path.insert(1, str(fake))
        self.assertEqual(self.run_hook(PATH=os.pathsep.join(path)), 0)

    def test_range_scans_use_plumbing_not_log(self):
        text = SCRIPT.read_text()
        self.assertNotIn("git log", text)
        self.assertEqual(len(re.findall(r"git rev-list \"\$\{RANGE\[@\]\}\" \|\s*\n\s*git diff-tree --stdin",
                                        text)), 2)

    def _signed_repo(self):
        wd = Path(self._tmp.name + "-key")
        wd.mkdir()
        self.addCleanup(shutil.rmtree, wd, ignore_errors=True)
        self.assertTrue(_configure_ssh_signing(self.repo, wd))
        self.git("config", "log.showSignature", "true")

    @unittest.skipUnless(ssh_signing_available(), "ssh commit signing unavailable (needs git >= 2.34 and ssh-keygen)")
    def test_show_signature_does_not_hide_env_in_range(self):
        self._signed_repo()
        base = self.git("rev-parse", "HEAD")
        self.commit({".env": "X=1\n"}, "add env")
        self.remove(".env", "rm env")
        self.assertEqual(self.run_hook(), 0)
        self.assertEqual(self.run_range(base), 1)

    @unittest.skipUnless(ssh_signing_available(), "ssh commit signing unavailable (needs git >= 2.34 and ssh-keygen)")
    def test_show_signature_does_not_hide_home_path_in_range(self):
        self._signed_repo()
        base = self.git("rev-parse", "HEAD")
        self.commit({"a.md": HOME_LINE}, "add")
        self.remove("a.md", "rm")
        self.assertEqual(self.run_range(base), 1)

    def test_env_added_only_in_merge_resolution_then_removed(self):
        self.commit({"a.md": "base\n"}, "a")
        base = self.git("rev-parse", "HEAD")
        branch = self.git("rev-parse", "--abbrev-ref", "HEAD")
        self.git("checkout", "-q", "-b", "side")
        self.commit({"a.md": "side\n"}, "side")
        self.git("checkout", "-q", branch)
        self.commit({"a.md": "main\n"}, "main")
        subprocess.run(["git", "merge", "side"], cwd=self.repo, env=_env(), capture_output=True)
        (self.repo / "a.md").write_text("resolved\n")
        (self.repo / ".env").write_text("X=1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "merge adding .env")
        self.remove(".env", "rm env")
        self.assertEqual(self.run_hook(), 0)
        self.assertEqual(self.run_range(base), 1)


class HelperTests(unittest.TestCase):
    def scan(self, mode, data):
        r = subprocess.run(["python3", str(HELPER), mode], input=data, capture_output=True)
        return r.returncode

    def test_added_lookbehind_cases(self):
        home = "/" + "home/u"
        users = "/" + "Users/u"
        hit = lambda text: self.scan("added", ("@@ -0,0 +1 @@\n+" + text + "\n").encode())
        self.assertEqual(hit("cd " + home), 0)
        self.assertEqual(hit(users + "/x"), 0)
        self.assertEqual(hit("(" + home + ")"), 0)
        self.assertEqual(hit("https://host" + home + "/x"), 1)
        self.assertEqual(hit("pre" + home), 1)
        self.assertEqual(hit("a-" + home), 1)
        self.assertEqual(hit("~" + home), 1)

    def test_added_ignores_headers_context_and_removals(self):
        home = "/" + "home/u"
        patch = ("diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1 +1 @@\n-" + home + "\n context " + home + "\n")
        self.assertEqual(self.scan("added", patch.encode()), 1)

    def test_combined_diff_needs_all_plus_columns(self):
        home = "/" + "home/u"
        # added against only the first parent: not a hit
        self.assertEqual(self.scan("added", ("@@@ -1 -1 +1 @@@\n+ " + home + "\n").encode()), 1)
        self.assertEqual(self.scan("added", ("@@@ -1 -1 +1 @@@\n +" + home + "\n").encode()), 1)
        self.assertEqual(self.scan("added", ("@@@ -1 -1 +1 @@@\n++" + home + "\n").encode()), 0)

    def test_paths(self):
        self.assertEqual(self.scan("paths", b"a/.env\0b.md\0"), 0)
        self.assertEqual(self.scan("paths", b"CONTEXT.md\0"), 0)
        self.assertEqual(self.scan("paths", b"docs/CONTEXT.md\0envoy.md\0config.env.md\0"), 1)

    def test_grep_mode(self):
        home = "/" + "home/u"
        self.assertEqual(self.scan("grep", ("f\0" + "1\0see " + home + "\n").encode()), 0)
        self.assertEqual(self.scan("grep", ("f\0" + "1\0see https://h" + home + "\n").encode()), 1)

    def test_bad_usage_fails(self):
        self.assertEqual(self.scan("nope", b""), 2)


class PortabilityTests(unittest.TestCase):
    def test_no_pcre_dependency(self):
        text = SCRIPT.read_text()
        self.assertIsNone(re.search(r"grep\b.*\s-[a-zA-Z]*P", text))
        self.assertNotIn("perl-regexp", text)
        self.assertNotIn("patternType", text)


if __name__ == "__main__":
    unittest.main()
