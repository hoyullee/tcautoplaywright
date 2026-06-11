import subprocess
import sys
import glob
import re
from pathlib import Path

LOGS_DIR = Path('logs')


def run_test(test_file):
    return subprocess.run(
        [sys.executable, test_file],
        cwd='.',
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )


def extract_failure_reason(stdout, stderr):
    # AUTOMATION_FAILED: <message> 우선 탐색
    for line in stdout.splitlines():
        if 'AUTOMATION_FAILED:' in line:
            return line.split('AUTOMATION_FAILED:', 1)[1].strip()
    # AssertionError 탐색
    for line in reversed(stderr.splitlines()):
        line = line.strip()
        if line.startswith('AssertionError') or line.startswith('assert '):
            return line
    # stderr 마지막 줄 fallback
    for line in reversed(stderr.splitlines()):
        if line.strip():
            return line.strip()
    return '알 수 없음'


def save_failure_log(no, stdout, stderr):
    LOGS_DIR.mkdir(exist_ok=True)
    reason = extract_failure_reason(stdout, stderr)
    log_path = LOGS_DIR / f'failed_TC_{int(no):02d}.log'
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"실패 사유: {reason}\n")
        f.write('=' * 60 + '\n\n')
        if stdout:
            f.write('--- stdout ---\n')
            f.write(stdout)
            f.write('\n')
        if stderr:
            f.write('--- stderr ---\n')
            f.write(stderr)
    return log_path, reason


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

        print(f"[{idx}/{total}] TC #{int(no):02d} ...", end=' ', flush=True)

        result = run_test(test_file)

        if result.returncode == 0:
            success_list.append(no)
            print(f"✅ 성공")
        else:
            log_path, reason = save_failure_log(no, result.stdout, result.stderr)
            failed_list.append((no, reason, log_path))
            print(f"❌ 실패  →  {reason}")
            print(f"         📄 {log_path}")

        # TC #05(로그아웃) 완료 후 TC #03(로그인)으로 세션 복원
        if int(no) == 5 and Path('test/test_03_success.py').exists():
            print(f"🔄 TC #05 로그아웃 완료 → TC #03 재실행으로 세션 복원 ...", end=' ', flush=True)
            restore = run_test('test/test_03_success.py')
            if restore.returncode == 0:
                print("✅ 세션 복원 성공")
            else:
                _, reason = save_failure_log('03_restore', restore.stdout, restore.stderr)
                print(f"⚠️ 세션 복원 실패 — {reason}")

    print(f"\n{'='*60}")
    print(f"📊 최종 결과")
    print(f"{'='*60}")
    print(f"✅ 성공: {len(success_list)}개  /  ❌ 실패: {len(failed_list)}개  /  전체: {total}개")

    if failed_list:
        print(f"\n❌ 실패한 케이스:")
        for no, reason, log_path in failed_list:
            print(f"   TC #{int(no):02d}  →  {reason}")
            print(f"           {log_path}")

    print()


if __name__ == '__main__':
    main()
