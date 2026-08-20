# TC Playwright Code Conversion and Automated Execution
이 프로젝트는 **Google Sheets에 작성된 자연어 TestCase**를 자동으로 **Playwright 코드로 변환**하고, **실행, 재시도, 결과 저장**까지 수행하는 No-Code to Automated Testing 시스템입니다.
Playwright를 기반으로 하며, **Mac OS** 환경에서 구현되었으며 **PC 브라우저**에서 실행됩니다.

## branch 생성 기준
- 시작 날짜_branch명
 - 예시) 20260519_project_automation

---

## 📦 사전 요구사항

- **Python**: 3.11.14
- **Node.js**: 16.x 이상
- **Claude Code**: CLI 설치 필요
- **운영체제**: Mac OS (테스트 환경..Windows OS는 실행해보지 않음..)

---

## 🚀 설치 및 환경 구성

### 1. 저장소 클론 및 이동
```bash
git clone <https://github.com/hoyullee/tcautoplaywright.git>
cd tcautoplaywright
```

### 2. Python 가상환경 생성 및 활성화
```bash
python3.11 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows
```

### 3. Python 의존성 설치
```bash
pip install -r requirements.txt
```

또는 개별 설치:
```bash
pip install playwright requests pytest pytest-playwright pytest-asyncio
```

### 4. Playwright 브라우저 설치
```bash
playwright install chromium
```

### 5. pytest 설정 파일 생성 (설정되어 있음(변경 불필요))

프로젝트 루트에 `pytest.ini` 파일 생성:
```ini
[pytest]
# asyncio 자동 모드 활성화
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

# 테스트 디렉토리
testpaths = test

# 테스트 파일 패턴
python_files = test_*.py

# 상세 출력
addopts = -v --tb=short
```

### 6. Claude Code 설치 및 인증

#### 6-1. Claude Code 설치
```bash
# Mac (Homebrew)
npm install -g @anthropic-ai/claude-code

# 또는 직접 다운로드
# https://docs.anthropic.com/en/docs/claude-code
```

#### 6-2. 토큰 설정
```bash
# 토큰 발급
claude setup-token

# 토큰 복사 후 환경변수 설정 (일회용)
export CLAUDE_CODE_OAUTH_TOKEN=<your-token>

# 영구 설정 (권장)
nano ~/.zshrc
# 또는
nano ~/.bash_profile

# 파일 맨 아래에 추가:
export CLAUDE_CODE_OAUTH_TOKEN=<your-token>

# 저장 후 적용
source ~/.zshrc
```

#### 6-3. 토큰 확인
```bash
echo $CLAUDE_CODE_OAUTH_TOKEN
```

### 7. Google Drive 설정

#### 방법 : 파일 ID 직접 사용 (공유 드라이브에 생성해두어서 불필요하지만 필요한 사람은 변경 후 사용)
```python
# download_tc.py에서
GOOGLE_DRIVE_FILE_ID = 'your-file-id-here'
```
파일 ID는 Google Sheets에서 H1 체크박스 클릭 후 J1 셀에서 확인

---

## 📊 Google Sheets 설정

### 1. 스프레드시트 구조

**TC 시트** (테스트 케이스 작성):
```
| A (NO) | B (환경) | C (기능영역) | D (사전조건) | E (확인사항) | F (기대결과) |
|--------|---------|-------------|-------------|-------------|-------------|
| 1      | PC      | 로그인       | ...         | ...         | ...         |
| 2      | Mobile  | 검색        | ...         | ...         | ...         |
```

**H1 셀**: 체크박스 (자동화 트리거)  
**J1 셀**: 파일 ID (자동 저장)  
**K1 셀**: 업데이트 시간 (자동 저장)

### 2. Apps Script 설정

#### 2-1. Apps Script 열기
```
구글 시트 → 확장 프로그램 → Apps Script
```

#### 2-2. 코드 붙여넣기
제공된 `exportJson.gs` 코드 전체 복사 후 붙여넣기

