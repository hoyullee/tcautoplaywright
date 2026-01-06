import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path

# ========== 설정 ==========
LAAS_API_KEY = os.environ.get('LAAS_API_KEY')  # ⭐ 수정
PROJECT_CODE = os.environ.get('PROJECT_CODE')  # ⭐ 수정
PRESET_HASH = os.environ.get('PRESET_HASH')    # ⭐ 수정
LAAS_API_URL = 'https://api-laas.wanted.co.kr/api/preset/v2/chat/completions'

# 디렉토리 생성
Path('generated_codes').mkdir(exist_ok=True)
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

# ========== LaaS API 호출 ==========
def generate_playwright_code(test_case):
    """테스트 케이스를 Playwright 코드로 변환"""
    
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

**시작 코드**:
```python
await page.goto('{base_url}')
await page.wait_for_load_state('networkidle')
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
    
    try:
        response = requests.post(LAAS_API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 401:
            logging.error(f"❌ 인증 실패 (401)")
            return None
        
        response.raise_for_status()
        result = response.json()
        code = result['choices'][0]['message']['content']
        
        # 코드 블록 추출
        if '```python' in code:
            code = code.split('```python')[1].split('```')[0].strip()
        elif '```' in code:
            code = code.split('```')[1].split('```')[0].strip()
        
        logging.info(f"✅ 코드 생성 성공 ({len(code)}자)")
        logging.info(f"   사용된 기본 URL: {base_url}")
        
        return code
    
    except requests.exceptions.HTTPError as e:
        logging.error(f"❌ HTTP 에러: {e}")
        if 'response' in locals():
            logging.error(f"  - 응답: {response.text}")
        return None
    except Exception as e:
        logging.error(f"❌ 예외 발생: {type(e).__name__}: {e}")
        return None

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
        
        logging.info("🤖 LaaS API로 Playwright 코드 생성 중...")
        generated_code = generate_playwright_code(test_case)
        
        if not generated_code:
            results.append({
                'test_no': test_no,
                'status': 'FAILED',
                'reason': '코드 생성 실패',
                'test_case': test_case
            })
            continue
        
        # 코드 저장
        code_filename = f'generated_codes/test_{test_no}_success.spec.py'
        with open(code_filename, 'w', encoding='utf-8') as f:
            f.write(generated_code)
        
        results.append({
            'test_no': test_no,
            'status': 'SUCCESS',
            'code_file': code_filename,
            'test_case': test_case
        })
        
        logging.info(f"✅ 테스트 {test_no} 완료")
    
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