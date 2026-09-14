import json
import subprocess
import os
import re
import sys
import shutil
import hashlib
import time
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

from ui_helpers import POPUPS

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()  # .env 파일 로드

# ========== 디렉토리 생성 ==========
for dir_name in ['test', 'screenshots', 'work']:
    Path(dir_name).mkdir(exist_ok=True)

# ========== 로깅 설정 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

AUTH_STATE_FILE = 'work/auth_state.json'


def requires_logged_in(precondition):
    """사전조건이 '로그인 상태'를 요구하는지.

    '비로그인 상태'에도 '로그인 상태'가 부분 문자열로 들어 있으므로
    앞 글자가 '비'인 경우는 제외한다.
    """
    return re.search(r'(?<!비)로그인 상태', precondition or '') is not None

def is_login_precondition(test_case):
    """사전조건이 '로그인 상태'인지 확인 → 저장된 세션 사용"""
    return requires_logged_in(test_case.get('사전조건', ''))

def is_login_action_test(test_case):
    """실제 로그인을 수행하고 세션을 저장해야 하는 케이스인지 확인"""
    precondition = test_case.get('사전조건', '')
    expected = test_case.get('기대결과', '')
    checks = test_case.get('확인사항', '')
    # 이미 로그인된 상태이거나, 비로그인 상태를 검증하는 케이스는 로그인을 수행하지 않는다
    if requires_logged_in(precondition) or '비로그인' in precondition:
        return False
    return '로그인' in expected or '로그인 버튼' in checks

def get_test_path_info(test_case):
    """TestCaseID로부터 (폴더명, 파일명 stem) 반환
    예) TestCaseID='RESUME-006' → ('RESUME', 'test_RESUME_006')
    """
    tc_id = test_case.get('TestCaseID', '')
    if tc_id and '-' in tc_id:
        prefix, num = tc_id.rsplit('-', 1)
        return prefix, f'test_{prefix}_{num}'
    # fallback: NO 번호
    no = str(test_case.get('NO', 0)).zfill(3)
    return 'MISC', f'test_MISC_{no}'

def is_popup_under_test(test_case):
    """이 TC 자체가 등록된 팝업의 노출·동작을 검증하는 케이스인지.

    이런 케이스에 공용 헬퍼를 쓰면 검증 대상이 먼저 닫혀 버리므로 제외해야 한다.
    """
    text = ' '.join(str(test_case.get(k, '')) for k in ('확인사항', '기대결과', '기능영역'))
    return any(p['has_text'] in text for p in POPUPS)


def build_popup_instruction(test_case):
    """방해 팝업 처리에 대한 TC별 지시문. 등록된 팝업 목록을 함께 알려 준다."""
    registered = '\n'.join(
        f"  - {p['name']} (식별 텍스트 '{p['has_text']}', 닫기 버튼 '{p['button']}')"
        for p in POPUPS) or '  - (등록된 팝업 없음)'

    if is_popup_under_test(test_case):
        return f"""
## 방해 팝업 처리
이 TC는 팝업 자체가 검증 대상으로 보입니다.
`dismiss_optional_popups` 를 **사용하지 마세요**. 헬퍼가 먼저 닫으면 검증할 대상이 사라집니다.
이 스크립트 안에서 직접 노출을 확인하고 닫으세요.
"""

    return f"""
## 방해 팝업 처리 (반드시 준수)
페이지 진입 직후, 실제 검증을 시작하기 전에 공용 헬퍼를 호출하세요.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups
...
await page.wait_for_load_state('domcontentloaded')
await dismiss_optional_popups(page)   # 검증 대상이 아닌 팝업 정리
```

현재 헬퍼에 등록된 팝업:
{registered}

등록되지 않은 새 팝업이 검증을 가로막으면, 스크립트에 개별 닫기 코드를 넣지 말고
`ui_helpers.py` 의 `POPUPS` 목록에 한 줄 추가한 뒤 위 헬퍼 호출만 남기세요.
"""


