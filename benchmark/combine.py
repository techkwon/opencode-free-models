"""Merge auto scores + two blind judges into results.json for the report page."""
import json, re, statistics
from pathlib import Path

D = Path(__file__).parent
ans = json.loads((D / "answers.json").read_text(encoding="utf-8"))
auto = json.loads((D / "auto_scores.json").read_text(encoding="utf-8"))
key = json.loads((D / "blind_key.json").read_text(encoding="utf-8"))
jc = json.loads((D / "judge_claude.json").read_text(encoding="utf-8"))
raw = (D / "judge_deepseek.txt").read_text(encoding="utf-8")
jd = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])

TASKS = {
    "T1": ("코딩 기초", "두 번째로 큰 수 함수", "자동"),
    "T2": ("계산", "분수 문장제", "자동"),
    "T3": ("지시 따르기", "3문장·40자·영문 금지", "자동"),
    "T4": ("한국어 글쓰기", "가정통신문 문단", "블라인드"),
    "T5": ("지어내지 않기", "없는 정책 질문", "블라인드"),
    "T6": ("요약", "두 문장 요약", "블라인드"),
    "T7": ("기초 지식", "역사·도형·거듭제곱", "자동"),
    "T8": ("코딩 심화", "숫자를 한글로 읽기", "자동"),
    "T9": ("계산 심화", "배수의 합", "자동"),
    "T10": ("맞춤법", "틀린 낱말 찾기", "자동"),
}
GROUP = {"deepseek": "free", "longcat": "free", "muse": "free", "mimo": "free", "nemotron": "free",
         "haiku": "claude", "sonnet": "claude", "opus": "claude", "fable": "claude"}
POLICY = {"deepseek": "보관·학습 안 함", "longcat": "보관·학습 안 함", "muse": "Meta 학습에 씀",
          "mimo": "개선에 씀", "nemotron": "기록 남음·체험용",
          "haiku": "Anthropic 정책", "sonnet": "Anthropic 정책", "opus": "Anthropic 정책", "fable": "Anthropic 정책"}

scores, notes = {}, {}
for m in ans["models"]:
    scores[m], notes[m] = {}, {}
    for t in TASKS:
        if t in auto[m]:
            s, n = auto[m][t]
        else:
            lab = next(l for l, mm in key[t].items() if mm == m)
            a, b = jc[t][lab], jd[t][lab]
            s, n = round((a + b) / 2, 1), f"쿠리만쥬(클로드) {a}점 · 딥시크 {b}점"
        scores[m][t], notes[m][t] = s, n

def secs(m):
    v = [x for x in ans["seconds"][m].values() if x]
    return round(statistics.median(v), 1) if v else None

rows = []
for m, name in ans["models"].items():
    total = round(sum(scores[m].values()) / len(TASKS) * 10, 1)
    rows.append({"id": m, "name": name, "group": GROUP[m], "policy": POLICY[m], "total": total,
                 "scores": scores[m], "notes": notes[m], "median_seconds": secs(m)})
rows.sort(key=lambda r: -r["total"])

out = {"tasks": {t: {"area": a, "title": ti, "method": me,
                     "prompt": (D / "tasks" / f"{t}.md").read_text(encoding="utf-8")} for t, (a, ti, me) in TASKS.items()},
       "rows": rows, "answers": ans["answers"],
       "judge_notes": {"claude": jc.get("notes", {}), "deepseek": jd.get("notes", {})}}
(D / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
for r in rows:
    print(f"{r['name']:24} {r['total']:5}  " + " ".join(f"{t}:{r['scores'][t]:>4}" for t in TASKS), r["median_seconds"])
