"""Offline tests for ask_opencode.py (no network, no opencode needed).

Run:  python3 -m unittest discover -s tests -v      (Windows: python -m unittest ...)
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ask_opencode as ao  # noqa: E402


def run_main(argv):
    """Run main(); real model calls are blocked so a failing guard cannot reach the network."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    blocked = mock.patch.object(ao, "run_one", side_effect=AssertionError("model call not expected"))
    no_preflight = mock.patch.object(ao, "preflight", side_effect=AssertionError("preflight not expected"))
    with blocked, no_preflight, redirect_stdout(out), redirect_stderr(err):
        try:
            code = ao.main(argv)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


def no_override():
    return mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "OPENCODE_BIN"}, clear=True)


class ResolveModels(unittest.TestCase):
    def test_default_aliases(self):
        self.assertEqual(ao.resolve_models("deepseek"), ["deepseek"])
        self.assertEqual(ao.resolve_models("safe"), ["deepseek", "longcat"])
        self.assertEqual(ao.resolve_models("all"), list(ao.MODELS))

    def test_full_ids_and_dedup(self):
        self.assertEqual(ao.resolve_models("opencode/muse-spark-1.3-contributor-free, MUSE,deepseek"),
                         ["muse", "deepseek"])

    def test_unknown_model_stops(self):
        with self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
            ao.resolve_models("gpt-99")
        self.assertEqual(cm.exception.code, 2)


class Pii(unittest.TestCase):
    def test_detects(self):
        for text, label in [
            ("연락처 010-1234-5678", "휴대전화 번호"),
            ("01012345678", "휴대전화 번호"),
            ("010.1234.5678", "휴대전화 번호"),
            ("+82 10-1234-5678", "휴대전화 번호"),
            ("+82-10-1234-5678", "휴대전화 번호"),
            ("010\u20131234\u20135678", "휴대전화 번호"),  # en dash
            ("900101-1234567", "주민등록번호"),
            ("mail me: a.b@school.go.kr", "이메일 주소"),
        ]:
            with self.subTest(text=text):
                self.assertIn(label, ao.find_pii(text))

    def test_no_false_positive(self):
        for text in ["광합성을 한 문장으로 설명해 줘",
                     "@decorator\ndef f(): return 1234567890123",
                     "주문번호 20261016123456",
                     "2026-10-16 회의"]:
            with self.subTest(text=text):
                self.assertEqual(ao.find_pii(text), [])


