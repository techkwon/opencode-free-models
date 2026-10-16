#!/usr/bin/env python3
"""Ask OpenCode Zen free models through the opencode CLI and print their answers.

Works on Windows, macOS and Linux with Python 3.9+ and only the standard library.

Usage examples:
  python3 ask_opencode.py --check                      # is everything installed?
  python3 ask_opencode.py --list                       # models and data policies
  python3 ask_opencode.py -m deepseek "질문"
  python3 ask_opencode.py -m safe --prompt-file q.md   # deepseek + longcat, in parallel
  python3 ask_opencode.py -m all --ok-shared "질문"    # every free model, in parallel
  python3 ask_opencode.py -m deepseek -- "-로 시작하는 질문"

Safety (see SPEC.md section 6):
  * opencode runs with a throw-away config folder (XDG_CONFIG_HOME), without plugins
    (--pure) and without Claude Code rules (OPENCODE_DISABLE_CLAUDE_CODE=1).
  * The built-in read-only "plan" agent is used with edit, bash, web, sub-agent, skill
    and outside-folder access denied; its working folder is an empty temp folder.
  * Models whose provider keeps or trains on data need --ok-shared.
  * Prompts and text attachments containing phone numbers, e-mail addresses or
    resident registration numbers are refused. Attachments that cannot be scanned
    (images, PDFs, ...) need --ok-unscanned.
"""

import argparse
import concurrent.futures
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

__version__ = "1.2.0"

MODELS = {
    # alias: (model id, shares data?, note)
    "deepseek": ("deepseek-v4.1-flash-free", False, "기본. 빠름, 데이터 보관·학습 안 함"),
    "longcat": ("longcat-2.5-preview-free", False, "데이터 보관·학습 안 함. 공개 성능 수치 없음"),
    "muse": ("muse-spark-1.3-contributor-free", True, "가장 똑똑함. 느릴 수 있음. 입력을 Meta 학습에 씀"),
    "mimo": ("mimo-v2.6-flash-free", True, "무료 기간 데이터를 모델 개선에 씀. 느린 편"),
    "nemotron": ("nemotron-3.5-super-vl-free", True, "체험용, 사용 기록 남음. 가장 약함"),
}
SAFE_DEFAULT = ["deepseek", "longcat"]

# Tools denied for the "plan" agent. Denying every tool ("*") makes the Zen free tier
# reject the request, so read/list/glob/grep stay allowed but only inside the empty
# working folder (external_directory is denied).
DENIED_TOOLS = ["edit", "bash", "webfetch", "websearch", "external_directory",
                "task", "skill", "codesearch", "lsp"]
OPENCODE_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "agent": {"plan": {"permission": {name: "deny" for name in DENIED_TOOLS}}},
}
# Inherited settings that could re-enable plugins, MCP servers or permissions.
STRIP_ENV = ["OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR", "OPENCODE_CONFIG_CONTENT", "OPENCODE_PERMISSION"]

DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−－"), "-")
PII_PATTERNS = {
    "휴대전화 번호": re.compile(r"(?<!\d)(?:\+\s?82[-\s.]?\(?0?\)?|0)1[016789][-\s.)]{0,2}\d{3,4}[-\s.]?\d{4}(?!\d)"),
    "주민등록번호": re.compile(r"(?<!\d)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[-\s]?[1-8]\d{6}(?!\d)"),
    "이메일 주소": re.compile(r"[\w.+-]+\s?(?:@|＠)\s?[\w-]+(?:\.[\w-]+)+"),
}
TEXT_ENCODINGS = ("utf-8-sig", "cp949")  # UTF-16 is accepted only with a BOM
# Containers whose visible text is compressed or encoded: decoding the raw bytes is not a
# real privacy check, so they always count as "unscanned".
BINARY_EXTS = {
    ".pdf", ".hwp", ".hwpx", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt",
    ".ods", ".odp", ".rtf", ".epub", ".zip", ".7z", ".rar", ".gz", ".tar", ".cell", ".show",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".heic", ".tif", ".tiff", ".svg", ".ico",
    ".mp3", ".wav", ".m4a", ".mp4", ".mov", ".avi", ".webm", ".exe", ".dll", ".so", ".dylib",
}
BINARY_MAGIC = (b"%PDF", b"PK\x03\x04", b"\x89PNG", b"GIF8", b"\xff\xd8\xff", b"RIFF",
                b"\xd0\xcf\x11\xe0", b"{\\rtf", b"7z\xbc\xaf", b"Rar!", b"\x1f\x8b", b"MZ")

