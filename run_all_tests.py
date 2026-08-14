import json
import subprocess
import sys
import glob
from pathlib import Path

LOGS_DIR = Path('logs')
TC_JSON = Path('test_cases.json')
MAX_RETRIES = 3


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


def run_test_with_retry(test_file, tc_id):
    """최대 MAX_RETRIES 회 재시도. (result, attempts) 반환"""
    last_result = None
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            print(f"  ↳ 재시도 {attempt - 1}/{MAX_RETRIES - 1} ...", end=' ', flush=True)
        last_result = run_test(test_file)
        if last_result.returncode == 0:
            return last_result, attempt
        if attempt < MAX_RETRIES:
            reason = extract_failure_reason(last_result.stdout, last_result.stderr)
            print(f"❌ ({reason[:50]})")
    return last_result, MAX_RETRIES


def regenerate_tc(tc_id):
    """claude_automation.py --tc {tc_id} 실행 후 success 파일 존재 여부 반환"""
    subprocess.run(
        [sys.executable, 'claude_automation.py', '--tc', tc_id],
        cwd='.',
        encoding='utf-8',
        errors='replace',
        timeout=600,
    )
    return find_test_file(tc_id) is not None


def git_commit_and_push(regenerated_tc_ids):
    """재생성된 테스트 스크립트를 master 브랜치에 자동 커밋·푸시"""
    print(f"\n{'='*60}")
    print("📦 Git 자동 커밋·푸시")
    print(f"{'='*60}")

    # 변경된 test/ 파일이 실제로 있는지 확인
    diff = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD', '--', 'test/'],
        capture_output=True, text=True, cwd='.'
    )
    untracked = subprocess.run(
        ['git', 'ls-files', '--others', '--exclude-standard', 'test/'],
        capture_output=True, text=True, cwd='.'
    )
    changed_files = (diff.stdout + untracked.stdout).strip()

    if not changed_files:
        print("ℹ️  test/ 디렉토리에 변경된 파일 없음 — 커밋 스킵")
        return

    print(f"변경 파일:\n{changed_files}\n")

    tc_label = ', '.join(regenerated_tc_ids)
    commit_msg = f"auto: regenerate test cases ({tc_label})"

    steps = [
        (['git', 'add', 'test/'], "git add test/"),
        (['git', 'commit', '-m', commit_msg], f"git commit"),
        (['git', 'push', 'origin', 'master'], "git push origin master"),
    ]

    for cmd, label in steps:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            print(f"✅ {label}")
        else:
            print(f"❌ {label} 실패:\n{result.stderr.strip()}")
            break


def main():
    clear_logs()
    tc_order = load_tc_order()

    all_files = glob.glob('test/*/test_*_success.py')
    test_files = sorted(
        all_files,
        key=lambda f: tc_order.get(str(Path(f)), (9999, ''))[0]
    )

    if not test_files:
        print("❌ 실행할 테스트 파일이 없습니다.")
        sys.exit(1)

    total = len(test_files)
    success_list = []      # (tc_id, note)
    failed_list = []       # (tc_id, reason, log_path)
    regenerated_ids = []   # 재생성이 시도된 tc_id 목록

    print(f"\n{'='*60}")
    print(f"🚀 총 {total}개 테스트 실행")
    print(f"{'='*60}\n")

    for idx, test_file in enumerate(test_files, 1):
        fp_key = str(Path(test_file))
        _, tc_id = tc_order.get(fp_key, (0, Path(test_file).stem))

        print(f"[{idx}/{total}] {tc_id} ...", end=' ', flush=True)

        result, attempts = run_test_with_retry(test_file, tc_id)

        if result.returncode == 0:
            note = f" (재시도 {attempts - 1}회)" if attempts > 1 else ""
            print(f"✅ 성공{note}")
            success_list.append((tc_id, note.strip()))
        else:
            # 3회 모두 실패 → 재생성 시도
            reason = extract_failure_reason(result.stdout, result.stderr)
            print(f"❌ 실패 → {reason[:60]}")
            print(f"         🔄 재생성 시도 중...", end=' ', flush=True)
            regenerated_ids.append(tc_id)

            try:
                regen_ok = regenerate_tc(tc_id)
            except subprocess.TimeoutExpired:
                regen_ok = False

            if regen_ok:
                new_file = find_test_file(tc_id)
                print(f"재생성 완료 → 재실행 중...", end=' ', flush=True)
                rerun = run_test(new_file)
                if rerun.returncode == 0:
                    print(f"✅ 재생성 후 성공")
                    success_list.append((tc_id, '재생성 후 성공'))
                else:
                    log_path, rerun_reason = save_failure_log(tc_id, rerun.stdout, rerun.stderr)
                    print(f"❌ 재생성 후에도 실패 → {rerun_reason[:50]}")
                    print(f"         📄 {log_path}")
                    failed_list.append((tc_id, f"[재생성 후 실패] {rerun_reason}", log_path))
            else:
                log_path, _ = save_failure_log(tc_id, result.stdout, result.stderr)
                print(f"❌ 재생성 실패")
                print(f"         📄 {log_path}")
                failed_list.append((tc_id, f"[재생성 실패] {reason}", log_path))

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
        print(f"\n❌ 최종 실패한 케이스:")
        for tc_id, reason, log_path in failed_list:
            print(f"   {tc_id}  →  {reason}")
            print(f"           {log_path}")

    # 재생성이 1회라도 있었고, 최종 실패 케이스가 없을 때만 커밋·푸시
    if regenerated_ids and not failed_list:
        git_commit_and_push(regenerated_ids)
    elif regenerated_ids and failed_list:
        print("\nℹ️  실패한 케이스가 있어 Git 커밋·푸시를 건너뜁니다.")

    print()


if __name__ == '__main__':
    main()
