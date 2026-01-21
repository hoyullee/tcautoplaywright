import requests
import os
import sys

# ========== 설정 ==========
GOOGLE_DRIVE_FILE_ID = '1d3dpFEzBegqCBlIno1zJ8VEwsKP6J0rX'  # 나중에 설정
OUTPUT_FILE = 'test_cases.json'

def download_from_google_drive(file_id, output_path):
    """Google Drive에서 파일 다운로드"""
    
    print(f"Google Drive에서 다운로드 중...")
    print(f" - 파일 ID: {file_id}")
    
    # Google Drive 다운로드 URL
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # 파일 저장
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f" - 다운로드 완료: {output_path}")
            print(f"   파일 크기: {len(response.content)} bytes")
            
            # JSON 유효성 검사
            import json
            with open(output_path, 'r', encoding='utf-8') as f:
                test_cases = json.load(f)
                print(f"   테스트 케이스: {len(test_cases)}개")
            
            return True
            
        else:
            print(f"❌ 다운로드 실패: HTTP {response.status_code}")
            print(f"   응답: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def main():
    print("=" * 60)
    print(" - Google Drive에서 test_cases.json 다운로드")
    print("=" * 60 + "\n")
    
    # 파일 ID 확인
    if GOOGLE_DRIVE_FILE_ID == 'YOUR_FILE_ID_HERE':
        print("❌ GOOGLE_DRIVE_FILE_ID를 설정하세요!")
        print("\n방법:")
        print("1. 구글 시트에서 H1 체크박스 클릭")
        print("2. J1 셀에 생성된 파일 ID 복사")
        print("3. download_tc.py에서 GOOGLE_DRIVE_FILE_ID 설정")
        sys.exit(1)
    
    # 다운로드
    success = download_from_google_drive(GOOGLE_DRIVE_FILE_ID, OUTPUT_FILE)
    
    if success:
        print("\n - 성공!")
    else:
        print("\n❌ 실패!")
        sys.exit(1)

if __name__ == '__main__':
    main()