INLINE_LIMIT = 6000  # longer prompts go in an attached file (command line length limits)
IS_WINDOWS = os.name == "nt"
SHIM_SUFFIXES = {".cmd", ".bat", ".ps1"}


def die(message):
    """Stop before calling any model (exit code 2)."""
    print(message, file=sys.stderr)
    sys.exit(2)


def _usable(path):
    p = Path(path)
    if not p.is_file():
        return False
    if IS_WINDOWS:
        return p.suffix.lower() == ".exe"
    return os.access(p, os.X_OK)


def find_opencode():
    """Return the path of a real opencode executable (never a .cmd/.bat/.ps1 shim)."""
    override = os.environ.get("OPENCODE_BIN")
    if override:
        if Path(override).suffix.lower() in SHIM_SUFFIXES:
            die(f"OPENCODE_BIN에는 실행기(.cmd/.bat/.ps1)가 아니라 실제 실행 파일을 지정하세요: {override}")
        if _usable(override):
            return override
        die(f"OPENCODE_BIN이 가리키는 실행 파일이 없습니다: {override}")

    which = shutil.which("opencode")
    candidates = []
    if IS_WINDOWS:
        if which:
            p = Path(which)
            candidates += [p, p.parent / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"]
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "npm" / "node_modules" / "opencode-ai" / "bin" / "opencode.exe")
        candidates.append(Path.home() / ".opencode" / "bin" / "opencode.exe")
    else:
        if which:
            candidates.append(Path(which))
        candidates += [Path.home() / ".opencode" / "bin" / "opencode",
                       Path("/opt/homebrew/bin/opencode"), Path("/usr/local/bin/opencode"),
                       Path.home() / ".local" / "bin" / "opencode"]
    for c in candidates:
        if _usable(c):
            return str(c)
    hint = "`npm i -g opencode-ai`" if IS_WINDOWS else "`npm i -g opencode-ai` 또는 `brew install opencode`"
    die("opencode 실행 파일을 찾지 못했습니다. 설치: " + hint
        + "\n설치했는데도 이 메시지가 나오면 환경 변수 OPENCODE_BIN에 실행 파일 경로를 넣으세요."
        + ("" if IS_WINDOWS else " (nvm을 쓰면 새 터미널에서 다시 시도)"))


def resolve_models(spec):
    if spec == "all":
        return list(MODELS)
    if spec == "safe":
        return list(SAFE_DEFAULT)
    names = []
    for raw in spec.split(","):
        name = raw.strip().lower()
        if not name:
            continue
        if name in MODELS:
            names.append(name)
            continue
        bare = name[len("opencode/"):] if name.startswith("opencode/") else name
        matched = [k for k, v in MODELS.items() if v[0] == bare]
        if not matched:
            die(f"알 수 없는 모델: {raw}. 쓸 수 있는 이름: {', '.join(MODELS)}, safe, all")
        names.extend(matched)
    if not names:
        die("모델 이름이 비어 있습니다")
    return list(dict.fromkeys(names))


def find_pii(text):
    text = text.translate(DASHES)
    return [label for label, pat in PII_PATTERNS.items() if pat.search(text)]


def read_text(path):
    """Return the file's text, or None if it is not a plain text file we can scan."""
    if Path(path).suffix.lower() in BINARY_EXTS:
        return None
    data = Path(path).read_bytes()
    if data.startswith(BINARY_MAGIC):
        return None
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16")
        except UnicodeError:
            return None
    if b"\x00" in data[:4096]:
        return None
    for enc in TEXT_ENCODINGS:
        try:
            return data.decode(enc)
        except UnicodeError:
            continue
    return None


def safe_read_text(path, label):
    try:
        return read_text(path)
    except OSError as e:
        die(f"{label}을 읽지 못했습니다: {path} ({e.strerror or e})")