def create_claude_prompt(test_case):
    """Claude Code에 전달할 프롬프트 (TC 고유 정보만 포함, 정적 내용은 system_prompt.txt로 분리)"""

    test_email = os.getenv('WANTED_TEST_EMAIL', '')
    test_password = os.getenv('WANTED_TEST_PASSWORD', '')
    test_no = test_case.get('NO', '')
    folder, stem = get_test_path_info(test_case)

    use_saved_session = is_login_precondition(test_case)
    save_session = is_login_action_test(test_case)
    popup_instruction = build_popup_instruction(test_case)

    # 세션 관련 지시
    if use_saved_session:
        session_instruction = f"사전조건이 '로그인 상태'이므로 직접 로그인하지 말고 저장된 세션 파일을 로드하세요: storage_state='{AUTH_STATE_FILE}'"
    elif save_session:
        session_instruction = f"로그인 성공 후 반드시 세션을 저장하세요: await context.storage_state(path='{AUTH_STATE_FILE}')"
    else:
        session_instruction = ""

    # 로그인 계정 정보 (로그인 수행 케이스에만)
    login_info = f"테스트 계정 — 이메일: {test_email} / 비밀번호: {test_password}" if (save_session and test_email) else ""

    # 이력서 진입 코드 스니펫 주입
    # 사전조건이 "이력서 작성 페이지 진입 상태"이고 "기본 이력서"가 없으면 비기본 이력서 선택 코드 삽입
    precondition = test_case.get('사전조건', '')
    needs_non_basic_resume = '이력서 작성 페이지 진입 상태' in precondition and '기본 이력서' not in precondition
    resume_entry_snippet = f"""
## 이력서 진입 코드 (반드시 아래 코드를 그대로 복사해서 사용할 것)

사전조건의 "이력서 작성 페이지 진입"은 아래 코드로 구현합니다.
절대로 cv/edit, cv/new, cv/create, cv/write 링크를 직접 탐색하지 마세요.
절대로 "새 이력서 작성" 버튼을 먼저 클릭하지 마세요.

```python
# 이력서 목록 페이지 진입
await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
await page.wait_for_load_state('domcontentloaded')
await page.wait_for_timeout(3000)
assert 'cv/list' in page.url, f"이력서 목록 페이지 진입 실패: {{page.url}}"

# 최상위 이력서 카드만 선택 (:has로 하위 요소 제외)
# 기본 이력서는 항상 index 0이므로 index 1(두 번째 카드)이 첫 번째 비기본 이력서
all_cards = page.locator('[class*="ResumeItem_ResumeItem"]:has([class*="__title__"])')
total = await all_cards.count()

# 비기본 이력서(index 1 이상)가 없으면 새 이력서 생성
if total < 2:
    for kw in ['새 이력서 작성', '새 이력서']:
        btn = page.get_by_text(kw, exact=False)
        if await btn.count() > 0:
            await btn.first.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            break
    total = await all_cards.count()

assert total >= 2, "기본 이력서 외 이력서 카드가 없습니다"

# index 0 = 기본 이력서, index 1 = 첫 번째 비기본 이력서
await all_cards.nth(1).click()
await page.wait_for_load_state('domcontentloaded')
await page.wait_for_timeout(3000)
assert '/cv/' in page.url and 'cv/list' not in page.url, f"이력서 편집 페이지 진입 실패: {{page.url}}"
```
""" if needs_non_basic_resume else ""

    prompt = f"""## 테스트 케이스 정보
- 번호: {test_no}
- TestCase ID: {test_case.get('TestCaseID', '')}
- 기능영역: {test_case.get('기능영역', '')}
- 사전조건: {test_case.get('사전조건', '없음')}
- 확인사항: {test_case.get('확인사항', '')}
- 기대결과: {test_case.get('기대결과', '')}
{f'- {login_info}' if login_info else ''}
{f'- 세션: {session_instruction}' if session_instruction else ''}
{resume_entry_snippet}
{popup_instruction}
## 스크린샷 경로 (반드시 아래 문자열 그대로 사용)
- 성공 시: `await page.screenshot(path='screenshots/{stem}_success.png')`
- 실패 시: `await page.screenshot(path='screenshots/{stem}_failed.png')`
- 변수나 f-string 없이 위 문자열을 그대로 적을 것. 순번(NO) 기반 이름 금지.

## 작업
1. `test/{folder}/{stem}_success.py` 파일에 코드 작성
2. `python3 test/{folder}/{stem}_success.py` 실행
3. 실패 시 코드 수정 후 재시도 (파일명 변경 없이 덮어쓰기)
4. 마지막에 반드시 `AUTOMATION_SUCCESS` 또는 `AUTOMATION_FAILED: 에러메시지` 출력

지금 바로 시작하세요!
"""

    return prompt

