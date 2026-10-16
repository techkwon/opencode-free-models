"""Collect answers from opencode (out/oc_T*.json) and Claude (out/claude_*.md), auto-grade
T1/T2/T3/T7, and write answers.json + auto_scores.json + blind packets for T4/T5/T6."""
import json, re, subprocess, sys, tempfile, random
from pathlib import Path

D = Path(__file__).parent
OUT = D / "raw"
TASKS = [f"T{i}" for i in range(1, 11)]

MODELS = {
    "deepseek": "DeepSeek V4.1 Flash", "longcat": "LongCat 2.5 Preview", "muse": "Muse Spark 1.3",
    "mimo": "MiMo-V2.6-Flash", "nemotron": "Nemotron 3.5 Super VL",
    "haiku": "Claude Haiku 5.5", "sonnet": "Claude Sonnet 5.5", "opus": "Claude Opus 5.5", "fable": "Claude Fable 5.1",
}

answers = {m: {} for m in MODELS}
seconds = {m: {} for m in MODELS}
for t in TASKS:
    p = OUT / f"oc_{t}.json"
    if p.exists() and p.stat().st_size:
        for r in json.loads(p.read_text(encoding="utf-8")):
            answers[r["alias"]][t] = r["answer"] if r["ok"] else ""
            seconds[r["alias"]][t] = r["seconds"]