def parse_events(stdout):
    texts, errors, tokens = [], [], {"input": 0, "output": 0}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        part = ev.get("part")
        part = part if isinstance(part, dict) else {}
        kind = ev.get("type")
        if kind == "text" and isinstance(part.get("text"), str) and part["text"]:
            texts.append(part["text"])
        elif kind == "step_finish":
            t = part.get("tokens")
            t = t if isinstance(t, dict) else {}
            for key in ("input", "output"):
                if isinstance(t.get(key), (int, float)):
                    tokens[key] += int(t[key])
        elif kind == "error":
            err = ev.get("error", ev)
            msg = None
            if isinstance(err, dict):
                data = err.get("data")
                if isinstance(data, dict) and isinstance(data.get("message"), str):
                    msg = data["message"]
            errors.append(msg or json.dumps(err, ensure_ascii=False)[:500])
    return "\n".join(texts).strip(), errors, tokens


def build_command(exe, model_id, workdir, files, message, variant):
    cmd = [exe, "run", "--pure", "--agent", "plan", "--dir", str(workdir),
           "--format", "json", "-m", f"opencode/{model_id}"]
    if variant:
        cmd += ["--variant", variant]
    for f in files:
        cmd += ["-f", str(f)]
    cmd += ["--", message]
    return cmd


def build_env(config_home):
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env.update({
        "XDG_CONFIG_HOME": str(config_home),
        "OPENCODE_DISABLE_CLAUDE_CODE": "1",
        "OPENCODE_CONFIG_CONTENT": json.dumps(OPENCODE_CONFIG),
    })
    return env


def kill_tree(proc):
    try:
        if IS_WINDOWS:
            r = subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True, timeout=30)
            if r.returncode != 0:
                proc.kill()
        else:
            os.killpg(proc.pid, 9)
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


def _result(alias, model_id, start, answer="", errors=(), tokens=None):
    errors = [e for e in errors if e]
    return {"alias": alias, "model": model_id, "ok": bool(answer), "answer": answer,
            "error": "; ".join(errors), "seconds": round(time.time() - start, 1),
            "tokens": tokens or {"input": 0, "output": 0}}


def make_sandbox():
    """Create <base>/work (empty, opencode's project dir), <base>/files and <base>/config."""
    base = Path(tempfile.mkdtemp(prefix="oc_ask_"))
    dirs = base / "work", base / "files", base / "config"
    for d in dirs:
        d.mkdir()
    return (base,) + dirs


def config_problems(cfg):
    """Return reasons why the resolved opencode config is not isolated (empty list = fine)."""
    if not isinstance(cfg, dict):
        return ["설정을 읽지 못했습니다"]
    problems = []
    mcp = cfg.get("mcp") or {}
    if isinstance(mcp, dict):
        active = [name for name, v in mcp.items()
                  if not (isinstance(v, dict) and v.get("enabled") is False)]
        if active:
            problems.append("MCP 서버: " + ", ".join(active))
    if cfg.get("plugin"):
        problems.append("플러그인: " + ", ".join(map(str, cfg["plugin"])))
    if cfg.get("instructions"):
        problems.append("추가 지침: " + ", ".join(map(str, cfg["instructions"])))
    agent = cfg.get("agent") if isinstance(cfg.get("agent"), dict) else {}
    plan = agent.get("plan") if isinstance(agent.get("plan"), dict) else {}
    perms = plan.get("permission") if isinstance(plan.get("permission"), dict) else {}
    loose = [t for t in DENIED_TOOLS if perms.get(t) != "deny"]
    if loose:
        problems.append("막히지 않은 도구: " + ", ".join(loose))
    return problems


