import json
import subprocess
import os
import sys
import shutil
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()  # .env 파일 로드

# ========== 디렉토리 생성 ==========
for dir_name in ['test', 'test_results', 'screenshots', 'logs', 'work']:  # ⭐ test_results 추가
    Path(dir_name).mkdir(exist_ok=True)

# ========== 로깅 설정 ==========
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/test_{timestamp}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
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

def create_claude_prompt(test_case):
    """Claude Code에 전달할 프롬프트 (TC 고유 정보만 포함, 정적 내용은 system_prompt.txt로 분리)"""

    test_email = os.getenv('WANTED_TEST_EMAIL', '')
    test_password = os.getenv('WANTED_TEST_PASSWORD', '')
    test_no = test_case.get('NO', '')
    test_no_str = str(test_no).zfill(2)  # 01, 02 ... 10, 11 형식

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

    prompt = f"""## 테스트 케이스 정보
- 번호: {test_no}
- 환경: {test_case.get('환경', 'PC')}
- 기능영역: {test_case.get('기능영역', '')}
- 사전조건: {test_case.get('사전조건', '없음')}
- 확인사항: {test_case.get('확인사항', '')}
- 기대결과: {test_case.get('기대결과', '')}
{f'- {login_info}' if login_info else ''}
{f'- 세션: {session_instruction}' if session_instruction else ''}

## 작업
1. `test/test_{test_no_str}_working.py` 생성 후 코드 작성
2. `python test/test_{test_no_str}_working.py` 실행
3. 성공 시 `test/test_{test_no_str}_success.py`로 이름 변경, 실패 시 수정 후 재시도
4. 마지막에 반드시 `AUTOMATION_SUCCESS` 또는 `AUTOMATION_FAILED: 에러메시지` 출력

지금 바로 시작하세요!
"""

    return prompt

def load_system_prompt():
    """system_prompt.txt 로드"""
    with open('system_prompt.txt', 'r', encoding='utf-8') as f:
        return f.read()

def run_claude_code(prompt, test_no, max_attempts=3):
    """Claude Code 실행"""

    system_prompt = load_system_prompt()
    test_no_str = str(test_no).zfill(2)

    for attempt in range(1, max_attempts + 1):
        logging.info(f"🤖 Claude Code 실행 시도 {attempt}/{max_attempts}")

        try:
            # ⭐ 프롬프트 파일로 저장 (디버깅용)
            prompt_file = f'work/test_{test_no_str}_prompt.txt'
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)

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
                timeout=300,
                cwd=os.getcwd(),
                encoding='utf-8',
                errors='replace',
                shell=sys.platform == 'win32'
            )
            
            output = result.stdout
            error = result.stderr
            
            # 로그 저장
            log_file = f'work/test_{test_no_str}_attempt_{attempt}.log'
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== 실행 시간 ===\n{datetime.now()}\n\n")
                f.write(f"=== 종료 코드 ===\n{result.returncode}\n\n")
                f.write(f"=== 출력 ===\n{output}\n\n")
                f.write(f"=== 에러 ===\n{error}\n")

            logging.info(f"📄 로그: {log_file}")

            if result.returncode != 0:
                logging.warning(f"⚠️ 종료 코드: {result.returncode}")

            # 성공 확인
            success_file = f'test/test_{test_no_str}_success.py'
            working_file = f'test/test_{test_no_str}_working.py'
            screenshot = f'screenshots/test_{test_no_str}_success.png'

            # working 파일 확인 및 처리
            if os.path.exists(working_file):
                logging.info(f"📝 작업 파일 발견: {working_file}")
                try:
                    shutil.move(working_file, success_file)
                    logging.info(f"✅ 파일명 변경: {success_file}")
                except Exception as e:
                    logging.warning(f"⚠️ 파일명 변경 실패: {e}")

            if 'AUTOMATION_SUCCESS' in output or os.path.exists(success_file) or os.path.exists(screenshot):
                # 이전 시도에서 생성된 실패 스크린샷 삭제 (성공 스크린샷으로 대체)
                failed_screenshot = f'screenshots/test_{test_no_str}_failed.png'
                if os.path.exists(failed_screenshot):
                    os.remove(failed_screenshot)
                    logging.info(f"🗑️ 실패 스크린샷 삭제: {failed_screenshot}")
                logging.info(f"✅ 테스트 {test_no} 성공!")
                return True, output, None

            elif 'AUTOMATION_FAILED:' in output:
                error_msg = output.split('AUTOMATION_FAILED:')[1].split('\n')[0].strip()
                logging.warning(f"❌ 테스트 {test_no} 실패: {error_msg}")
                
                if attempt < max_attempts:
                    logging.info("🔄 재시도...")
                    time.sleep(5)
                else:
                    return False, output, error_msg
            
            else:
                logging.warning(f"⚠️ 결과 불명확")
                if attempt < max_attempts:
                    time.sleep(5)
                else:
                    return False, output, "결과 불명확"
                    
        except subprocess.TimeoutExpired:
            logging.warning(f"⏱️ 타임아웃 (5분)")
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
    parser.add_argument('--test-no', type=int, default=None, help='실행할 테스트 케이스 번호 (예: --test-no 4)')
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
    if args.test_no is not None:
        test_cases = [tc for tc in all_test_cases if tc.get('NO') == args.test_no]
        if not test_cases:
            logging.error(f"❌ NO:{args.test_no} 테스트 케이스를 찾을 수 없습니다!")
            return
        logging.info(f"🎯 NO:{args.test_no} 단일 테스트 실행")
    else:
        test_cases = all_test_cases
        logging.info(f"📋 총 {len(test_cases)}개 테스트")

    # TC #3 (로그인 세션 복원용) 미리 확보
    login_tc = next((tc for tc in all_test_cases if tc.get('NO') == 3), None)

    results = []

    for idx, test_case in enumerate(test_cases, 1):
        test_no = test_case.get('NO', idx)

        print(f"\n{'='*60}")
        print(f"📝 테스트 {idx}/{len(test_cases)}: TC #{test_no}")
        print("="*60)

        prompt = create_claude_prompt(test_case)
        success, output, error = run_claude_code(prompt, test_no, max_attempts=3)

        results.append({
            'test_no': test_no,
            'status': 'SUCCESS' if success else 'FAILED',
            'test_case': test_case,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })

        print(f"{'✅ 성공!' if success else '❌ 실패!'}")

        # TC #5(로그아웃) 완료 후 TC #3(로그인)으로 세션 복원
        if test_no == 5 and login_tc is not None:
            print(f"\n{'='*60}")
            print(f"🔄 TC #5 로그아웃 완료 → TC #3 재실행으로 세션 복원")
            print("="*60)
            time.sleep(2)
            login_prompt = create_claude_prompt(login_tc)
            login_success, _, login_error = run_claude_code(login_prompt, 3, max_attempts=3)
            print(f"{'✅ 세션 복원 성공!' if login_success else '❌ 세션 복원 실패: ' + str(login_error)}")

        if idx < len(test_cases):
            time.sleep(2)
    
    # ⭐ 결과 JSON 저장
    result_file = f'test_results/result_{timestamp}.json'
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'total': len(test_cases),
            'success': sum(1 for r in results if r['status'] == 'SUCCESS'),
            'failed': sum(1 for r in results if r['status'] == 'FAILED'),
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    # 최종 리포트
    print(f"\n{'='*60}")
    print("📊 최종 결과")
    print("="*60)
    
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    total = len(test_cases)
    
    print(f"\n총 {total}개")
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {total - success_count}개")
    print(f"\n📄 결과: {result_file}")

if __name__ == '__main__':
    main()