for m, suffix in [(m, s) for m in ("haiku", "sonnet", "opus", "fable") for s in ("", "_b")]:
    p = OUT / f"claude_{m}{suffix}.md"
    if not p.exists():
        continue
    parts = re.split(r"^=====\s*(T\d+)\s*=====\s*$", p.read_text(encoding="utf-8"), flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        answers[m][parts[i]] = parts[i + 1].strip()


def g_t1(ans):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", ans, re.S)
    code = m.group(1) if m else ans
    cases = [([3, 1, 4, 4, 5], 4), ([5, 5], None), ([], None), ([-1, -2], -2), ([2, 3, 3], 2), ([7], None),
             ([1, 2, 3, 4, 5, 5, 5], 4), ([10, 9, 10, 8], 9)]
    test = code + "\nimport json\nres=[]\n"
    for args, exp in cases:
        test += f"try:\n    res.append(second_largest({args!r}) == {exp!r})\nexcept Exception:\n    res.append(False)\n"
    test += "print(json.dumps(res))\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(test)
    try:
        r = subprocess.run([sys.executable, "-I", f.name], capture_output=True, text=True, timeout=10)
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        res = [False] * len(cases)
    passed = sum(res)
    return round(10 * passed / len(cases), 1), f"테스트 {passed}/{len(cases)} 통과"


def g_t2(ans):
    lines = [l.strip() for l in ans.strip().splitlines() if l.strip()]
    last = lines[-1] if lines else ""
    if re.fullmatch(r"\**정답\s*:\s*14(명)?\**", last):
        return 10, "정답 14, 형식 맞음"
    if re.search(r"(?<!\d)14(?!\d)", last):
        return 7, "정답 14, 마지막 줄 형식 어긋남"
    return 0, f"오답 (마지막 줄: {last[:30]})"


def g_t3(ans):
    lines = [l for l in ans.strip().splitlines() if l.strip()]
    s, notes = 0, []
    if len(lines) == 3:
        s += 4
    else:
        notes.append(f"{len(lines)}줄")
    if lines and all(len(l.strip()) <= 40 for l in lines):
        s += 2
    else:
        notes.append("40자 초과: " + ", ".join(str(len(l.strip())) for l in lines if len(l.strip()) > 40))
    if not re.search(r"[A-Za-z]", ans):
        s += 2
    else:
        notes.append("알파벳 있음")
    if not any(re.match(r"\s*(\d+[.)]|[-*•·]|[\"'“‘「#])", l) for l in lines):
        s += 2
    else:
        notes.append("번호·기호 있음")
    return s, "규칙 모두 지킴" if not notes else "; ".join(notes)


def g_t7(ans):
    want = {1: ["1446"], 2: ["84"], 3: ["1024", "1,024"]}
    got, notes = 0, []
    for k, opts in want.items():
        m = re.search(rf"^\s*{k}\)\s*(.+)$", ans, re.M)
        val = m.group(1) if m else ""
        if any(o in val for o in opts):
            got += 1
        else:
            notes.append(f"{k}번 틀림({val.strip()[:12] or '없음'})")
    return round(10 * got / 3, 1), f"{got}/3 정답" + ("" if not notes else ": " + ", ".join(notes))


def _run_tests(code, fn, cases):
    test = code + "\nimport json\nres=[]\n"
    for args, exp in cases:
        test += f"try:\n    res.append({fn}({args!r}) == {exp!r})\nexcept Exception:\n    res.append(False)\n"
    test += "print(json.dumps(res))\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(test)
    try:
        r = subprocess.run([sys.executable, "-I", f.name], capture_output=True, text=True, timeout=10)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return [False] * len(cases)


def g_t8(ans):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", ans, re.S)
    code = m.group(1) if m else ans
    cases = [(0, "영"), (7, "칠"), (10, "십"), (11, "십일"), (100, "백"), (105, "백오"), (1000, "천"),
             (10000, "만"), (11000, "만천"), (12345, "만이천삼백사십오"), (20010, "이만십"),
             (1000000, "백만"), (30000507, "삼천만오백칠"), (99999999, "구천구백구십구만구천구백구십구"),
             (100000, "십만"), (10001, "만일"), (210000, "이십일만"), (12340000, "천이백삼십사만")]
    res = _run_tests(code, "korean_number", cases)
    return round(10 * sum(res) / len(cases), 1), f"테스트 {sum(res)}/{len(cases)} 통과"


def g_t9(ans):
    lines = [l.strip() for l in ans.strip().splitlines() if l.strip()]
    last = lines[-1] if lines else ""
    if re.fullmatch(r"\**정답\s*:\s*2,?103\**", last):
        return 10, "정답 2103, 형식 맞음"
    if re.search(r"2,?103", last):
        return 7, "정답 2103, 형식 어긋남"
    return 0, f"오답 (마지막 줄: {last[:30]})"


def g_t10(ans):
    want = {"금새": "금세", "뵈요": "봬요", "몇일": "며칠"}
    ok = [w for w, r in want.items() if re.search(rf"{w}\s*(→|->|=>)\s*{r}", ans)]
    false_pos = [w for w in ("왠지", "잃어버리", "조심", "도서관") if re.search(rf"^\s*\S*{w}\S*\s*(→|->|=>)", ans, re.M)]
    score = max(0, len(ok) - len(false_pos)) / 3 * 10
    note = f"{len(ok)}/3 찾음" + (f", 잘못 고침: {', '.join(false_pos)}" if false_pos else "")
    missing = [w for w in want if w not in ok]
    if missing:
        note += f", 놓침: {', '.join(missing)}"
    return round(score, 1), note


GRADERS = {"T1": g_t1, "T2": g_t2, "T3": g_t3, "T7": g_t7, "T8": g_t8, "T9": g_t9, "T10": g_t10}
auto = {m: {} for m in MODELS}
for m in MODELS:
    for t, g in GRADERS.items():
        a = answers[m].get(t, "")
        auto[m][t] = g(a) if a else (0, "답 없음")

(D / "answers.json").write_text(json.dumps({"models": MODELS, "answers": answers, "seconds": seconds},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
(D / "auto_scores.json").write_text(json.dumps(auto, ensure_ascii=False, indent=2), encoding="utf-8")

# Blind packets: shuffle model order per task, label A..I
rng = random.Random(20261016)
key = {}
for t in ("T4", "T5", "T6"):
    order = list(MODELS)
    rng.shuffle(order)
    labels = {chr(65 + i): m for i, m in enumerate(order)}
    key[t] = labels
    task = (D / "tasks" / f"{t}.md").read_text(encoding="utf-8")
    body = [f"# 과제 {t}\n\n## 문제\n{task}\n\n## 답안 (모델 이름은 가려져 있음)\n"]
    for lab, m in labels.items():
        body.append(f"### 답안 {lab}\n{answers[m].get(t) or '(답 없음)'}\n")
    (D / f"blind_{t}.md").write_text("\n".join(body), encoding="utf-8")
(D / "blind_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")

missing = {m: [t for t in TASKS if not answers[m].get(t)] for m in MODELS}
print("missing:", {m: v for m, v in missing.items() if v})
for m in MODELS:
    print(f"{m:9}", " ".join(f"{t}:{auto[m][t][0]:>4}" for t in GRADERS))
