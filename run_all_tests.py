import subprocess
import sys
import glob
import re
from pathlib import Path

def main():
    test_files = sorted(
        glob.glob('test/test_*_success.py'),
        key=lambda f: int(re.search(r'test_(\d+)_success', f).group(1))
    )

    if not test_files:
        print("❌ 실행할 테스트 파일이 없습니다.")
        sys.exit(1)

    total = len(test_files)
    success_list = []
    failed_list = []

    print(f"\n{'='*60}")
    print(f"🚀 총 {total}개 테스트 실행")
    print(f"{'='*60}\n")

    for idx, test_file in enumerate(test_files, 1):
        name = Path(test_file).name
        no = re.search(r'test_(\d+)_success', name).group(1)

        print(f"\n{'='*60}")
        print(f"[{idx}/{total}] TC #{int(no):02d} — {name}")
        print(f"{'='*60}")

        result = subprocess.run(
            [sys.executable, test_file],
            cwd='.'
        )

        if result.returncode == 0:
            success_list.append(no)
            print(f"✅ TC #{int(no):02d} 성공")
        else:
            failed_list.append(no)
            print(f"❌ TC #{int(no):02d} 실패")

        # TC #05(로그아웃) 완료 후 TC #03(로그인)으로 세션 복원
        if int(no) == 5 and Path('test/test_03_success.py').exists():
            print(f"\n{'='*60}")
            print(f"🔄 TC #05 로그아웃 완료 → TC #03 재실행으로 세션 복원")
            print(f"{'='*60}")
            restore = subprocess.run([sys.executable, 'test/test_03_success.py'], cwd='.')
            if restore.returncode == 0:
                print("✅ 세션 복원 성공")
            else:
                print("⚠️ 세션 복원 실패 — 이후 로그인 필요 케이스가 실패할 수 있습니다")

    print(f"\n{'='*60}")
    print(f"📊 최종 결과")
    print(f"{'='*60}")
    print(f"✅ 성공: {len(success_list)}개  /  ❌ 실패: {len(failed_list)}개  /  전체: {total}개")

    if failed_list:
        print(f"\n❌ 실패한 케이스:")
        for no in failed_list:
            print(f"   - TC #{int(no):02d}  (test_{no}_success.py)")

    print()

if __name__ == '__main__':
    main()