#### 2-3. 설정 수정
```javascript
const DRIVE_FOLDER_ID = 'your-folder-id';  // Google Drive 폴더 ID
const FILE_NAME = 'test_cases.json';
```

#### 2-4. 트리거 설정
```
1. Apps Script 편집기 왼쪽 "트리거" 아이콘 (⏰) 클릭
2. "트리거 추가" 버튼 클릭
3. 설정:
   - 실행할 함수: onCheckboxEdit
   - 배포 시 실행: Head
   - 이벤트 소스: 스프레드시트에서
   - 이벤트 유형: 수정 시
4. "저장" 클릭
5. 권한 승인
```

---

## 🎯 사용 방법

### 전체 워크플로우

#### 1단계: Google Sheets에서 TC 작성
```
1. TC 시트에 테스트 케이스 작성
2. H1 셀의 체크박스 클릭
3. 사이드바에서 진행 상황 확인
4. J1 셀에 파일 ID 자동 저장됨
```

#### 2단계: 로컬에서 자동화 실행
```bash
# 활성화 (한 번만)
source venv/bin/activate

# TC 다운로드 + 코드 생성 + 실행 + 결과 저장
python run_automation.py
```

실행 로그는 `logs/` 폴더에서 확인 가능합니다.

---

## 🔧 실행 옵션

### 옵션 1: 전체 자동화 실행
```bash
python run_automation.py
```
- TC 다운로드
- Playwright 코드 생성
- 테스트 실행
- 결과 저장
- 모든 과정 자동화

### 옵션 2: 생성된 코드만 실행

#### pytest로 실행
```bash
# 전체 테스트 실행
pytest test/ -v

# 특정 폴더만 실행
pytest test/RESUME/ -v
pytest test/LOGIN/ -v

# 특정 테스트만 실행
pytest test/RESUME/test_RESUME_006_success.py -v
```

#### Python으로 직접 실행
```bash
# 개별 실행
python3 test/RESUME/test_RESUME_006_success.py
```

### 옵션 3: 전체 테스트 순차 실행 + 결과 요약

생성된 모든 테스트 파일을 `test_cases.json`의 NO 순서대로 실행하고, 종료 후 성공/실패 케이스를 요약합니다.

```bash
python3 run_all_tests.py
```

- 각 TC 실행 결과를 실시간으로 확인 가능
- LOGIN-005(로그아웃) 완료 후 LOGIN-003(로그인)을 자동 재실행하여 세션 복원
- 실패한 케이스는 `logs/failed_RESUME_006.log`에 실패 사유와 함께 저장
- 전체 종료 후 실패 케이스 목록 출력:
```
📊 최종 결과
✅ 성공: 59개  /  ❌ 실패: 2개  /  전체: 61개

❌ 실패한 케이스:
   RESUME-006  →  이력서 편집 페이지 진입 실패: https://...
               logs/failed_RESUME_006.log
```

### 옵션 4: 특정 테스트 케이스만 재생성

코드 생성에 실패한 특정 케이스만 TestCaseID로 지정하여 단독 재생성합니다.

```bash
python3 claude_automation.py --tc RESUME-006
python3 claude_automation.py --tc LOGIN-001
```

- `--tc` 옵션 사용 시 이미 생성된 파일이 있어도 강제로 덮어씁니다.
- 성공 시 `test/RESUME/test_RESUME_006_success.py`로 저장됩니다.
- 실패 시 마지막 시도 코드가 `test/RESUME/test_RESUME_006_failed.py`로 보존됩니다.

### 옵션 5: 중단 후 이어서 생성

스크립트 실행 중 중단한 경우, 다시 실행하면 **이미 생성된 케이스는 자동으로 스킵**하고 미완료 케이스부터 이어서 생성합니다.

```bash
# 중단 후 재실행 — 완료된 케이스 스킵, 미완료 케이스만 생성
python3 claude_automation.py
```

