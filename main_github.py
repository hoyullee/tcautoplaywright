import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
import subprocess
import sys

# ========== 설정 ==========
LAAS_API_KEY = os.environ.get('128fdaef23493311666005a94cccb7e75f1b6a127f8c0330577eac89e7dd2767')
LAAS_API_URL = 'https://api-laas.wanted.co.kr/api/preset/v2/chat/completions'
PROJECT_CODE = os.environ.get('0fcabc0b9e')
PRESET_HASH = os.environ.get('888aa18dddcd5d6db56e96a39f13813d74d0962e8a5251a4f8e7a3468a7e825f')

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
        logging.StreamHandler(sys.stdout)
    ]
)

# ========== LaaS API 호출 (코드 생성) ==========
def generate_playwright_code(test_case):
    """테스트 케이스를 Playwright 코드로 변환"""
    
    prompt = f"""
다음 테스트 케이스를 Playwright Python 코드로 변환해주세요:

환경: {test_case.get('환경', 'PC')}
기능영역: {test_case.get('기능영역', '')}
테스트 단계: {test_case.get('단계', '')}
기대결과: {test_case.get('기대결과', '')}

요구사항:
1. async/await 사용
2. headless=True로 설정
3. 스크린샷 캡처 포함
4. 명확한 에러 처리
"""

    headers = {
        'apiKey': LAAS_API_KEY,           # Authorization → apiKey로 변경
        'project': PROJECT_CODE,           # 프로젝트 코드 추가 필요
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    payload = {
        'hash': PRESET_HASH,  # 프리셋 해시 값 필요
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ]
    }
    
    try:
        response = requests.post(LAAS_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        # 응답 형식이 다를 수 있으므로 확인 필요
        code = result['choices'][0]['message']['content']
        
        # 코드 블록 추출
        if '```python' in code:
            code = code.split('```python')[1].split('```')[0].strip()
        elif '```' in code:
            code = code.split('```')[1].split('```')[0].strip()
        
        return code
    
    except Exception as e:
        logging.error(f"코드 생성 실패: {e}")
        return None

# ========== Playwright 코드 실행 ==========
def run_playwright_code(code, test_no, max_retries=3):
    """생성된 Playwright 코드를 실행"""
    
    for attempt in range(1, max_retries + 1):
        logging.info(f"🔄 테스트 {test_no} 실행 시도 {attempt}/{max_retries}")
        
        # 임시 파일로 저장
        temp_file = f'temp_test_{test_no}.py'
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        try:
            # 실행
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=120  # 2분 타임아웃
            )
            
            # 성공
            if result.returncode == 0:
                logging.info(f"✅ 테스트 {test_no} 성공!")
                os.remove(temp_file)
                return True, result.stdout
            
            # 실패
            logging.warning(f"❌ 테스트 {test_no} 실패 (시도 {attempt}): {result.stderr}")
            
        except subprocess.TimeoutExpired:
            logging.warning(f"⏱️ 테스트 {test_no} 타임아웃 (시도 {attempt})")
        except Exception as e:
            logging.warning(f"⚠️ 테스트 {test_no} 예외 발생 (시도 {attempt}): {e}")
        
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    return False, "최대 재시도 횟수 초과"

# ========== 메인 실행 로직 ==========
def main():
    logging.info("=" * 60)
    logging.info("🚀 Playwright 자동화 테스트 시작")
    logging.info("=" * 60)
    
    # 환경변수에서 테스트 케이스 가져오기
    test_cases_json = os.environ.get('TEST_CASES', '[]')
    test_cases = json.loads(test_cases_json)
    
    logging.info(f"📋 총 {len(test_cases)}개의 테스트 케이스")
    
    results = []
    
    for idx, test_case in enumerate(test_cases, 1):
        test_no = test_case.get('NO', idx)
        logging.info(f"\n{'='*60}")
        logging.info(f"📝 테스트 케이스 {test_no} 처리 중...")
        logging.info(f"{'='*60}")
        
        # 1. 코드 생성
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
        
        # 2. 코드 실행
        success, output = run_playwright_code(generated_code, test_no)
        
        # 3. 결과 저장
        status = 'SUCCESS' if success else 'FAILED'
        code_filename = f'generated_codes/test_{test_no}_{status.lower()}.py'
        
        with open(code_filename, 'w', encoding='utf-8') as f:
            f.write(generated_code)
        
        results.append({
            'test_no': test_no,
            'status': status,
            'output': output,
            'code_file': code_filename,
            'test_case': test_case
        })
        
        logging.info(f"{'✅ 성공' if success else '❌ 실패'}: 테스트 {test_no}")
    
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