def load_system_prompt():
    """system_prompt.txt 로드"""
    with open('system_prompt.txt', 'r', encoding='utf-8') as f:
        return f.read()

def _snapshot(path):
    """파일 내용 스냅샷 (파일이 없으면 None)"""
    try:
        return Path(path).read_bytes()
    except FileNotFoundError:
        return None


def _digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


_CLI_ERROR_KEYWORDS = (
    'does not have access',
    'Please login',
    'Invalid API key',
    'Credit balance',
    'usage limit',
    'rate limit',
    'Authentication',
    'Unauthorized',
    'not authenticated',
)

# claude CLI가 키체인 로그인보다 우선해서 사용하는 인증 환경 변수.
# 셸에 만료된 값이 남아 있으면 정상 로그인 상태여도 CLI가 실패한다.
_AUTH_ENV_VARS = (
    'CLAUDE_CODE_OAUTH_TOKEN',
    'ANTHROPIC_API_KEY',
    'ANTHROPIC_AUTH_TOKEN',
)

# 인증 실패로 볼 수 있는 메시지 패턴.
# 실제로 관측된 문구를 그대로 반영한다.
#   - Your organization does not have access to Claude. Please login again...
#   - Failed to authenticate. API Error: 401 {"type":"authentication_error",
#     "message":"OAuth access token has been revoked."}
_AUTH_ERROR_RE = re.compile(
    r'authentication_error'
    r'|failed to authenticate'
    r'|api error:\s*401'
    r'|\b401\b[^\n]{0,80}(?:unauthorized|authentic)'
    r'|(?:token|credential)s?[^\n]{0,40}revoked'
    r'|does not have access'
    r'|please login'
    r'|invalid api key'
    r'|\bunauthorized\b'
    r'|not authenticated'
    r'|인증 오류',
    re.IGNORECASE,
)

AUTH_GUIDE = ('터미널에서 `claude /login` 으로 다시 로그인한 뒤 실행하세요. '
              '`claude logout` 과 `claude setup-token` 은 기존 토큰을 무효화하므로 '
              '자동화 실행 중에는 사용하지 마세요.')


def _is_auth_error(message):
    return bool(_AUTH_ERROR_RE.search(message or ''))


def _stale_auth_vars():
    """현재 환경에 설정돼 있는 인증 환경 변수 이름 목록"""
    return [v for v in _AUTH_ENV_VARS if os.environ.get(v)]


def _child_env(drop_auth_vars):
    """자식 프로세스에 넘길 환경. drop_auth_vars=True 면 인증 변수를 제거한다."""
    if not drop_auth_vars:
        return None
    env = os.environ.copy()
    for v in _AUTH_ENV_VARS:
        env.pop(v, None)
    return env


def _meaningful_lines(text):
    """구분선·빈 줄을 제외한 의미 있는 출력 줄만 추린다."""
    return [s for s in ((raw.strip()) for raw in (text or '').splitlines())
            if s and not set(s) <= set('=-─· ')]