```
⏭️  [LOGIN-001] 이미 생성됨, 스킵
⏭️  [LOGIN-002] 이미 생성됨, 스킵
📝 테스트 3/72: LOGIN-003   ← 여기서부터 재개
```

### 옵션 6: 단계별 수동 실행
```bash
# 1. TC 다운로드만
python3 download_tc.py

# 2. 전체 코드 생성 (이어서 생성 가능)
python3 claude_automation.py

# 3. 특정 케이스만 재생성
python3 claude_automation.py --tc RESUME-006

# 4. 테스트 실행만
pytest test/ -v
```

---

## 💬 Slack 이모지로 실행하기

Slack 스레드에 지정한 이모지를 달면 **Mac 로컬에서 `run_all_tests.py`가 실행되고, 결과가 같은 스레드의 답글로 돌아옵니다.**

Socket Mode 방식이라 공개 URL이나 별도 서버가 필요 없습니다. 대신 리스너 프로세스가 Mac에서 상시 실행되어 있어야 합니다.

```
Slack 스레드에 :rocket: 클릭
   ↓ 1~2초
🚀 자동화 실행을 시작합니다. (요청: @홍길동)      ← 진행률로 계속 갱신됨
   ↓ run_all_tests.py 실행 (수십 분)
✅ 자동화 실행 완료 — 65/67 성공 (33분 20초)
   ✅ 성공 65    ❌ 실패 2    전체 67
   🔄 재생성 시도: RESUME-006, GNB-004
   📦 master 브랜치에 자동 푸시 완료 (abc1234)

   실패 케이스
   • RESUME-006 — 이력서 편집 페이지 진입 실패
   • GNB-004 — [재생성 후 실패] AssertionError...
   📎 failed_RESUME_006.log  📎 failed_GNB_004.log
```

### 1. Slack App 생성 (최초 1회)

**1-1. 앱 만들기**
```
https://api.slack.com/apps → Create New App → From scratch
앱 이름 입력 → 워크스페이스 선택 → Create App
```

**1-2. Socket Mode 활성화 + 앱 레벨 토큰 발급**
```
좌측 메뉴 Socket Mode → Enable Socket Mode 를 On
→ 토큰 이름 입력 (예: tcauto-socket)
→ Scope 에 connections:write 포함 확인 → Generate
→ 생성된 xapp-... 토큰 복사
```

**1-3. 봇 권한(Scope) 설정**
```
좌측 메뉴 OAuth & Permissions → Bot Token Scopes → Add an OAuth Scope
```
| Scope | 용도 |
|---|---|
| `reactions:read` | 이모지 추가 이벤트 수신 |
| `chat:write` | 스레드에 답글 작성·갱신 |
| `channels:history` | 리액션이 달린 메시지의 부모 스레드 확인 (공개 채널) |
| `groups:history` | 비공개 채널을 쓸 경우 추가 |
| `files:write` | 실패 로그 파일 첨부 |

**1-4. 이벤트 구독**
```
좌측 메뉴 Event Subscriptions → Enable Events 를 On
→ Subscribe to bot events → Add Bot User Event → reaction_added 추가
→ Save Changes
```

**1-5. 워크스페이스에 설치**
```
좌측 메뉴 Install App → Install to Workspace → 권한 승인
→ Bot User OAuth Token (xoxb-...) 복사
```
> 워크스페이스 정책에 따라 관리자 승인이 필요할 수 있습니다.

**1-6. 채널에 봇 초대 + 채널 ID 확인**
```
사용할 채널에서:  /invite @앱이름
채널 ID: 채널명 우클릭 → "링크 복사" → .../archives/C0XXXXXXX 의 C0XXXXXXX 부분
```

### 2. `.env` 설정