def preflight(exe):
    """Ask opencode for its resolved config under our isolation and refuse to run if
    anything else (managed, remote or parent-folder config) added tools, MCP servers,
    plugins or instructions."""
    base = None
    try:
        base, workdir, _, config_home = make_sandbox()
        r = subprocess.run([exe, "debug", "config", "--pure"], cwd=workdir, env=build_env(config_home),
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=120,
                           encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        die(f"opencode 설정 확인 실패: {e}")
    finally:
        if base is not None:
            shutil.rmtree(base, ignore_errors=True)
    out = r.stdout.strip()
    try:
        cfg = json.loads(out[out.index("{"):]) if "{" in out else None
    except (ValueError, json.JSONDecodeError):
        cfg = None
    if r.returncode != 0 or cfg is None:
        die("opencode 설정을 확인하지 못해 보내지 않았습니다(`opencode debug config` 실패). "
            "`npm i -g opencode-ai@latest`로 업데이트하세요.\n" + (r.stderr or r.stdout).strip()[-300:])
    problems = config_problems(cfg)
    if problems:
        die("opencode에 이 스킬이 끌 수 없는 설정(관리자·원격·상위 폴더 설정 등)이 있어 보내지 않았습니다:\n- "
            + "\n- ".join(problems))


def run_one(exe, alias, prompt, attachments, timeout, variant):
    model_id = MODELS[alias][0]
    start = time.time()
    base = None
    try:
        base, workdir, files_dir, config_home = make_sandbox()
        files = []
        if len(prompt) > INLINE_LIMIT:
            pf = files_dir / "_prompt" / "prompt.md"
            pf.parent.mkdir()
            pf.write_text(prompt, encoding="utf-8")
            files.append(pf)
            message = "Follow the request written in the attached prompt.md exactly and output only the answer."
        else:
            message = prompt
        for i, a in enumerate(attachments):
            dst = files_dir / f"a{i}" / Path(a).name
            dst.parent.mkdir()
            shutil.copyfile(a, dst)
            files.append(dst)

        cmd = build_command(exe, model_id, workdir, files, message, variant)
        popen_kw = {} if IS_WINDOWS else {"start_new_session": True}
        proc = subprocess.Popen(cmd, cwd=workdir, env=build_env(config_home),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, encoding="utf-8", errors="replace",
                                **popen_kw)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(proc)
            try:
                proc.communicate(timeout=15)
            except Exception:  # noqa: BLE001
                pass
            return _result(alias, model_id, start, errors=[f"{timeout}초 안에 끝나지 않았습니다"])

        answer, errors, tokens = parse_events(stdout)
        if proc.returncode != 0:
            errors.append(f"opencode 끝 코드 {proc.returncode}")
        if not answer and not errors:
            errors.append((stderr or stdout).strip()[-800:] or "빈 응답")
        elif not answer:
            tail = (stderr or "").strip()[-300:]
            if tail:
                errors.append(tail)
        return _result(alias, model_id, start, answer, errors, tokens)
    except Exception as e:  # noqa: BLE001 - one model failing must not lose the others
        return _result(alias, model_id, start, errors=[f"{type(e).__name__}: {e}"])
    finally:
        if base is not None:
            shutil.rmtree(base, ignore_errors=True)


REQUIRED_RUN_OPTIONS = ("--pure", "--format", "--dir", "--agent")


def has_option(help_text, opt):
    """True if `opt` starts a line of the help text as a whole option name
    (so "--pure-unsupported" does not count as "--pure")."""
    pattern = r"(?m)^\s*(?:-\w,\s*)?" + re.escape(opt) + r"(?=\s|=|,|$)"
    return re.search(pattern, help_text) is not None


def check_environment():
    print(f"ask_opencode {__version__}")
    print(f"운영체제: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"파이썬: {sys.version.split()[0]} ({sys.executable})")
    if sys.version_info < (3, 9):
        die("파이썬 3.9 이상이 필요합니다")
    exe = find_opencode()
    print(f"opencode: {exe}")
    try:
        ver = subprocess.run([exe, "--version"], capture_output=True, timeout=60,
                             encoding="utf-8", errors="replace")
        hlp = subprocess.run([exe, "run", "--help"], capture_output=True, timeout=60,
                             encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        die(f"opencode 실행 실패: {e}")
    version = (ver.stdout or ver.stderr).strip()
    if ver.returncode != 0 or not version:
        die(f"opencode --version 실패 (끝 코드 {ver.returncode}): {version[-300:]}")
    print(f"opencode 버전: {version}")
    if hlp.returncode != 0:
        die(f"opencode run --help 실패 (끝 코드 {hlp.returncode})")
    help_text = hlp.stdout + hlp.stderr
    missing = [opt for opt in REQUIRED_RUN_OPTIONS if not has_option(help_text, opt)]
    if missing:
        die("이 opencode에는 필요한 옵션이 없습니다: " + ", ".join(missing)
            + "\n`npm i -g opencode-ai@latest`로 업데이트하세요.")
    preflight(exe)
    print("격리 설정: 확인함 (MCP·플러그인·추가 지침 없음, 위험 도구 차단)")
    print("준비 완료. 시험 호출: ask_opencode.py -m deepseek \"한 문장으로 답해: 1+1은?\"")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="OpenCode Zen 무료 모델에 질문하기")
    ap.add_argument("prompt", nargs="?", help="보낼 질문(짧을 때). 길거나 특수 문자가 있으면 --prompt-file")
    ap.add_argument("--prompt-file", help="질문이 담긴 텍스트 파일(UTF-8 권장)")
    ap.add_argument("-m", "--model", default="deepseek",
                    help="deepseek(기본) | longcat | muse | mimo | nemotron | safe | all, 쉼표로 여러 개")
    ap.add_argument("-f", "--file", action="append", default=[], help="함께 보낼 파일(여러 번 가능)")
    ap.add_argument("--ok-shared", action="store_true",
                    help="데이터를 보관·학습하는 모델(muse, mimo, nemotron)에 보내도 되는 내용임을 확인함")
    ap.add_argument("--ok-unscanned", action="store_true",
                    help="개인정보 검사를 할 수 없는 첨부(이미지·PDF 등)를 직접 확인했음")
    ap.add_argument("--timeout", type=int, default=300, help="모델별 제한 시간(초), 기본 300")
    ap.add_argument("--variant", help="추론 강도(high, max, minimal 등, 모델이 지원할 때)")
    ap.add_argument("--json", action="store_true", help="결과를 JSON으로 출력")
    ap.add_argument("--list", action="store_true", help="쓸 수 있는 모델 목록")
    ap.add_argument("--check", action="store_true", help="파이썬·opencode 설치 상태 확인")
    ap.add_argument("--version", action="version", version=f"ask_opencode {__version__}")
    args = ap.parse_args(argv)

    if args.list:
        for alias, (mid, shares, note) in MODELS.items():
            flag = "학습/보관 O, --ok-shared 필요" if shares else "학습/보관 X"
            print(f"{alias:9} opencode/{mid:34} [{flag}] {note}")
        return 0
    if args.check:
        check_environment()
        return 0
    if args.timeout <= 0:
        die("--timeout은 1 이상이어야 합니다")

    if args.prompt_file:
        if not Path(args.prompt_file).is_file():
            die(f"질문 파일이 없습니다: {args.prompt_file}")
        prompt = safe_read_text(args.prompt_file, "질문 파일")
        if prompt is None:
            die(f"질문 파일을 글자로 읽지 못했습니다(UTF-8로 저장하세요): {args.prompt_file}")
    elif args.prompt is not None:
        prompt = args.prompt
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read()
    else:
        ap.error("질문을 주세요 (인자, --prompt-file, 또는 표준 입력)")
    prompt = prompt.strip()
    if not prompt:
        die("질문이 비어 있습니다")

    aliases = resolve_models(args.model)
    shared = [a for a in aliases if MODELS[a][1]]
    if shared and not args.ok_shared:
        die(f"{', '.join(shared)} 모델은 입력을 보관하거나 학습에 씁니다. "
            "개인정보·내부 자료가 없는 내용이면 --ok-shared를 붙이세요. 애매하면 deepseek이나 longcat을 쓰세요.")

    found = find_pii(prompt)
    unscanned = []
    for f in args.file:
        if not Path(f).is_file():
            die(f"첨부 파일이 없습니다: {f}")
        text = safe_read_text(f, "첨부 파일")
        if text is None:
            unscanned.append(f)
        else:
            found += find_pii(text)
    if found:
        die("개인정보로 보이는 내용이 있어 보내지 않았습니다: " + ", ".join(dict.fromkeys(found))
            + "\n해당 부분을 지우거나 [이름], [연락처]처럼 바꾼 뒤 다시 보내세요.")
    if unscanned and not args.ok_unscanned:
        die("다음 첨부는 글자가 아니라 개인정보 검사를 할 수 없습니다: " + ", ".join(unscanned)
            + "\n얼굴·이름·연락처 등이 없는지 직접 확인했으면 --ok-unscanned를 붙이세요.")

    exe = find_opencode()
    preflight(exe)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(aliases)) as pool:
        futures = [pool.submit(run_one, exe, a, prompt, args.file, args.timeout, args.variant)
                   for a in aliases]
        results = [f.result() for f in futures]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"===== {r['alias']} (opencode/{r['model']}) · {r['seconds']}초 =====")
            if r["ok"]:
                print(r["answer"])
                if r["error"]:
                    print(f"[주의] 답은 받았지만 오류도 있었습니다: {r['error']}")
            else:
                print(f"[실패] {r['error']}")
            print()
    return 0 if any(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
