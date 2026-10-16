# opencode-free-models

[![test](https://github.com/techkwon/opencode-free-models/actions/workflows/test.yml/badge.svg)](https://github.com/techkwon/opencode-free-models/actions/workflows/test.yml)

Claude Code가 **OpenCode Zen의 무료 AI 모델 5종**을 불러 쓸 수 있게 해 주는 스킬입니다.
"딥시크한테도 물어봐", "무료 모델끼리 비교해 봐"라고 말하면 Claude가 대신 묻고 답을 정리해 줍니다.
요금은 들지 않습니다.

> A Claude Code skill that lets Claude call OpenCode Zen's free models (DeepSeek, LongCat, Muse Spark, MiMo, Nemotron) through the `opencode` CLI, with privacy guards. Works on macOS, Windows and Linux. Docs are in Korean; see [SPEC.md](SPEC.md) for the full specification.

---

## 이런 걸 할 수 있어요

- 다른 AI의 의견 듣기: "이 수업 계획 딥시크는 어떻게 생각하는지 물어봐"
- 여러 모델 답 비교: "무료 모델 다섯 개한테 같은 질문 하고 비교해 줘"
- 초안 여러 개 받기: "롱캣이랑 딥시크한테 가정통신문 제목 5개씩 받아 줘"
- Claude가 스스로 교차 확인용으로 쓰기도 합니다

## 쓸 수 있는 모델

| 부르는 이름 | 모델 | 특징 | 내 데이터 |
|---|---|---|---|
| `deepseek` (기본) | DeepSeek V4.1 Flash | 클로드급 정확도, 빠름 | 보관·학습 안 함 ✅ |
| `longcat` | LongCat 2.5 Preview | 데이터 안전, 사실은 지어낼 수 있음 | 보관·학습 안 함 ✅ |
| `muse` | Muse Spark 1.3 (Meta) | 무료 중 점수 1위 | **Meta 학습에 쓰임** ⚠️ |
| `mimo` | MiMo-V2.6-Flash (Xiaomi) | 영상·소리 입력 | 무료 기간 개선에 쓰임 ⚠️ |
| `nemotron` | Nemotron 3.5 Super VL (NVIDIA) | 이미지 읽기, 영어로 답할 때 있음 | 체험용, 기록 남음 ⚠️ |

무료 모델은 **기간 한정**입니다. 목록이 바뀌면 [opencode.ai/docs/zen](https://opencode.ai/docs/zen)을 확인하세요.

---

## 어떤 모델을 쓸까? 직접 비교해 봤어요

2026-10-16, 무료 모델 5종과 클로드 모델 4종에 **같은 문제 10개**를 내고 채점했어요. 학교·사무 업무에 가까운 문제로 골랐어요.

### 결과 (100점 만점)

| 순위 | 모델 | 구분 | 총점 | 입력 데이터 | 한 줄 평 |
|---|---|---|---|---|---|
| 1 | Claude Opus 5.5 | 클로드 | **99** | 유료 서비스 정책 | 모든 문제에서 고르게 최고 |
| 2 | Muse Spark 1.3 | 무료 | **98.5** | ⚠️ Meta 학습에 씀 | 무료 중 1위, 클로드와 같은 수준 |
| 2 | Claude Fable 5.1 | 클로드 | 98.5 | 유료 서비스 정책 | |
| 4 | Claude Sonnet 5.5 | 클로드 | 98 | 유료 서비스 정책 | |
| 5 | Claude Haiku 5.5 | 클로드 | 97 | 유료 서비스 정책 | |
| 6 | DeepSeek V4.1 Flash | 무료 | **96.5** | ✅ 보관·학습 안 함 | 데이터가 안전한 무료 모델 중 1위 |
| 7 | Nemotron 3.5 Super VL | 무료 | 89 | ⚠️ 기록 남음 | 한국어 질문에 영어로 답함 |
| 8 | LongCat 2.5 Preview | 무료 | 83.5 | ✅ 보관·학습 안 함 | 없는 정책을 그럴듯하게 지어냄 |
| 9 | MiMo-V2.6-Flash | 무료 | 83 | ⚠️ 개선에 씀 | 까다로운 코딩에서 크게 틀림 |

### 문제별 점수 (각 10점)

| 문제 | Opus | Muse | Fable | Sonnet | Haiku | DeepSeek | Nemotron | LongCat | MiMo |
|---|---|---|---|---|---|---|---|---|---|
| T1 코딩 기초 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| T2 계산 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| T3 지시 따르기 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| T4 가정통신문 쓰기 | 10 | 9 | 9.5 | 9 | 9 | 9 | 8.5 | 9 | 8 |
| T5 없는 정책 질문 | 9 | 9.5 | 9 | 9 | 9 | 8 | **6.5** | **1** | 7.5 |
| T6 두 문장 요약 | 10 | 10 | 10 | 10 | 9 | 9.5 | 9.5 | 9 | 8 |
| T7 기초 지식 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| T8 숫자를 한글로 읽는 코딩 | 10 | 10 | 10 | 10 | 10 | 10 | 7.8 | 7.8 | **2.8** |
| T9 배수의 합 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| T10 맞춤법 찾기 | 10 | 10 | 10 | 10 | 10 | 10 | 6.7 | 6.7 | 6.7 |

### 눈에 띈 점

- **쉬운 문제는 모두 다 맞혔어요.** 코딩 기초, 계산, 지시 따르기, 기초 지식은 9종 모두 만점이에요. 차이는 아래 실수에서 났어요
- **LongCat은 사실을 지어냈어요.** 존재하지 않는 「AI 하늘반 3000」 정책을 물었더니 도입 연도·과목·출처까지 만들어 답했어요. 나머지 8종은 "확인되지 않는 정책"이라고 답했어요
- **Nemotron은 한국어 질문에 영어로 답한 적이 있어요.** 내용은 맞았지만 한국어 업무에는 불편해요
- **MiMo는 까다로운 규칙이 있는 코딩에서 크게 틀렸어요.** 숫자를 한글로 읽는 함수에서 시험 18개 중 5개만 통과했어요
- LongCat·Nemotron·MiMo는 맞춤법 문제에서 「뵈요 → 봬요」를 놓쳤어요. LongCat은 「봐요」로 잘못 고쳤어요

### 그래서 이렇게 고르세요

| 하려는 일 | 추천 | 이유 |
|---|---|---|
| 업무 문서 초안, 일반 질문 (기본) | `deepseek` | 클로드와 거의 같은 점수, 입력을 보관하지 않음 |
| 두 번째 의견 | `safe` (deepseek + longcat) | 둘 다 데이터 안전. 다만 LongCat의 사실 주장은 꼭 확인 |
| 개인정보가 전혀 없는 어려운 질문 | `muse` (`--ok-shared`) | 무료 중 가장 정확. 입력이 Meta 학습에 쓰임 |
| 사실·날짜·규정 확인 | 무료 모델에 맡기지 말기 | 지어내는 모델이 있음. 공식 자료로 확인 |
| 이미지 설명 | `nemotron` (`--ok-shared --ok-unscanned`) | 이미지 입력용. 한국어로 답하라고 꼭 적기 |

### 어떻게 시험했나

- **문제**: [benchmark/tasks/](benchmark/tasks/)에 원문이 있어요. 모든 모델에 같은 문제를 **한 번씩만** 물었어요
- **자동 채점**: 코딩은 실제로 실행해 테스트했고(T1 8개, T8 18개), 계산·규칙·단답·맞춤법은 정답과 맞춰 봤어요
- **블라인드 채점**: T4·T5·T6은 모델 이름을 가리고 순서를 섞은 뒤, Claude Opus와 DeepSeek가 [같은 기준](benchmark/judge_rubric.md)으로 따로 채점해 평균을 냈어요. 두 채점자의 점수는 대부분 1점 안쪽으로 같았어요
- **조건 차이**: 무료 모델은 이 스킬로, 클로드 모델은 Claude Code의 하위 에이전트로 물었어요
- **원본 자료**: 모든 답 원문은 [benchmark/raw/](benchmark/raw/), 점수는 [benchmark/results.json](benchmark/results.json)에 있어요. `python benchmark/grade.py && python benchmark/combine.py`로 채점을 다시 돌릴 수 있어요

### 결과를 읽을 때 주의할 점

- 문제가 10개뿐이고 한 번씩만 물어서 **1~2점 차이는 운에 따라 바뀔 수 있어요.** 지어내기·영어 답·코딩 실수 같은 큰 차이만 믿을 만한 신호로 보세요
- 채점자가 자기 계열 모델을 좋게 볼 가능성이 있어서, 서로 다른 회사 모델 두 개로 채점했어요
- 무료 모델은 수시로 바뀌어요. 이 결과는 2026-10-16 기준이에요
- 응답 시간은 무료 모델만 같은 방식으로 쟀어요. 문제 하나에 18~26초였어요(opencode 시작 시간 포함)

---

## 설치 (처음 한 번)

### 1단계. 준비물 설치

| 필요한 것 | macOS | Windows |
|---|---|---|
| [Claude Code](https://claude.com/claude-code) | 설치 안내 참고 | 설치 안내 참고 |
| Python 3.9 이상 | 보통 이미 있음 (`python3 --version`으로 확인) | [python.org](https://www.python.org/downloads/)에서 설치, "Add to PATH" 체크 |
| Node.js | [nodejs.org](https://nodejs.org/) 또는 `brew install node` | [nodejs.org](https://nodejs.org/) |
| opencode CLI | `npm i -g opencode-ai` 또는 `brew install opencode` | `npm i -g opencode-ai` |

### 2단계. 스킬 내려받기

**macOS / Linux** (터미널)
```bash
git clone https://github.com/techkwon/opencode-free-models.git ~/.claude/skills/opencode-free-models
```

**Windows** (PowerShell)
```powershell
git clone https://github.com/techkwon/opencode-free-models.git "$env:USERPROFILE\.claude\skills\opencode-free-models"
```

git이 없으면 GitHub 페이지의 **Code → Download ZIP**으로 받아서, 압축을 푼 폴더 이름을 `opencode-free-models`로 바꾼 뒤 위 위치(`~/.claude/skills/`)에 넣으면 됩니다.

### 3단계. 잘 되는지 확인

**macOS / Linux**
```bash
python3 ~/.claude/skills/opencode-free-models/scripts/ask_opencode.py --check
python3 ~/.claude/skills/opencode-free-models/scripts/ask_opencode.py -m deepseek "한 문장으로 답해: 1+1은?"
```

**Windows**
```powershell
python "$env:USERPROFILE\.claude\skills\opencode-free-models\scripts\ask_opencode.py" --check
python "$env:USERPROFILE\.claude\skills\opencode-free-models\scripts\ask_opencode.py" -m deepseek "한 문장으로 답해: 1+1은?"
```

`준비 완료`가 나오고 답이 오면 성공입니다. 이제 Claude Code를 새로 열고 "딥시크한테 물어봐"라고 말해 보세요.

---

## 개인정보 보호

이 스킬은 질문을 **외부 회사 서버**로 보냅니다. 그래서 여러 겹으로 막아 둡니다.

1. **스크립트가 자동으로 막음**: 휴대전화 번호, 주민등록번호, 이메일 주소가 보이면 보내지 않고 멈춥니다
2. **학습하는 모델은 한 번 더 확인**: `muse`, `mimo`, `nemotron`은 Claude가 `--ok-shared`(개인정보 없음 확인)를 붙여야만 보내집니다
3. **검사할 수 없는 파일도 확인**: 사진·PDF처럼 글자로 검사할 수 없는 첨부는 `--ok-unscanned`(직접 봤음)를 붙여야만 보내집니다
4. **Claude가 직접 확인**: 이름처럼 자동으로 못 잡는 정보는 Claude가 `[학생A]`처럼 바꿔서 보내고, 상담·건강 기록 같은 민감한 내용은 아예 보내지 않도록 SKILL.md에 적혀 있습니다

또 모델은 **빈 임시 폴더에서, 내 opencode 설정·플러그인 없이, 읽기 전용으로** 실행됩니다. 파일 고치기, 명령 실행, 인터넷 검색, 작업 폴더 밖 파일 읽기를 막아 두었고, 보내기 전에 opencode의 최종 설정을 점검해 회사·학교가 깔아 둔 설정 등으로 이 격리가 풀려 있으면 보내지 않습니다. 다만 운영체제 수준의 샌드박스는 아니고 opencode의 권한 기능에 기댑니다. 자세한 내용은 [SPEC.md 6절](SPEC.md#6-보안-설계)에 있습니다.

⚠️ 그래도 완벽하지 않습니다. 학생 기록, 비밀번호, 내부 문서는 처음부터 넣지 마세요.

---

## 자주 묻는 질문

**Q. 돈이 드나요?** 아니요. OpenCode Zen의 무료 모델만 씁니다. 무료 기간이 끝난 모델은 목록에서 빠집니다.

**Q. "opencode CLI를 찾지 못했습니다"라고 나와요.** 1단계의 opencode 설치를 다시 하세요. 다른 곳에 설치했다면 환경 변수 `OPENCODE_BIN`에 실행 파일 경로를 넣으세요.

**Q. 답이 너무 늦어요.** `muse`는 첫 글자까지 1분 가까이 걸릴 수 있습니다. 빠른 답이 필요하면 `deepseek`을 쓰세요.

**Q. 답을 그대로 믿어도 되나요?** 아니요. 무료 모델은 틀린 내용을 그럴듯하게 지어내기도 합니다. 날짜·숫자·규정은 꼭 확인하세요.

**Q. Claude가 알아서 쓰는 게 싫어요.** `SKILL.md` 맨 위 `description`에서 "Claude가 스스로 판단해 ... 사용한다" 문장을 지우면, 사용자가 부탁할 때만 씁니다.

---

## 폴더 구성

```
opencode-free-models/
├── SKILL.md                 # Claude가 읽는 사용 규칙
├── SPEC.md                  # 세부 명세 (동작·옵션·끝 코드·보안 설계)
├── README.md                # 이 문서
├── scripts/ask_opencode.py  # 모델을 부르는 스크립트 (파이썬 표준 라이브러리만 사용)
├── tests/test_ask_opencode.py  # 인터넷 없이 도는 테스트
└── benchmark/               # 무료 모델 대 클로드 비교 시험 자료 (문제, 답 원문, 채점 코드)
```

테스트 실행: `python3 -m unittest discover -s tests -v` (Windows는 `python`)

## 라이선스

MIT. 각 모델의 이용 약관과 데이터 정책은 OpenCode Zen과 모델 제공사를 따릅니다.