def _cli_error_line(stdout, stderr):
    """claude CLI가 남긴 오류 메시지 한 줄 추출"""
    out_lines = _meaningful_lines(stdout)
    err_lines = _meaningful_lines(stderr)
    for line in out_lines + err_lines:
        if any(k in line for k in _CLI_ERROR_KEYWORDS):
            return line[:200]
    tail = err_lines or out_lines
    return tail[-1][:200] if tail else '출력 없음'


def _preserve_or_restore(success_file, failed_file, original, changed, tc_id):
    """마지막 시도까지 실패했을 때 스크립트 정리.

    - 이번 실행에서 새로 만들어진 스크립트 → _failed.py 로 보존
    - 기존 스크립트를 덮어쓴 경우      → 실패본을 _failed.py 로 남기고 원본 복원
    - 파일이 전혀 바뀌지 않은 경우      → 손대지 않음 (멀쩡한 스크립트 삭제 방지)
    """
    if not changed:
        logging.info(f"ℹ️  [{tc_id}] 스크립트가 변경되지 않아 기존 파일을 그대로 둡니다")
        return
    if success_file.exists():
        shutil.move(str(success_file), str(failed_file))
        logging.info(f"📄 [{tc_id}] 실패 코드 보존: {failed_file}")
    if original is not None:
        success_file.write_bytes(original)
        logging.info(f"↩️  [{tc_id}] 이전 스크립트 복원: {success_file}")


def _cleanup_temp_files(test_dir, stem):
    """_success.py / _failed.py 외 동일 stem의 임시 파일 삭제 (예: _debug.py, _debug2.py)"""
    keep = {f'{stem}_success.py', f'{stem}_failed.py'}
    for f in test_dir.glob(f'{stem}_*.py'):
        if f.name not in keep:
            f.unlink()
            logging.info(f"🗑️  임시 파일 삭제: {f.name}")

