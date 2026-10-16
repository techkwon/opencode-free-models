# 비교 시험 자료 (2026-10-16)

무료 모델 5종과 클로드 모델 4종을 같은 문제 10개로 비교한 원본 자료입니다. 결과 요약은 저장소의 [README.md](../README.md#어떤-모델을-쓸까-직접-비교해-봤어요)에 있습니다.

| 경로 | 내용 |
|---|---|
| `tasks/T1.md` ~ `T10.md` | 모델에게 보낸 문제 원문 |
| `raw/oc_T*.json` | 무료 모델 5종의 답(`ask_opencode.py --json` 출력 그대로) |
| `raw/claude_*.md` | 클로드 모델 4종의 답(`_b`는 T8~T10) |
| `judge_rubric.md` | 블라인드 채점 기준(T4·T5·T6) |
| `judge_claude.json`, `judge_deepseek.txt` | 두 채점자의 점수(답안 A~I) |
| `blind_key.json` | 답안 A~I가 어느 모델인지 |
| `grade.py` | 답을 모으고 T1·T2·T3·T7·T8·T9·T10을 자동 채점, 블라인드 답안 묶음 생성 |
| `combine.py` | 자동 점수와 두 채점자 평균을 합쳐 `results.json` 생성 |
| `results.json` | 최종 점수, 채점 근거, 모든 답 |

## 다시 채점하기

```bash
cd benchmark
python grade.py
python combine.py
```

`grade.py`는 코드 답을 실제로 실행해 시험합니다. 모델이 쓴 코드이므로 믿을 수 있는 환경에서만 돌리세요.

## 새 모델로 다시 시험하기

무료 모델은 스킬 스크립트로 문제마다 이렇게 물었습니다.

```bash
python ../scripts/ask_opencode.py -m all --ok-shared --json --prompt-file tasks/T1.md > raw/oc_T1.json
```

클로드 모델은 Claude Code의 하위 에이전트에 도구 없이 문제를 주고, 답을 `raw/claude_<모델>.md`에 `===== T1 =====` 구분선으로 적게 했습니다.