```bash
# Slack (필수)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_TRIGGER_CHANNELS=C0XXXXXXX        # 쉼표로 복수 지정 가능

# Slack (선택)
SLACK_TRIGGER_EMOJIS=rocket             # 기본값 rocket, 쉼표로 복수 지정
SLACK_ALLOWED_USERS=U01ABC,U02DEF       # 미지정 시 채널의 누구나 실행 가능
TCAUTO_RUN_TIMEOUT=7200                 # 실행 타임아웃(초)
TCAUTO_AUTO_PUSH=1                      # 재생성 성공 시 자동 푸시, 끄려면 0
TCAUTO_PUSH_BRANCH=master               # 자동 푸시 대상 브랜치

# 테스트 실행에 필요 (기존)
WANTED_TEST_EMAIL=...
WANTED_TEST_PASSWORD=...

# launchd 는 ~/.zshrc 를 읽지 않으므로 .env 에 반드시 넣어야 함
CLAUDE_CODE_OAUTH_TOKEN=...
```

> ⚠️ `SLACK_TRIGGER_CHANNELS`를 지정하지 않으면 리스너가 시작을 거부합니다. 아무 채널에서나 67개 테스트가 도는 것을 막기 위한 안전장치입니다.

### 3. 의존성 설치

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 먼저 포그라운드로 동작 확인

```bash
python3 slack_listener.py
```
```
============================================================
🔌 TC 자동화 Slack 리스너 (Socket Mode)
============================================================
저장소       : /Users/me/tcautoplaywright
트리거 채널  : C0XXXXXXX
트리거 이모지: :rocket:
허용 사용자  : 전원
자동 푸시    : ON
타임아웃     : 2시간 0분
============================================================
이모지 대기 중… (종료: Ctrl+C)
```

이 상태에서 해당 채널의 스레드에 `:rocket:`을 달아 답글이 오는지 확인합니다.

### 5. 상시 실행 등록 (launchd)

터미널을 닫아도 계속 살아있고, 프로세스가 죽으면 자동 재시작됩니다.

```bash
# 저장소 경로를 plist 에 반영
sed -i '' "s|__REPO_DIR__|$PWD|g" com.wanted.tcauto.slack.plist

# 등록 및 시작
cp com.wanted.tcauto.slack.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.wanted.tcauto.slack.plist

# 상태 확인
launchctl list | grep tcauto

# 로그 확인
tail -f logs/slack_listener.out

# 중지
launchctl unload -w ~/Library/LaunchAgents/com.wanted.tcauto.slack.plist
```

### 6. 동작 방식과 주의사항

| 항목 | 동작 |
|---|---|
| **트리거 범위** | 지정한 채널 + 지정한 이모지 + (설정 시) 허용된 사용자만 |
| **동시 실행** | 파일 락으로 차단. 실행 중 이모지를 달면 "이미 진행 중" 안내만 남김 |
| **중복 이벤트** | 같은 이벤트가 재전달되면 무시 (이모지를 떼고 다시 달면 재실행됨) |
| **절전 방지** | `caffeinate -i -s`로 감싸 실행 중 Mac이 잠들지 않게 함 |
| **타임아웃** | 기본 2시간 초과 시 프로세스 그룹 종료 후 스레드에 보고 |
| **민감정보** | 스레드에 올리는 모든 텍스트·첨부 로그에서 이메일·비밀번호·토큰·세션 쿠키 값을 마스킹 |
| **자동 푸시** | 재생성이 있었고 최종 실패가 0건이면 `TCAUTO_PUSH_BRANCH`에 커밋·푸시하고 결과 답글에 커밋 해시를 표시 |

> **노트북 뚜껑을 닫으면 중단됩니다.** `caffeinate`는 유휴 절전만 막습니다. 24시간 무인 운영이 필요하면 GitHub Actions 방식(`repository_dispatch`)으로 옮기는 것을 검토하세요.

### 7. 문제 해결

| 증상 | 확인 |
|---|---|
| 이모지를 달아도 반응 없음 | 봇이 채널에 초대되어 있는지 (`/invite @앱이름`), `SLACK_TRIGGER_CHANNELS`의 채널 ID가 맞는지, `logs/slack_listener.out` 확인 |
| `not_in_channel` 오류 | 봇을 해당 채널에 초대 |
| `missing_scope` 오류 | 위 Scope 표를 다시 확인하고 앱 재설치 |
| 재생성이 항상 실패 | `.env`에 `CLAUDE_CODE_OAUTH_TOKEN`이 있는지 확인 (launchd는 셸 프로필을 읽지 않음) |
| `git push` 실패 | launchd 환경의 자격증명 문제. `TCAUTO_AUTO_PUSH=0`으로 끄거나 keychain helper 설정 |