class Guards(unittest.TestCase):
    def test_shared_model_needs_flag(self):
        code, _, err = run_main(["-m", "muse", "hello"])
        self.assertEqual(code, 2)
        self.assertIn("--ok-shared", err)

    def test_pii_blocks_before_call(self):
        with mock.patch.object(ao, "find_opencode") as fo:
            code, _, err = run_main(["-m", "deepseek", "학부모 010-1234-5678"])
        self.assertEqual(code, 2)
        self.assertIn("휴대전화 번호", err)
        fo.assert_not_called()

    def test_pii_in_attached_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.txt"
            p.write_text("이메일 x@y.com", encoding="utf-8")
            code, _, err = run_main(["-m", "deepseek", "-f", str(p), "요약해 줘"])
        self.assertEqual(code, 2)
        self.assertIn("이메일 주소", err)

    def test_missing_prompt_file(self):
        code, _, err = run_main(["--prompt-file", "no/such/file.md"])
        self.assertEqual(code, 2)
        self.assertIn("질문 파일이 없습니다", err)

    def test_prompt_file_utf16_scanned(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "q.txt"
            p.write_text("연락처 010-2222-3333", encoding="utf-16")
            code, _, err = run_main(["--prompt-file", str(p)])
        self.assertEqual(code, 2)
        self.assertIn("휴대전화 번호", err)

    def test_prompt_file_cp949_scanned(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "q.txt"
            p.write_bytes("연락처 010-2222-3333".encode("cp949"))
            code, _, err = run_main(["--prompt-file", str(p)])
        self.assertEqual(code, 2)
        self.assertIn("휴대전화 번호", err)

    def test_binary_attachment_needs_flag(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "img.png"
            p.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")
            code, _, err = run_main(["-m", "deepseek", "-f", str(p), "설명해 줘"])
        self.assertEqual(code, 2)
        self.assertIn("--ok-unscanned", err)

    def test_pdf_like_text_is_unscanned(self):
        with tempfile.TemporaryDirectory() as d:
            for name, data in [("a.pdf", b"plain words"), ("b.bin", b"%PDF-1.7 ascii body"),
                               ("c.hwpx", b"text"), ("d.txt", b"PK\x03\x04zip")]:
                p = Path(d) / name
                p.write_bytes(data)
                with self.subTest(name=name):
                    self.assertIsNone(ao.read_text(p))
            p = Path(d) / "ok.md"
            p.write_text("보통 글", encoding="utf-8")
            self.assertEqual(ao.read_text(p), "보통 글")

    def test_unreadable_attachment_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.txt"
            p.write_text("x", encoding="utf-8")
            with mock.patch.object(ao, "read_text", side_effect=PermissionError(13, "Permission denied")):
                code, _, err = run_main(["-m", "deepseek", "-f", str(p), "요약"])
        self.assertEqual(code, 2)
        self.assertIn("읽지 못했습니다", err)

    def test_list(self):
        code, out, _ = run_main(["--list"])
        self.assertEqual(code, 0)
        for alias in ao.MODELS:
            self.assertIn(alias, out)


class FindOpencode(unittest.TestCase):
    def test_env_override(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / ("opencode.exe" if ao.IS_WINDOWS else "opencode")
            path.write_bytes(b"")
            path.chmod(0o755)
            with mock.patch.dict(os.environ, {"OPENCODE_BIN": str(path)}):
                self.assertEqual(ao.find_opencode(), str(path))

    def test_env_override_rejects_shim(self):
        with mock.patch.dict(os.environ, {"OPENCODE_BIN": "C:/npm/opencode.cmd"}), \
             self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
            ao.find_opencode()
        self.assertEqual(cm.exception.code, 2)

    def test_posix_uses_which(self):
        target = "/opt/homebrew/bin/opencode"
        with no_override(), mock.patch.object(ao, "IS_WINDOWS", False), \
             mock.patch.object(ao, "_usable", side_effect=lambda p: Path(p) == Path(target)), \
             mock.patch.object(ao.shutil, "which", return_value=target):
            self.assertEqual(Path(ao.find_opencode()), Path(target))

    def test_posix_curl_install_without_path(self):
        target = Path.home() / ".opencode" / "bin" / "opencode"
        with no_override(), mock.patch.object(ao, "IS_WINDOWS", False), \
             mock.patch.object(ao, "_usable", side_effect=lambda p: Path(p) == target), \
             mock.patch.object(ao.shutil, "which", return_value=None):
            self.assertEqual(Path(ao.find_opencode()), target)

    def test_windows_prefers_exe_next_to_npm_shim(self):
        with tempfile.TemporaryDirectory() as d:
            npm = Path(d) / "npm"
            exe = npm / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"")
            shim = npm / "opencode.cmd"
            shim.write_text("@echo off", encoding="utf-8")
            with no_override(), mock.patch.object(ao, "IS_WINDOWS", True), \
                 mock.patch.object(ao.shutil, "which", return_value=str(shim)):
                self.assertEqual(ao.find_opencode(), str(exe))

    def test_windows_never_returns_shim(self):
        with no_override(), mock.patch.object(ao, "IS_WINDOWS", True), \
             mock.patch.object(ao, "_usable", return_value=False), \
             mock.patch.object(ao.shutil, "which", return_value="C:/npm/opencode.cmd"), \
             self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
            ao.find_opencode()
        self.assertEqual(cm.exception.code, 2)


class FakeProc:
    pid, returncode = 1, 0

    def communicate(self, timeout=None):
        return (json.dumps({"type": "text", "part": {"text": "ok"}}), "")


class RunOne(unittest.TestCase):
    def test_exception_becomes_failure_result(self):
        with mock.patch.object(ao.subprocess, "Popen", side_effect=OSError("boom")):
            r = ao.run_one("opencode", "deepseek", "hi", [], 5, None)
        self.assertFalse(r["ok"])
        self.assertIn("boom", r["error"])

    def test_isolation_and_attachments(self):
        seen = {}

        def fake_popen(cmd, **kw):
            files = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-f"]
            seen["files"] = [Path(f).read_text(encoding="utf-8") for f in files]
            seen["env"], seen["cwd"], seen["cmd"] = kw["env"], kw["cwd"], cmd
            seen["cwd_items"] = list(Path(kw["cwd"]).iterdir())
            return FakeProc()

        long_prompt = "가" * (ao.INLINE_LIMIT + 1)
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "x" / "prompt.md", Path(d) / "y" / "prompt.md"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_text("A", encoding="utf-8")
            b.write_text("B", encoding="utf-8")
            with mock.patch.object(ao.subprocess, "Popen", side_effect=fake_popen):
                r = ao.run_one("opencode", "deepseek", long_prompt, [str(a), str(b)], 5, None)
        self.assertTrue(r["ok"])
        self.assertEqual(seen["files"], [long_prompt, "A", "B"])  # same-name files kept apart
        self.assertEqual(seen["cwd_items"], [])  # model's working folder is empty
        self.assertFalse(Path(seen["cwd"]).exists())  # cleaned up afterwards
        env = seen["env"]
        self.assertEqual(env["OPENCODE_DISABLE_CLAUDE_CODE"], "1")
        self.assertIn("XDG_CONFIG_HOME", env)
        perms = json.loads(env["OPENCODE_CONFIG_CONTENT"])["agent"]["plan"]["permission"]
        for tool in ("edit", "bash", "external_directory", "webfetch"):
            self.assertEqual(perms[tool], "deny")
        self.assertIn("--pure", seen["cmd"])


    def test_sandbox_creation_error_is_contained(self):
        with mock.patch.object(ao.tempfile, "mkdtemp", side_effect=OSError("disk full")):
            r = ao.run_one("opencode", "deepseek", "hi", [], 5, None)
        self.assertFalse(r["ok"])
        self.assertIn("disk full", r["error"])


class Preflight(unittest.TestCase):
    GOOD = {"agent": {"plan": {"permission": {t: "deny" for t in ao.DENIED_TOOLS}}},
            "plugin": [], "mcp": None, "instructions": None}

    def test_clean_config(self):
        self.assertEqual(ao.config_problems(self.GOOD), [])

    def test_detects_injected_settings(self):
        bad = json.loads(json.dumps(self.GOOD))
        bad["mcp"] = {"gh": {"type": "remote"}, "off": {"enabled": False}}
        bad["plugin"] = ["evil-plugin"]
        bad["instructions"] = ["/etc/rules.md"]
        bad["agent"]["plan"]["permission"]["bash"] = "allow"
        problems = " ".join(ao.config_problems(bad))
        for word in ("gh", "evil-plugin", "/etc/rules.md", "bash"):
            self.assertIn(word, problems)
        self.assertNotIn("off", problems)

    def test_preflight_refuses_bad_config(self):
        bad = json.loads(json.dumps(self.GOOD))
        bad["plugin"] = ["x"]
        done = mock.Mock(returncode=0, stdout="log line\n" + json.dumps(bad), stderr="")
        with mock.patch.object(ao.subprocess, "run", return_value=done), \
             self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
            ao.preflight("opencode")
        self.assertEqual(cm.exception.code, 2)

    def test_preflight_accepts_good_config(self):
        done = mock.Mock(returncode=0, stdout=json.dumps(self.GOOD), stderr="")
        with mock.patch.object(ao.subprocess, "run", return_value=done) as run:
            ao.preflight("opencode")
        cmd, kw = run.call_args[0][0], run.call_args[1]
        self.assertEqual(cmd[1:3], ["debug", "config"])
        self.assertEqual(kw["env"]["OPENCODE_DISABLE_CLAUDE_CODE"], "1")

    def test_preflight_sandbox_error_exit_2(self):
        with mock.patch.object(ao.tempfile, "mkdtemp", side_effect=OSError("disk full")), \
             self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
            ao.preflight("opencode")
        self.assertEqual(cm.exception.code, 2)

    def test_has_option_whole_name(self):
        help_text = "Options:\n  -m, --model  model\n      --pure-unsupported  x\n      --dir=PATH\n"
        self.assertFalse(ao.has_option(help_text, "--pure"))
        self.assertTrue(ao.has_option(help_text, "--model"))
        self.assertTrue(ao.has_option(help_text, "--dir"))
        self.assertTrue(ao.has_option("      --pure         run without plugins", "--pure"))
        self.assertTrue(ao.has_option("      --pure", "--pure"))

    def test_preflight_fails_closed(self):
        done = mock.Mock(returncode=1, stdout="", stderr="unknown command")
        with mock.patch.object(ao.subprocess, "run", return_value=done), \
             self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
            ao.preflight("opencode")
        self.assertEqual(cm.exception.code, 2)


class Parsing(unittest.TestCase):
    def test_parse_events(self):
        lines = [
            json.dumps({"type": "step_start", "part": {}}),
            "garbage line",
            json.dumps({"type": "text", "part": {"text": "안녕"}}),
            json.dumps({"type": "step_finish", "part": {"tokens": {"input": 10, "output": 3}}}),
        ]
        answer, errors, tokens = ao.parse_events("\n".join(lines))
        self.assertEqual(answer, "안녕")
        self.assertEqual(errors, [])
        self.assertEqual(tokens, {"input": 10, "output": 3})

    def test_parse_events_tolerates_odd_shapes(self):
        lines = [
            json.dumps({"type": "text", "part": "not a dict"}),
            json.dumps({"type": "step_finish", "part": {"tokens": {"input": "x"}}}),
            json.dumps({"type": "error", "error": {"data": {"message": "free tier"}}}),
            json.dumps([1, 2]),
        ]
        answer, errors, tokens = ao.parse_events("\n".join(lines))
        self.assertEqual(answer, "")
        self.assertEqual(errors, ["free tier"])
        self.assertEqual(tokens, {"input": 0, "output": 0})

    def test_build_command_isolated(self):
        cmd = ao.build_command("opencode", "deepseek-v4.1-flash-free", "/tmp/x", ["/tmp/f/p.md"], "-hi", None)
        self.assertEqual(cmd[:4], ["opencode", "run", "--pure", "--agent"])
        self.assertIn("plan", cmd)
        self.assertEqual(cmd[-2:], ["--", "-hi"])  # message starting with '-' is not read as a flag
        self.assertIn("opencode/deepseek-v4.1-flash-free", cmd)


if __name__ == "__main__":
    unittest.main()
