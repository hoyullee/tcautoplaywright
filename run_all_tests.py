import json
import subprocess
import sys
import glob
from pathlib import Path

LOGS_DIR = Path('logs')
TC_JSON = Path('test_cases.json')


def load_tc_order():
    """test_cases.json → {파일경로: (NO, tc_id)} 매핑 (NO 순 정렬용)"""
    if not TC_JSON.exists():
        return {}
    with open(TC_JSON, encoding='utf-8') as f:
        cases = json.load(f)
    mapping = {}
    for tc in cases:
        tc_id = tc.get('TestCaseID', '')
        if '-' in tc_id:
            prefix, num = tc_id.rsplit('-', 1)
            stem = f'test_{prefix}_{num}'
            fp = str(Path('test') / prefix / f'{stem}_success.py')
            mapping[fp] = (tc['NO'], tc_id)
    return mapping


def find_test_file(tc_id):
    """TestCaseID로 파일 경로 반환 (없으면 None)"""
    if '-' not in tc_id:
        return None
    prefix, num = tc_id.rsplit('-', 1)
    p = Path('test') / prefix / f'test_{prefix}_{num}_success.py'
    return str(p) if p.exists() else None


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
    for line in stdout.splitlines():
        if 'AUTOMATION_FAILED:' in line:
            return line.split('AUTOMATION_FAILED:', 1)[1].strip()
    for line in reversed(stderr.splitlines()):
        line = line.strip()
        if line.startswith('AssertionError') or line.startswith('assert '):
            return line
    for line in reversed(stderr.splitlines()):
        if line.strip():
            return line.strip()
    return '알 수 없음'


def save_failure_log(tc_id, stdout, stderr):
    LOGS_DIR.mkdir(exist_ok=True)
    reason = extract_failure_reason(stdout, stderr)
    safe_id = tc_id.replace('-', '_')
    log_path = LOGS_DIR / f'failed_{safe_id}.log'
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


def clear_logs():
    if LOGS_DIR.exists():
        for f in LOGS_DIR.glob('*.log'):
            f.unlink()


def main():
    clear_logs()
    tc_order = load_tc_order()  # {filepath: (NO, tc_id)}

    all_files = glob.glob('test/*/test_*_success.py')
    test_files = sorted(
        all_files,
        key=lambda f: tc_order.get(str(Path(f)), (9999, ''))[0]
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
        fp_key = str(Path(test_file))
        _, tc_id = tc_order.get(fp_key, (0, Path(test_file).stem))

        print(f"[{idx}/{total}] {tc_id} ...", end=' ', flush=True)

        result = run_test(test_file)

        if result.returncode == 0:
            success_list.append(tc_id)
            print("✅ 성공")
        else:
            log_path, reason = save_failure_log(tc_id, result.stdout, result.stderr)
            failed_list.append((tc_id, reason, log_path))
            print(f"❌ 실패  →  {reason}")
            print(f"         📄 {log_path}")

        # LOGIN-005(로그아웃) 완료 후 LOGIN-003(로그인)으로 세션 복원
        if tc_id == 'LOGIN-005':
            restore_file = find_test_file('LOGIN-003')
            if restore_file:
                print(f"🔄 LOGIN-005 완료 → LOGIN-003 재실행으로 세션 복원 ...", end=' ', flush=True)
                restore = run_test(restore_file)
                if restore.returncode == 0:
                    print("✅ 세션 복원 성공")
                else:
                    _, reason = save_failure_log('LOGIN-003_restore', restore.stdout, restore.stderr)
                    print(f"⚠️ 세션 복원 실패 — {reason}")

    print(f"\n{'='*60}")
    print("📊 최종 결과")
    print(f"{'='*60}")
    print(f"✅ 성공: {len(success_list)}개  /  ❌ 실패: {len(failed_list)}개  /  전체: {total}개")

    if failed_list:
        print(f"\n❌ 실패한 케이스:")
        for tc_id, reason, log_path in failed_list:
            print(f"   {tc_id}  →  {reason}")
            print(f"           {log_path}")

    print()


if __name__ == '__main__':
    main()