---

## 🐛 문제 해결

### Claude Code 토큰 만료

**증상:**
```
Authentication failed
```

**해결:**
```bash
# 토큰 재발급
claude setup-token

# 환경변수 재설정
export CLAUDE_CODE_OAUTH_TOKEN=<new-token>
```

### Google Drive 파일 다운로드 실패

**원인 1:** 파일 ID 틀림
```bash
# J1 셀에서 파일 ID 다시 확인
# download_tc.py에서 GOOGLE_DRIVE_FILE_ID 업데이트
```

**원인 2:** 권한 문제
```
Apps Script에서 파일 공유 설정 확인:
exportJson.gs에서 forceAuthorize 함수 실행하여 권한 승인 실행 후 재확인
```

---

## 📁 프로젝트 구조
```
sheets-automation/
├── venv/                       # Python 가상환경
├── test/                       # 생성된 Playwright 테스트 코드 (기능영역별 폴더)
│   ├── LOGIN/
│   │   ├── test_LOGIN_001_success.py
│   │   ├── test_LOGIN_002_success.py
│   │   └── test_LOGIN_003_failed.py   # 마지막 실패 시도 코드 보존
│   ├── RESUME/
│   │   ├── test_RESUME_001_success.py
│   │   └── ...
│   └── {기능영역}/
│       └── test_{기능영역}_{NNN}_{success|failed}.py
├── screenshots/                # 테스트 스크린샷
├── logs/                       # 실패한 케이스 로그 (run_all_tests.py 실행 시 생성)
│   ├── failed_RESUME_006.log   # 실패 사유 포함
│   ├── run_summary.json        # 실행 결과 요약 (Slack 리스너가 읽음)
│   └── slack_listener.out      # Slack 리스너 로그 (launchd 실행 시)
├── work/                       # 로그인 세션 파일
│   └── auth_state.json         # 로그인 세션 저장 파일
├── .github/
│   └── workflows/
│       └── run-tests.yml       # GitHub Actions 워크플로우
├── claude_automation.py        # Claude Code 기반 테스트 자동 생성
├── run_automation.py           # 전체 자동화 메인 스크립트
├── run_all_tests.py            # 전체 테스트 순차 실행 + 결과 요약
├── download_tc.py              # Google Drive TC 다운로드
├── slack_listener.py           # Slack 이모지 트리거 리스너 (Socket Mode)
├── com.wanted.tcauto.slack.plist  # 리스너 상시 실행용 launchd 설정
├── system_prompt.txt           # Claude 시스템 프롬프트 (코드 작성 규칙 포함)
├── test_cases.json             # 다운로드된 TC
├── pytest.ini                  # pytest 설정
├── requirements.txt            # Python 의존성
└── README.md
```

### 파일 명명 규칙
- 성공: `test/{PREFIX}/test_{PREFIX}_{NNN}_success.py`
- 실패 (마지막 시도 보존): `test/{PREFIX}/test_{PREFIX}_{NNN}_failed.py`
- PREFIX는 TestCaseID의 기능영역 (예: LOGIN, RESUME, PROFILE 등)

---

## 🔒 보안 주의사항

### 중요: 민감 정보 관리
```bash
# .gitignore에 추가 필수
test_cases.json
*.log
.env
venv/
__pycache__/
.pytest_cache/
screenshots/*.png
```

### 환경변수 관리
```bash
# 토큰은 절대 코드에 직접 입력 금지!
# 환경변수 사용:
export CLAUDE_CODE_OAUTH_TOKEN=<token>
export GOOGLE_API_KEY=<api-key>
```
