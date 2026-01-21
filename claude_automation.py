import json
import subprocess
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

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

def create_claude_prompt(test_case):
    """Claude Code에 전달할 프롬프트"""

    # ⭐ 변수 선언 한 번만 (중복 제거)
    test_email = os.getenv('WANTED_TEST_EMAIL', '')
    test_password = os.getenv('WANTED_TEST_PASSWORD', '')
    test_no = test_case.get('NO', '')
    function_area = test_case.get('기능영역', '')
    
    # URL 결정
    if '회원가입' in function_area or '로그인' in function_area:
        base_url = 'https://www.wanted.co.kr/'
    else:
        base_url = 'https://www.wanted.co.kr/'
    
    # 로그인 관련 테스트인지 확인
    is_login_test = '로그인' in function_area or '로그인' in test_case.get('확인사항', '')
    
    # 로그인 정보 섹션
    login_info_section = ""
    if is_login_test and test_email and test_password:
        login_info_section = f"""
## 🔐 테스트 계정 정보
⚠️ **중요**: 다음 테스트 계정을 사용하세요
- 이메일: {test_email}
- 비밀번호: {test_password}

로그인이 필요한 경우 위 정보를 사용하세요.
"""

    prompt = f"""
당신은 Playwright 테스트 자동화 전문가입니다.

## 테스트 정보
- 테스트 번호: {test_no}
- URL: {base_url}
- 환경: {test_case.get('환경', 'PC')}
- 기능영역: {function_area}
- 사전조건: {test_case.get('사전조건', '없음')}
- 확인사항: {test_case.get('확인사항', '')}
- 기대결과: {test_case.get('기대결과', '')}

{login_info_section}

---

## 작업 지시

### 1단계: 파일 생성
test/test_{test_no}_working.py 파일을 생성하세요.

### 2단계: 코드 작성

⚠️ **중요**: Playwright는 **비동기(async/await)** 라이브러리입니다!

다음 구조로 **완전히 작동하는** Playwright Python 코드를 작성하세요:
```python
from playwright.async_api import async_playwright
import asyncio
import sys
import os

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "{test_email}"
TEST_PASSWORD = "{test_password}"

async def main():
    async with async_playwright() as p:
        # 브라우저 실행
        browser = await p.chromium.launch(headless=True)
        
        # 한국어 설정
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()
        
        try:
            # screenshots 폴더 생성
            os.makedirs('screenshots', exist_ok=True)
            
            # 페이지 접속
            print("🌐 페이지 접속: {base_url}")
            await page.goto('{base_url}', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")
            
            # ========================================
            # 여기에 테스트 로직 작성
            # ========================================
            # 확인사항: {test_case.get('확인사항', '')}
            #
            # ⚠️ 중요: 모든 Playwright 메서드에 await 사용!
            #
            # 로케이터 우선순위:
            # 1. await page.get_by_role('button', name='정확한텍스트').click()
            # 2. await page.get_by_text('정확한텍스트').click()
            # 3. await page.locator('css-selector').click()
            #
            # 로그인 필요 시 예시:
            # email_input = page.get_by_label('이메일') 또는 page.locator('input[type="email"]')
            # await email_input.fill(TEST_EMAIL)
            # 
            # password_input = page.get_by_label('비밀번호') 또는 page.locator('input[type="password"]')
            # await password_input.fill(TEST_PASSWORD)
            # 
            # login_button = page.get_by_role('button', name='로그인')
            # await login_button.click()
            # await page.wait_for_load_state('networkidle')
            
            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_{test_no}_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {{e}}")
            print(f"AUTOMATION_FAILED: {{e}}")  # ⭐ 실패 시그널
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
```

### 3단계: 필수 체크리스트

✅ **async/await 체크리스트** (반드시 확인!):
- [ ] `async def main():`로 시작
- [ ] `async with async_playwright() as p:`
- [ ] `await p.chromium.launch()`
- [ ] `await browser.new_context()`
- [ ] `await context.new_page()`
- [ ] `await page.goto()`
- [ ] `await page.wait_for_load_state()`
- [ ] `await page.click()` 또는 `await element.click()`
- [ ] `await page.fill()`
- [ ] `await page.screenshot()`
- [ ] `await browser.close()`
- [ ] `asyncio.run(main())`로 실행

### 4단계: 코드 실행
작성한 코드를 실행하세요: python test/test_{test_no}_working.py

### 5단계: 결과 처리
- 성공하면 test/test_{test_no}_success.spec.py로 이름 변경
- 실패하면 에러 분석 후 코드 수정하고 재시도

### 6단계: 최종 출력
반드시 다음 중 하나를 출력하세요:
- AUTOMATION_SUCCESS
- AUTOMATION_FAILED: 에러메시지

⚠️ **다시 한번 강조**: Playwright의 모든 메서드는 **비동기**입니다!
await를 빠뜨리면 코드가 작동하지 않습니다!

지금 바로 시작하세요!
"""
    
    return prompt

def run_claude_code(prompt, test_no, max_attempts=3):
    """Claude Code 실행"""
    
    for attempt in range(1, max_attempts + 1):
        logging.info(f"🤖 Claude Code 실행 시도 {attempt}/{max_attempts}")
        
        try:
            # ⭐ 프롬프트 파일로 저장 (디버깅용)
            prompt_file = f'work/test_{test_no}_prompt.txt'
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            result = subprocess.run(
                [
                    'claude',
                    '--print',
                    '--model', 'sonnet',
                    '--dangerously-skip-permissions',
                    prompt
                ],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=os.getcwd(),
                encoding='utf-8',
                errors='replace'
            )
            
            output = result.stdout
            error = result.stderr
            
            # 로그 저장
            log_file = f'work/test_{test_no}_attempt_{attempt}.log'
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== 실행 시간 ===\n{datetime.now()}\n\n")
                f.write(f"=== 종료 코드 ===\n{result.returncode}\n\n")
                f.write(f"=== 출력 ===\n{output}\n\n")
                f.write(f"=== 에러 ===\n{error}\n")
            
            logging.info(f"📄 로그: {log_file}")
            
            if result.returncode != 0:
                logging.warning(f"⚠️ 종료 코드: {result.returncode}")
            
            # 성공 확인
            success_file = f'test/test_{test_no}_success.spec.py'
            working_file = f'test/test_{test_no}_working.py'  # ⭐ 추가
            screenshot = f'screenshots/test_{test_no}_success.png'
            
            # ⭐ working 파일 확인 및 처리
            if os.path.exists(working_file):
                logging.info(f"📝 작업 파일 발견: {working_file}")
                # 성공 파일로 이름 변경
                try:
                    os.rename(working_file, success_file)
                    logging.info(f"✅ 파일명 변경: {success_file}")
                except Exception as e:
                    logging.warning(f"⚠️ 파일명 변경 실패: {e}")
            
            if 'AUTOMATION_SUCCESS' in output or os.path.exists(success_file) or os.path.exists(screenshot):
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
    
    print("\n" + "=" * 60)
    print("🚀 Claude Code Playwright 자동화")
    print("=" * 60 + "\n")
    
    # test_cases.json 확인
    if not os.path.exists('test_cases.json'):
        logging.error("❌ test_cases.json 파일이 없습니다!")
        return
    
    # 테스트 케이스 로드
    with open('test_cases.json', 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
    
    logging.info(f"📋 총 {len(test_cases)}개 테스트")
    
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