def run_claude_code(prompt, test_case, max_attempts=3):
    """Claude Code 실행. (성공여부, 출력, 오류메시지) 반환

    성공 판정 기준
      1) claude CLI 종료 코드가 0이고
      2) 출력에 AUTOMATION_SUCCESS 가 있거나, 이번 실행에서 스크립트가 실제로 바뀐 경우
    이전 실행에서 만들어진 스크립트/스크린샷이 남아 있다는 이유만으로는 성공으로 보지 않는다.
    """

    system_prompt = load_system_prompt()
    tc_id = test_case.get('TestCaseID', '') or f"NO{test_case.get('NO', '?')}"
    folder, stem = get_test_path_info(test_case)
    test_dir = Path('test') / folder
    test_dir.mkdir(parents=True, exist_ok=True)

    success_file = test_dir / f'{stem}_success.py'
    failed_file = test_dir / f'{stem}_failed.py'

    # 실행 전 원본 보존 — 변경 여부 판단과 실패 시 원복에 사용
    original = _snapshot(success_file)
    original_digest = _digest(original)

    def invoke(env=None):
        return subprocess.run(
            [
                'claude',
                '--print',
                '--model', 'sonnet',
                '--dangerously-skip-permissions',
                '--system-prompt', system_prompt,
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=os.getcwd(),
            encoding='utf-8',
            errors='replace',
            shell=sys.platform == 'win32',
            env=env,
        )

    dropped_auth_env = False

    for attempt in range(1, max_attempts + 1):
        logging.info(f"🤖 [{tc_id}] 실행 시도 {attempt}/{max_attempts}")

        try:
            result = invoke(_child_env(dropped_auth_env))
            output = result.stdout or ''

            # 셸에 남아 있는 만료된 인증 토큰이 키체인 로그인을 가리는 경우가 있다.
            # 인증 오류면 해당 환경 변수를 빼고 같은 시도 안에서 한 번 더 호출한다.
            if result.returncode != 0 and not dropped_auth_env:
                stale = _stale_auth_vars()
                if stale and _is_auth_error(_cli_error_line(output, result.stderr)):
                    logging.warning(
                        f"⚠️ [{tc_id}] 인증 오류 — 셸에 남아 있는 "
                        f"{', '.join(stale)} 를 제외하고 다시 호출합니다")
                    dropped_auth_env = True
                    result = invoke(_child_env(True))
                    output = result.stdout or ''
                    if result.returncode == 0:
                        logging.info(
                            f"✅ [{tc_id}] 환경 변수 제외 후 정상 호출됨 "
                            f"(셸 설정에서 {', '.join(stale)} 를 정리하세요)")

            # Claude가 잘못된 경로에 파일을 생성한 경우 올바른 위치로 이동
            for misplaced in Path('test').rglob(f'{stem}_success.py'):
                if misplaced.resolve() != success_file.resolve():
                    shutil.move(str(misplaced), str(success_file))
                    logging.info(f"📦 파일 위치 정정: {misplaced} → {success_file}")
                    break

            changed = _digest(_snapshot(success_file)) != original_digest

            # 1) CLI 자체가 실패한 경우 (인증 오류, 사용량 초과 등) → 무조건 실패
            if result.returncode != 0:
                detail = _cli_error_line(output, result.stderr)
                logging.error(
                    f"❌ [{tc_id}] claude CLI 실패 (종료 코드 {result.returncode}) — {detail}")

                # 인증 문제는 재시도해도 결과가 같다. 시간만 쓰므로 즉시 중단한다.
                if _is_auth_error(detail):
                    logging.error(f"🔑 [{tc_id}] 인증 문제로 판단되어 재시도 없이 중단합니다.")
                    logging.error(f"🔑 {AUTH_GUIDE}")
                    _preserve_or_restore(success_file, failed_file, original, changed, tc_id)
                    return False, output, f"인증 오류 — {detail}"

                if attempt < max_attempts:
                    logging.info("🔄 재시도...")
                    time.sleep(5)
                    continue
                _preserve_or_restore(success_file, failed_file, original, changed, tc_id)
                return False, output, f"claude CLI 실패(종료 코드 {result.returncode}) — {detail}"

            # 2) 성공 마커가 있거나, 실패 마커 없이 스크립트가 실제로 갱신된 경우만 성공
            if 'AUTOMATION_SUCCESS' in output or (changed and 'AUTOMATION_FAILED:' not in output):
                if failed_file.exists():
                    failed_file.unlink()
                _cleanup_temp_files(test_dir, stem)
                logging.info(f"✅ [{tc_id}] 성공!")
                return True, output, None

            if 'AUTOMATION_FAILED:' in output:
                error_msg = output.split('AUTOMATION_FAILED:')[1].split('\n')[0].strip()
                logging.warning(f"❌ [{tc_id}] 실패: {error_msg}")
                if attempt < max_attempts:
                    logging.info("🔄 재시도...")
                    time.sleep(5)
                    continue
                _preserve_or_restore(success_file, failed_file, original, changed, tc_id)
                return False, output, error_msg

            logging.warning(f"⚠️ [{tc_id}] 결과 불명확 — 성공/실패 마커가 없고 스크립트 변경도 없음")
            if attempt < max_attempts:
                time.sleep(5)
                continue
            _preserve_or_restore(success_file, failed_file, original, changed, tc_id)
            return False, output, "결과 불명확"

        except subprocess.TimeoutExpired:
            logging.warning(f"⏱️ [{tc_id}] 타임아웃")
            if attempt >= max_attempts:
                return False, None, "타임아웃"

        except Exception as e:
            logging.error(f"⚠️ 예외: {e}")
            if attempt >= max_attempts:
                return False, None, str(e)

    return False, None, "최대 재시도 횟수 초과"

def main():
    """메인 함수"""

    parser = argparse.ArgumentParser()
    parser.add_argument('--tc', type=str, default=None, help='실행할 TestCaseID (예: --tc RESUME-006)')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🚀 Claude Code Playwright 자동화")
    print("=" * 60 + "\n")

    # test_cases.json 확인
    if not os.path.exists('test_cases.json'):
        logging.error("❌ test_cases.json 파일이 없습니다!")
        sys.exit(1)

    # 테스트 케이스 로드
    with open('test_cases.json', 'r', encoding='utf-8') as f:
        all_test_cases = json.load(f)

    # 특정 케이스만 필터링
    if args.tc is not None:
        test_cases = [tc for tc in all_test_cases if tc.get('TestCaseID') == args.tc]
        if not test_cases:
            logging.error(f"❌ TestCaseID '{args.tc}'를 찾을 수 없습니다!")
            sys.exit(1)
        logging.info(f"🎯 {args.tc} 단일 테스트 실행")
    else:
        test_cases = all_test_cases
        logging.info(f"📋 총 {len(test_cases)}개 테스트")

    # LOGIN-003 (로그인 세션 복원용) 미리 확보
    login_tc = next((tc for tc in all_test_cases if tc.get('TestCaseID') == 'LOGIN-003'), None)

    results = []

    for idx, test_case in enumerate(test_cases, 1):
        tc_id = test_case.get('TestCaseID', f"NO{test_case.get('NO', idx)}")
        folder, stem = get_test_path_info(test_case)
        success_file = Path('test') / folder / f'{stem}_success.py'

        print(f"\n{'='*60}")
        print(f"📝 테스트 {idx}/{len(test_cases)}: {tc_id}")
        print("="*60)

        if success_file.exists() and args.tc is None:
            print(f"⏭️  이미 생성됨, 스킵")
            results.append({'tc_id': tc_id, 'status': 'SKIPPED', 'error': None})
            continue

        prompt = create_claude_prompt(test_case)
        success, _, error = run_claude_code(prompt, test_case, max_attempts=3)

        results.append({
            'tc_id': tc_id,
            'status': 'SUCCESS' if success else 'FAILED',
            'error': error,
        })

        print(f"✅ 성공!" if success else f"❌ 실패! — {error or '원인 미확인'}")

        # LOGIN-005(로그아웃) 완료 후 LOGIN-003(로그인)으로 세션 복원
        if tc_id == 'LOGIN-005' and login_tc is not None:
            print(f"\n{'='*60}")
            print(f"🔄 LOGIN-005 로그아웃 완료 → LOGIN-003 재실행으로 세션 복원")
            print("="*60)
            time.sleep(2)
            login_prompt = create_claude_prompt(login_tc)
            login_success, _, login_error = run_claude_code(login_prompt, login_tc, max_attempts=3)
            print(f"{'✅ 세션 복원 성공!' if login_success else '❌ 세션 복원 실패: ' + str(login_error)}")

        if idx < len(test_cases):
            time.sleep(2)
    
    # 최종 리포트
    print(f"\n{'='*60}")
    print("📊 최종 결과")
    print("="*60)

    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    skipped_count = sum(1 for r in results if r['status'] == 'SKIPPED')
    failed_count  = sum(1 for r in results if r['status'] == 'FAILED')

    print(f"\n총 {len(test_cases)}개")
    print(f"✅ 성공: {success_count}개")
    print(f"⏭️  스킵: {skipped_count}개")
    print(f"❌ 실패: {failed_count}개")

    for r in results:
        if r['status'] == 'FAILED':
            print(f"   ❌ {r['tc_id']} — {r['error'] or '원인 미확인'}")

    # 호출한 쪽(run_all_tests.py)이 종료 코드로 성패를 판단할 수 있게 한다
    sys.exit(1 if failed_count else 0)

if __name__ == '__main__':
    main()