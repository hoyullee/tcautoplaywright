import os
import json
import logging
import requests
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ========== 설정 ==========
LAAS_API_KEY = os.environ.get('LAAS_API_KEY')
PROJECT_CODE = os.environ.get('PROJECT_CODE')
PRESET_HASH = os.environ.get('PRESET_HASH')
LAAS_API_URL = 'https://api-laas.wanted.co.kr/api/preset/v2/chat/completions'

# 디렉토리 생성
Path('test').mkdir(exist_ok=True)
Path('test_results').mkdir(exist_ok=True)
Path('screenshots').mkdir(exist_ok=True)
Path('logs').mkdir(exist_ok=True)

# 로깅 설정
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/test_{timestamp}.log'),
        logging.StreamHandler()
    ]
)

# ========== LaaS API 호출 (재시도 포함) ==========
def generate_playwright_code(test_case, max_retries=3):
    """테스트 케이스를 Playwright 코드로 변환 (재시도 포함)"""
    
    # 기능영역 기반 URL 결정
    function_area = test_case.get('기능영역', '')
    
    if '회원가입' in function_area or '로그인' in function_area:
        base_url = 'https://id.wanted.co.kr/login'
    else:
        base_url = 'https://www.wanted.co.kr/'
    
    prompt = f"""
🚨 중요: 반드시 {base_url} 를 사용하세요!

테스트 케이스를 Playwright Python 코드로 변환:

**테스트 정보**
- NO: {test_case.get('NO', '')}
- 환경: {test_case.get('환경', 'PC')}
- 기능영역: {test_case.get('기능영역', '')}
- 시작 URL: {base_url}

**사전조건**: {test_case.get('사전조건', '없음')}
**확인사항**: {test_case.get('확인사항', '')}
**기대결과**: {test_case.get('기대결과', '')}

**필수 요구사항**:
1. await page.goto('{base_url}') 로 시작 (다른 URL 절대 금지!)
2. async/await 사용
3. headless=True
4. 스크린샷 캡처 (screenshots/test_{test_case.get('NO', '')}_*.png)
5. 에러 처리 및 타임아웃 30초
6. 반드시 성공 시 return True, 실패 시 return False

**시작 코드**:
```python
from playwright.async_api import async_playwright
import asyncio

async def test_case():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 한국어 설정
        context = await browser.new_context(
            locale='ko-KR',           # 한국어
            timezone_id='Asia/Seoul'  # 한국 시간대
            )

        page = await browser.new_page()
        
        try:
            await page.goto('{base_url}')
            await page.wait_for_load_state('networkidle')
            
            # 테스트 로직...
            
            await page.screenshot(path='screenshots/test_{test_case.get('NO', '')}_success.png')
            print("✅ 테스트 성공")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {{e}}")
            await page.screenshot(path='screenshots/test_{test_case.get('NO', '')}_error.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_case())
    sys.exit(0 if result else 1)
```

코드만 출력하세요.
"""

    headers = {
        'apiKey': LAAS_API_KEY,
        'project': PROJECT_CODE,
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    payload = {
        'hash': PRESET_HASH,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ]
    }
    
    # 재시도 로직
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"🔄 API 호출 시도 {attempt}/{max_retries}")
            
            response = requests.post(LAAS_API_URL, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 401:
                logging.error(f"❌ 인증 실패 (401) - 재시도 불가")
                return None, "인증 실패"
            
            response.raise_for_status()
            result = response.json()
            code = result['choices'][0]['message']['content']
            
            # 코드 블록 추출
            if '```python' in code:
                code = code.split('```python')[1].split('```')[0].strip()
            elif '```' in code:
                code = code.split('```')[1].split('```')[0].strip()
            
            logging.info(f"✅ 코드 생성 성공 ({len(code)}자) - 시도 {attempt}회")
            logging.info(f"   사용된 기본 URL: {base_url}")
            
            return code, None
        
        except requests.exceptions.Timeout:
            error_msg = f"타임아웃 (60초 초과)"
            logging.warning(f"⏱️ {error_msg} - 시도 {attempt}/{max_retries}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logging.info(f"   {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                logging.error(f"❌ 최대 재시도 횟수 초과")
                return None, error_msg
                
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP 에러: {e}"
            logging.warning(f"❌ {error_msg} - 시도 {attempt}/{max_retries}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logging.info(f"   {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                logging.error(f"❌ 최대 재시도 횟수 초과")
                if 'response' in locals():
                    logging.error(f"  - 응답: {response.text[:500]}")
                return None, error_msg
                
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logging.warning(f"⚠️ {error_msg} - 시도 {attempt}/{max_retries}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logging.info(f"   {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                logging.error(f"❌ 최대 재시도 횟수 초과")
                return None, error_msg
    
    return None, "알 수 없는 오류"

# ========== Playwright 코드 실행 ==========
def run_playwright_code(code_file, test_no, max_retries=3):
    """생성된 Playwright 코드를 실행 (최대 3회 재시도)"""
    
    for attempt in range(1, max_retries + 1):
        logging.info(f"▶️ 테스트 {test_no} 실행 시도 {attempt}/{max_retries}")
        
        try:
            # Python 파일 실행
            result = subprocess.run(
                [sys.executable, code_file],
                capture_output=True,
                text=True,
                timeout=120,  # 2분 타임아웃
                cwd=os.getcwd()
            )
            
            # 성공 (exit code 0)
            if result.returncode == 0:
                logging.info(f"✅ 테스트 {test_no} 실행 성공!")
                if result.stdout:
                    logging.info(f"출력:\n{result.stdout}")
                return True, result.stdout, None
            
            # 실패
            error_msg = result.stderr or result.stdout
            logging.warning(f"❌ 테스트 {test_no} 실행 실패 (시도 {attempt}/{max_retries})")
            logging.warning(f"에러:\n{error_msg[:500]}")  # 처음 500자만
            
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logging.info(f"   {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                return False, result.stdout, error_msg
                
        except subprocess.TimeoutExpired:
            logging.warning(f"⏱️ 테스트 {test_no} 타임아웃 (시도 {attempt}/{max_retries})")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logging.info(f"   {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                return False, None, "타임아웃 (120초 초과)"
                
        except Exception as e:
            logging.warning(f"⚠️ 테스트 {test_no} 예외 발생 (시도 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logging.info(f"   {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                return False, None, str(e)
    
    return False, None, "최대 재시도 횟수 초과"

# ========== 메인 실행 로직 ==========
def main():
    logging.info("=" * 60)
    logging.info("🚀 Playwright 자동화 테스트 시작")
    logging.info("=" * 60)
    
    logging.info(f"🔐 환경변수 검증:")
    logging.info(f"  - LAAS_API_KEY: {'✅ 설정됨' if LAAS_API_KEY else '❌ 없음'}")
    logging.info(f"  - PROJECT_CODE: {'✅ 설정됨' if PROJECT_CODE else '❌ 없음'} (값: {PROJECT_CODE})")
    logging.info(f"  - PRESET_HASH: {'✅ 설정됨' if PRESET_HASH else '❌ 없음'}")
    
    if not LAAS_API_KEY:
        logging.error("❌ LAAS_API_KEY가 설정되지 않았습니다!")
        return
    
    if not PROJECT_CODE:
        logging.error("❌ PROJECT_CODE가 설정되지 않았습니다!")
        return
        
    if not PRESET_HASH:
        logging.error("❌ PRESET_HASH가 설정되지 않았습니다!")
        return
    
    # 테스트 케이스 가져오기
    test_cases_json = os.environ.get('TEST_CASES', '[]')
    
    try:
        test_cases = json.loads(test_cases_json)
        if test_cases is None:
            test_cases = []
    except json.JSONDecodeError as e:
        logging.error(f"❌ TEST_CASES JSON 파싱 실패: {e}")
        test_cases = []
    
    logging.info(f"📋 총 {len(test_cases)}개의 테스트 케이스")
    
    if len(test_cases) == 0:
        logging.warning("⚠️ 테스트 케이스가 없습니다!")
        result_file = f'test_results/result_{timestamp}.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'total': 0,
                'success': 0,
                'failed': 0,
                'results': []
            }, f, indent=2, ensure_ascii=False)
        return
    
    results = []
    
    for idx, test_case in enumerate(test_cases, 1):
        test_no = test_case.get('NO', idx)
        logging.info(f"\n{'='*60}")
        logging.info(f"📝 테스트 케이스 {test_no} 처리 중...")
        logging.info(f"{'='*60}")
        
        # 1. 코드 생성
        logging.info("🤖 LaaS API로 Playwright 코드 생성 중...")
        generated_code, gen_error = generate_playwright_code(test_case, max_retries=3)
        
        if not generated_code:
            logging.error(f"❌ 테스트 케이스 {test_no} 코드 생성 실패: {gen_error}")
            results.append({
                'test_no': test_no,
                'status': 'FAILED',
                'reason': f'코드 생성 실패: {gen_error}',
                'test_case': test_case,
                'phase': 'generation',
                'retries': 3
            })
            continue
        
        # 코드 저장 (임시)
        code_filename = f'test/test_{test_no}_temp.spec.py'
        try:
            with open(code_filename, 'w', encoding='utf-8') as f:
                f.write(generated_code)
        except Exception as e:
            logging.error(f"❌ 파일 저장 실패: {e}")
            results.append({
                'test_no': test_no,
                'status': 'FAILED',
                'reason': f'파일 저장 실패: {str(e)}',
                'test_case': test_case,
                'phase': 'save'
            })
            continue
        
        # 2. 코드 실행
        logging.info("▶️ 생성된 코드 실행 중...")
        success, stdout, exec_error = run_playwright_code(code_filename, test_no, max_retries=3)
        
        # 3. 결과에 따라 파일명 변경
        status = 'SUCCESS' if success else 'FAILED'
        final_filename = f'test/test_{test_no}_{status.lower()}.spec.py'
        
        try:
            if os.path.exists(final_filename):
                os.remove(final_filename)
            os.rename(code_filename, final_filename)
        except Exception as e:
            logging.warning(f"⚠️ 파일명 변경 실패: {e}")
            final_filename = code_filename
        
        # 4. 결과 저장
        result_data = {
            'test_no': test_no,
            'status': status,
            'code_file': final_filename,
            'test_case': test_case,
            'phase': 'execution'
        }
        
        if success:
            result_data['output'] = stdout
            logging.info(f"✅ 테스트 {test_no} 완료 - {final_filename}")
        else:
            result_data['error'] = exec_error
            result_data['output'] = stdout
            logging.error(f"❌ 테스트 {test_no} 실패 - {final_filename}")
            logging.error(f"   에러: {exec_error[:200] if exec_error else 'None'}")
        
        results.append(result_data)
    
    # 최종 결과 저장
    result_file = f'test_results/result_{timestamp}.json'
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'total': len(test_cases),
            'success': sum(1 for r in results if r['status'] == 'SUCCESS'),
            'failed': sum(1 for r in results if r['status'] == 'FAILED'),
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    logging.info(f"\n{'='*60}")
    logging.info("📊 최종 결과")
    logging.info(f"{'='*60}")
    logging.info(f"✅ 성공: {sum(1 for r in results if r['status'] == 'SUCCESS')}")
    logging.info(f"❌ 실패: {sum(1 for r in results if r['status'] == 'FAILED')}")
    logging.info(f"📄 결과 파일: {result_file}")

if __name__ == '__main__':
    main()