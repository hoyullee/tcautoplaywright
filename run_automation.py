#!/usr/bin/env python3
"""
Google Drive에서 TC 다운로드 후 자동화 실행
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def clean_directories():
    """기존 파일 삭제"""
    
    print("=" * 60)
    print("🧹 기존 파일 정리")
    print("=" * 60 + "\n")
    
    # 정리할 디렉토리 목록
    directories = ['logs', 'screenshots', 'test', 'work']
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        
        if dir_path.exists():
            # 디렉토리 내 파일 개수 확인
            files = list(dir_path.glob('*'))
            file_count = len(files)
            
            if file_count > 0:
                print(f"📂 {dir_name}/ - {file_count}개 파일 삭제 중...")
                
                # 모든 파일 삭제
                for file in files:
                    try:
                        if file.is_file():
                            file.unlink()
                        elif file.is_dir():
                            shutil.rmtree(file)
                    except Exception as e:
                        print(f"   ⚠️ 삭제 실패: {file.name} - {e}")
                
                print(f"   ✅ 완료")
            else:
                print(f"📂 {dir_name}/ - 파일 없음 (스킵)")
        else:
            print(f"📂 {dir_name}/ - 폴더 없음 (생성됨)")
            dir_path.mkdir(exist_ok=True)
    
    print()

def main():
    print("=" * 60)
    print("🚀 완전 자동화 실행")
    print("=" * 60 + "\n")
    
    # ⭐ 기존 파일 삭제
    clean_directories()
    
    # 환경변수 확인
    token = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN')
    if not token:
        print("❌ CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다!")
        print("\n해결 방법:")
        print("1. export CLAUDE_CODE_OAUTH_TOKEN='your-token'")
        print("2. 또는 ~/.zshrc에 추가")
        sys.exit(1)
    
    print(f"✅ Claude 토큰 확인 완료 (길이: {len(token)}자)\n")
    
    # 1. test_cases.json 다운로드
    print("=" * 60)
    print("📥 1단계: Google Drive에서 TC 다운로드")
    print("=" * 60 + "\n")
    
    env = os.environ.copy()
    
    result = subprocess.run(
        [sys.executable, 'download_tc.py'],
        env=env
    )
    
    if result.returncode != 0:
        print("\n❌ 다운로드 실패!")
        sys.exit(1)
    
    print()
    
    # 2. Claude 자동화 실행
    print("=" * 60)
    print("🤖 2단계: Claude Code 자동화 실행")
    print("=" * 60 + "\n")
    
    result = subprocess.run(
        [sys.executable, 'claude_automation.py'],
        env=env
    )
    
    if result.returncode != 0:
        print("\n❌ 자동화 실패!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 모든 작업 완료!")
    print("=" * 60)
    
    # 생성된 파일 요약
    print("\n📊 생성된 파일:")
    
    summary = {
        'test': list(Path('test').glob('*.py')),
        'screenshots': list(Path('screenshots').glob('*.png')),
        'test_results': list(Path('test_results').glob('*.json')),
        'logs': list(Path('logs').glob('*.log'))
    }
    
    for folder, files in summary.items():
        if files:
            print(f"   📂 {folder}/: {len(files)}개")
        else:
            print(f"   📂 {folder}/: 0개")

if __name__ == '__main__':
    main()