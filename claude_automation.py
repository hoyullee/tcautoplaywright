import json
import subprocess
import os
import sys
import shutil
import time
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

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


def is_login_precondition(test_case):
    """사전조건이 '로그인 상태'인지 확인 → 저장된 세션 사용"""
    return '로그인 상태' in test_case.get('사전조건', '')

def is_login_action_test(test_case):
    """실제 로그인을 수행하고 세션을 저장해야 하는 케이스인지 확인"""
    precondition = test_case.get('사전조건', '')
    expected = test_case.get('기대결과', '')
    checks = test_case.get('확인사항', '')
    return (
        '로그인 상태' not in precondition and
        ('로그인' in expected or '로그인 버튼' in checks)
    )

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

def create_claude_prompt(test_case):
    """Claude Code에 전달할 프롬프트 (TC 고유 정보만 포함, 정적 내용은 system_prompt.txt로 분리)"""

    test_email = os.getenv('WANTED_TEST_EMAIL', '')
    test_password = os.getenv('WANTED_TEST_PASSWORD', '')
    test_no = test_case.get('NO', '')
    folder, stem = get_test_path_info(test_case)

    use_saved_session = is_login_precondition(test_case)
    save_session = is_login_action_test(test_case)

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

def _cleanup_temp_files(test_dir, stem):
    """_success.py / _failed.py 외 동일 stem의 임시 파일 삭제 (예: _debug.py, _debug2.py)"""
    keep = {f'{stem}_success.py', f'{stem}_failed.py'}
    for f in test_dir.glob(f'{stem}_*.py'):
        if f.name not in keep:
            f.unlink()
            logging.info(f"🗑️  임시 파일 삭제: {f.name}")

def run_claude_code(prompt, test_case, max_attempts=3):
    """Claude Code 실행"""

    system_prompt = load_system_prompt()
    tc_id = test_case.get('TestCaseID', '') or f"NO{test_case.get('NO', '?')}"
    folder, stem = get_test_path_info(test_case)
    test_dir = Path('test') / folder
    test_dir.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max_attempts + 1):
        logging.info(f"🤖 [{tc_id}] 실행 시도 {attempt}/{max_attempts}")

        try:
            result = subprocess.run(
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
                shell=sys.platform == 'win32'
            )

            output = result.stdout

            if result.returncode != 0:
                logging.warning(f"⚠️ 종료 코드: {result.returncode}")

            success_file = test_dir / f'{stem}_success.py'
            failed_file  = test_dir / f'{stem}_failed.py'
            screenshot   = Path('screenshots') / f'{stem}_success.png'

            # Claude가 잘못된 경로에 파일을 생성한 경우 올바른 위치로 이동
            for misplaced in Path('test').rglob(f'{stem}_success.py'):
                if misplaced.resolve() != success_file.resolve():
                    shutil.move(str(misplaced), str(success_file))
                    logging.info(f"📦 파일 위치 정정: {misplaced} → {success_file}")
                    break

            if 'AUTOMATION_SUCCESS' in output or success_file.exists() or screenshot.exists():
                # 이전 실패 파일 및 중간 디버그 파일 정리
                if failed_file.exists():
                    failed_file.unlink()
                _cleanup_temp_files(test_dir, stem)
                logging.info(f"✅ [{tc_id}] 성공!")
                return True, output, None

            elif 'AUTOMATION_FAILED:' in output:
                error_msg = output.split('AUTOMATION_FAILED:')[1].split('\n')[0].strip()
                logging.warning(f"❌ [{tc_id}] 실패: {error_msg}")
                if attempt < max_attempts:
                    logging.info("🔄 재시도...")
                    time.sleep(5)
                else:
                    # 마지막 시도 실패 → success.py를 failed.py로 보존
                    if success_file.exists():
                        shutil.move(str(success_file), str(failed_file))
                        logging.info(f"📄 실패 코드 보존: {failed_file}")
                    return False, output, error_msg

            else:
                logging.warning(f"⚠️ 결과 불명확")
                if attempt < max_attempts:
                    time.sleep(5)
                else:
                    if success_file.exists():
                        shutil.move(str(success_file), str(failed_file))
                        logging.info(f"📄 실패 코드 보존: {failed_file}")
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
        return

    # 테스트 케이스 로드
    with open('test_cases.json', 'r', encoding='utf-8') as f:
        all_test_cases = json.load(f)

    # 특정 케이스만 필터링
    if args.tc is not None:
        test_cases = [tc for tc in all_test_cases if tc.get('TestCaseID') == args.tc]
        if not test_cases:
            logging.error(f"❌ TestCaseID '{args.tc}'를 찾을 수 없습니다!")
            return
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

        print(f"{'✅ 성공!' if success else '❌ 실패!'}")

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

if __name__ == '__main__':
    main()