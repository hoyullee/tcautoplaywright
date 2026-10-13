import argparse
import hashlib
import json
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import glob
import time
from datetime import datetime
from pathlib import Path

from run_report import CaseRecord, build_report, summarize_failure, write_report
from run_perf import build_perf_report, scan_fixed_waits, write_perf_report
from ui_helpers import DISMISS_MARKER, POPUP_NAMES

LOGS_DIR = Path('logs')
TC_JSON = Path('test_cases.json')
MAX_RETRIES = 3

# 병렬 실행 워커 수.
# 브라우저 하나가 1.4~1.7GB 를 쓰므로 메모리가 상한이다. 4가 실측 기준 균형점.
DEFAULT_WORKERS = 4


def load_tc_meta():
    """test_cases.json → (파일경로 매핑, tc_id 메타 매핑)

    - order_map : {파일경로: (NO, tc_id)}   NO 순 정렬용
    - meta_map  : {tc_id: {'no', '기능영역', '기대결과'}}
    """
    if not TC_JSON.exists():
        return {}, {}
    with open(TC_JSON, encoding='utf-8') as f:
        cases = json.load(f)
    order_map, meta_map = {}, {}
    for tc in cases:
        tc_id = tc.get('TestCaseID', '')
        if '-' not in tc_id:
            continue
        prefix, num = tc_id.rsplit('-', 1)
        fp = str(Path('test') / prefix / f'test_{prefix}_{num}_success.py')
        order_map[fp] = (tc['NO'], tc_id)
        meta_map[tc_id] = {
            'no': tc['NO'],
            'feature': tc.get('기능영역', ''),
            'expected': tc.get('기대결과', ''),
        }
    return order_map, meta_map


def find_test_file(tc_id):
    """TestCaseID로 파일 경로 반환 (없으면 None)"""
    if '-' not in tc_id:
        return None
    prefix, num = tc_id.rsplit('-', 1)
    p = Path('test') / prefix / f'test_{prefix}_{num}_success.py'
    return str(p) if p.exists() else None


# 팝업 정리 헬퍼가 실제로 발동한 횟수 (이름 → 횟수)
POPUP_HITS = {}
_HITS_LOCK = threading.Lock()
_PRINT_LOCK = threading.Lock()


def emit(lines):
    """여러 줄을 한 덩어리로 출력한다. 병렬 실행에서 줄이 섞이지 않게 한다."""
    with _PRINT_LOCK:
        for line in lines:
            print(line)
        sys.stdout.flush()


def run_test(test_file):
    result = _run_test(test_file)
    with _HITS_LOCK:
        count_popup_hits(result.stdout, POPUP_HITS)
    return result


def _run_test(test_file):
    return subprocess.run(
        [sys.executable, test_file],
        cwd='.',
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )


def extract_failure_block(stdout, stderr):
    """실패 지점의 첫 줄(head)과 그 뒤 로그 블록(block)을 뽑아낸다.

    playwright 예외는 여러 줄이므로 뒤따르는 call log까지 함께 넘겨
    '무엇을 기다리다 실패했는지'까지 요약할 수 있게 한다.
    """
    lines = (stdout or '').splitlines()
    for i, line in enumerate(lines):
        if 'AUTOMATION_FAILED:' in line:
            head = line.split('AUTOMATION_FAILED:', 1)[1].strip()
            return head, '\n'.join(lines[i:i + 20])

    err_lines = (stderr or '').splitlines()
    for i in range(len(err_lines) - 1, -1, -1):
        s = err_lines[i].strip()
        if s.startswith('AssertionError') or s.startswith('assert '):
            return s, '\n'.join(err_lines[i:i + 20])
    for i in range(len(err_lines) - 1, -1, -1):
        if err_lines[i].strip():
            return err_lines[i].strip(), '\n'.join(err_lines[max(0, i - 10):i + 10])
    return '', ''


def extract_failure_reason(stdout, stderr):
    """사람이 읽을 수 있는 한 줄 실패 사유"""
    head, block = extract_failure_block(stdout, stderr)
    if not head:
        return '알 수 없음'
    return summarize_failure(head, block)


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
    """이전 실행의 실패 로그만 정리 (요약 리포트는 보존)"""
    if LOGS_DIR.exists():
        for f in LOGS_DIR.glob('*.log'):
            if f.name.startswith(('summary', 'perf')):
                continue
            f.unlink()


def run_test_with_retry(test_file, tc_id):
    """최대 MAX_RETRIES 회 재시도. (result, attempts, reasons, durations) 반환

    reasons[i]   = i+1 회차 실행의 실패 사유 요약 (성공한 회차는 포함되지 않음)
    durations[i] = i+1 회차 실행에 걸린 시간(초). 속도 분석 로그에서 사용한다.
    """
    last_result = None
    reasons = []
    durations = []
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            print(f"  ↳ 재시도 {attempt - 1}/{MAX_RETRIES - 1} ...", end=' ', flush=True)
        started = time.perf_counter()
        last_result = run_test(test_file)
        durations.append(time.perf_counter() - started)
        if last_result.returncode == 0:
            return last_result, attempt, reasons, durations
        reason = extract_failure_reason(last_result.stdout, last_result.stderr)
        reasons.append(reason)
        if attempt < MAX_RETRIES:
            print(f"❌ ({reason[:50]})")
    return last_result, MAX_RETRIES, reasons, durations


def _digest(path):
    """파일 내용 해시. 파일이 없으면 None"""
    if path is None:
        return None
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


_CLI_ERROR_KEYWORDS = (
    'does not have access',
    'Please login',
    'Invalid API key',
    'Credit balance',
    'usage limit',
    'rate limit',
    'Unauthorized',
    'authentication_error',
    'Failed to authenticate',
    'revoked',
)

# claude_automation.py 의 판별과 동일한 기준 (인증 문제는 재시도 의미 없음)
_AUTH_ERROR_RE = re.compile(
    r'authentication_error'
    r'|failed to authenticate'
    r'|api error:\s*401'
    r'|\b401\b[^\n]{0,80}(?:unauthorized|authentic)'
    r'|(?:token|credential)s?[^\n]{0,40}revoked'
    r'|does not have access'
    r'|please login'
    r'|invalid api key'
    r'|\bunauthorized\b'
    r'|not authenticated'
    r'|인증 오류',
    re.IGNORECASE,
)

AUTH_GUIDE = ('터미널에서 `claude /login` 으로 다시 로그인한 뒤 실행하세요. '
              '`claude logout` 과 `claude setup-token` 은 기존 토큰을 무효화합니다.')


def is_auth_failure(text):
    """재생성 실패 사유가 인증 문제인지"""
    return bool(_AUTH_ERROR_RE.search(text or ''))


def count_popup_hits(stdout, counter):
    """테스트 출력에서 'POPUP_DISMISSED: <이름>' 표시를 세어 counter 에 누적한다.

    한 번도 발동하지 않은 팝업은 기능이 사라졌을 가능성이 있으므로
    실행 요약에서 정리 대상으로 알려 준다.
    """
    for line in (stdout or '').splitlines():
        s = line.strip()
        if s.startswith(DISMISS_MARKER):
            name = s[len(DISMISS_MARKER):].strip()
            counter[name] = counter.get(name, 0) + 1


def _meaningful_lines(text):
    """구분선·빈 줄을 제외한 의미 있는 출력 줄만 추린다."""
    lines = []
    for raw in (text or '').splitlines():
        s = raw.strip()
        if not s or set(s) <= set('=-─· '):
            continue
        lines.append(s)
    return lines


def _strip_log_prefix(line):
    """'2026-09-10 11:43:38,438 - ERROR - ' 같은 로깅 프리픽스 제거"""
    return re.sub(r'^\d{4}-\d{2}-\d{2} [\d:,]+ - \w+ - ', '', line).lstrip('❌⚠️ ')


def summarize_regen(result):
    """재생성 프로세스 출력에서 실패 원인 한 줄 추출"""
    out_lines = _meaningful_lines(result.stdout)
    err_lines = _meaningful_lines(result.stderr)

    for line in out_lines + err_lines:
        if any(k in line for k in _CLI_ERROR_KEYWORDS):
            return f"Claude CLI 인증/사용량 문제 — {line[:90]}"

    for line in err_lines + out_lines:
        if ' - ERROR - ' in line or ' - WARNING - ' in line or line.startswith('❌'):
            return _strip_log_prefix(line)[:120]

    tail = err_lines or out_lines
    return _strip_log_prefix(tail[-1])[:120] if tail else '출력 없음'


def save_regen_log(tc_id, result, summary):
    """재생성 프로세스의 전체 출력을 로그 파일로 보관"""
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / f"regen_{tc_id.replace('-', '_')}.log"
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"재생성 결과: {summary}\n")
        f.write(f"종료 코드: {result.returncode}\n")
        f.write('=' * 60 + '\n\n')
        if result.stdout:
            f.write('--- stdout ---\n')
            f.write(result.stdout)
            f.write('\n')
        if result.stderr:
            f.write('--- stderr ---\n')
            f.write(result.stderr)
    return log_path


def regenerate_tc(tc_id):
    """claude_automation.py --tc {tc_id} 실행.

    반환: (스크립트가 실제로 새로 생성/변경됐는지, 한 줄 요약, 로그 경로)
    파일이 존재한다는 사실만으로는 재생성 성공으로 보지 않는다.
    이전 실행에서 만들어진 스크립트가 그대로 남아 있어도 파일은 존재하기 때문이다.
    """
    before = _digest(find_test_file(tc_id))

    result = subprocess.run(
        [sys.executable, 'claude_automation.py', '--tc', tc_id],
        cwd='.',
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=600,
    )

    after = _digest(find_test_file(tc_id))
    changed = after is not None and after != before

    if changed:
        summary = '스크립트 갱신 완료'
    elif after is None:
        summary = f"스크립트가 생성되지 않음 — {summarize_regen(result)}"
    else:
        summary = f"스크립트가 변경되지 않음 — {summarize_regen(result)}"

    log_path = save_regen_log(tc_id, result, summary)
    return changed, summary, log_path


def git_commit_and_push(regenerated_tc_ids):
    """재생성된 테스트 스크립트를 master 브랜치에 자동 커밋·푸시. 결과 요약 문자열 반환"""
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
        return '변경된 스크립트가 없어 커밋 생략'

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
            return f"{label} 단계에서 실패 — {result.stderr.strip().splitlines()[0][:60] if result.stderr.strip() else '원인 미확인'}"

    file_count = len([x for x in changed_files.splitlines() if x.strip()])
    return f"재설계된 스크립트 {file_count}개 master 브랜치에 커밋·푸시 완료"


# 계정 데이터를 바꿀 가능성이 있다고 보는 신호.
# 같은 영역끼리 동시에 돌면 서로 간섭할 수 있으므로 영역 안에서는 순차로 돌린다.
_MUTATION_RE = re.compile(r'\.fill\(|\.set_input_files\(|저장|삭제|북마크|지원하기|스크랩')


def classify_tests(test_files, order_map):
    """실행 방식에 따라 세 묶음으로 나눈다.

    A 세션 묶음 : 로그인 세션을 만들거나 끊는 케이스. 반드시 순차, 가장 먼저.
                  LOGIN 전체가 여기 들어간다. LOGIN-005 가 로그아웃을 수행하므로
                  다른 케이스와 겹치면 전체 세션이 무너지기 때문이다.
    B 읽기 전용 : 화면만 확인하는 케이스. 자유롭게 병렬.
    C 변경 묶음 : 계정 데이터를 건드릴 수 있는 케이스. 영역별로 묶어
                  영역끼리는 병렬, 같은 영역 안에서는 순차.

    반환: (wave_a, wave_b, wave_c)  — wave_c 는 {영역: [(파일, tc_id)]}
    """
    wave_a, wave_b, wave_c = [], [], {}

    for test_file in test_files:
        fp_key = str(Path(test_file))
        _, tc_id = order_map.get(fp_key, (0, Path(test_file).stem))
        prefix = tc_id.rsplit('-', 1)[0] if '-' in tc_id else '기타'
        try:
            src = Path(test_file).read_text(encoding='utf-8')
        except OSError:
            src = ''

        writes_session = 'storage_state(path=' in src
        if writes_session or prefix == 'LOGIN':
            wave_a.append((test_file, tc_id))
        elif _MUTATION_RE.search(src):
            wave_c.setdefault(prefix, []).append((test_file, tc_id))
        else:
            wave_b.append((test_file, tc_id))

    return wave_a, wave_b, wave_c


def run_case(rec, tc_id, test_file, session_restores, label=''):
    """1단계: 케이스 1건을 재시도까지만 실행한다. 재설계는 하지 않는다.

    MAX_RETRIES 회 모두 실패하면 실패로 기록만 하고 넘어간다.
    재설계는 전체 실행이 끝난 뒤 2단계에서 모아서 처리한다.

    병렬 실행에서 출력이 뒤섞이지 않도록, 화면에 바로 찍지 않고
    케이스가 끝난 뒤 한 덩어리로 돌려준다.

    반환: (마지막 실행 결과, 실패 사유, 출력 줄 목록)
    """
    lines = []
    case_started = time.perf_counter()
    result, attempts, retry_reasons, attempt_durations = run_test_with_retry(test_file, tc_id)
    rec.attempts = attempts
    rec.retry_reasons = retry_reasons
    rec.attempt_durations = attempt_durations

    took = f"{time.perf_counter() - case_started:.0f}초"
    reason = ''
    if result.returncode == 0:
        note = f" (재시도 {attempts - 1}회)" if attempts > 1 else ""
        lines.append(f"{label}{tc_id} ... ✅ 성공{note}  [{took}]")
        rec.status = 'success'
        rec.outcome = (f"{attempts}회차 실행에서 성공" if attempts > 1
                       else '첫 시도에 성공')
    else:
        reason = retry_reasons[-1] if retry_reasons else '알 수 없음'
        lines.append(f"{label}{tc_id} ... ❌ 실패 → {reason[:60]}  [{took}]")
        rec.status = 'failed'
        rec.outcome = f"{attempts}회 실행 모두 실패"
        rec.fail_reason = reason

    rec.duration = time.perf_counter() - case_started

    # LOGIN-005(로그아웃) 완료 후 LOGIN-003(로그인)으로 세션 복원
    # 세션 그룹은 항상 순차로 돌리므로 여기서 경쟁 상태가 생기지 않는다.
    if tc_id == 'LOGIN-005':
        restore_file = find_test_file('LOGIN-003')
        if restore_file:
            restore = run_test(restore_file)
            if restore.returncode == 0:
                lines.append("         🔄 LOGIN-003 재실행으로 세션 복원 ... ✅ 성공")
                session_restores.append((tc_id, True, ''))
            else:
                _, r = save_failure_log('LOGIN-003_restore', restore.stdout, restore.stderr)
                lines.append(f"         🔄 세션 복원 실패 — {r}")
                session_restores.append((tc_id, False, r))

    return result, reason, lines


def regenerate_case(rec, tc_id, result, reason, failed_list, regenerated_ids,
                    skip_regen=False):
    """2단계: 1단계에서 실패한 케이스를 재설계하고 다시 실행한다.

    skip_regen=True 면 앞선 케이스에서 인증 문제가 확인된 것이므로 재설계를 건너뛴다.
    반환값: 이 케이스에서 인증 문제가 확인되면 True
    """
    auth_error = False
    started = time.perf_counter()

    if skip_regen:
        # 인증 문제가 이미 확인된 상태 — 재설계를 시도해도 같은 오류만 반복된다
        log_path, _ = save_failure_log(tc_id, result.stdout, result.stderr)
        print("⏭️  재생성 건너뜀 — 앞선 케이스에서 인증 문제가 확인되었습니다")
        print(f"         📄 {log_path}")
        rec.outcome = '인증 문제로 재설계를 건너뜀'
        rec.log_path = str(log_path)
        failed_list.append((tc_id, f"[재생성 건너뜀] {reason}", log_path))
        return False

    regenerated_ids.append(tc_id)
    rec.regenerated = True
    rec.regen_trigger = reason
    rec.outcome = f"{rec.attempts}회 실행 모두 실패 → 재설계 시도"

    regen_started = time.perf_counter()
    try:
        regen_ok, regen_note, regen_log = regenerate_tc(tc_id)
    except subprocess.TimeoutExpired:
        regen_ok, regen_note, regen_log = False, '재생성 타임아웃 (600초 초과)', None
    rec.regen_duration = time.perf_counter() - regen_started
    rec.regen_built = regen_ok
    rec.regen_note = regen_note

    if regen_ok:
        new_file = find_test_file(tc_id)
        print(f"재생성 완료 → 재실행 중...", end=' ', flush=True)
        rerun_started = time.perf_counter()
        rerun = run_test(new_file)
        rec.rerun_duration = time.perf_counter() - rerun_started
        if rerun.returncode == 0:
            print(f"✅ 재생성 후 성공")
            rec.status = 'success'
            rec.outcome = '재설계 후 재실행에서 성공'
        else:
            log_path, rerun_reason = save_failure_log(tc_id, rerun.stdout, rerun.stderr)
            print(f"❌ 재생성 후에도 실패 → {rerun_reason[:50]}")
            print(f"         📄 {log_path}")
            rec.outcome = '재설계 후 재실행도 실패'
            rec.fail_reason = rerun_reason
            rec.log_path = str(log_path)
            failed_list.append((tc_id, f"[재생성 후 실패] {rerun_reason}", log_path))
    else:
        log_path, _ = save_failure_log(tc_id, result.stdout, result.stderr)
        print(f"❌ 재생성 실패 — {regen_note[:70]}")
        print(f"         📄 {log_path}")
        if regen_log:
            print(f"         📄 {regen_log}")
        rec.outcome = f'재설계 실패로 재실행 불가 — {regen_note}'
        rec.log_path = str(log_path)
        failed_list.append((tc_id, f"[재생성 실패] {regen_note}", log_path))

        if is_auth_failure(regen_note):
            auth_error = True
            print(f"         🔑 인증 문제입니다. 이후 케이스의 재생성은 건너뜁니다.")
            print(f"         🔑 {AUTH_GUIDE}")

    # 2단계에서 쓴 시간을 케이스 소요에 더한다 (속도 분석 로그용)
    rec.duration += time.perf_counter() - started
    return auth_error


def main(workers=DEFAULT_WORKERS):
    started_at = datetime.now()
    clear_logs()
    order_map, meta_map = load_tc_meta()

    all_files = glob.glob('test/*/test_*_success.py')
    test_files = sorted(
        all_files,
        key=lambda f: order_map.get(str(Path(f)), (9999, ''))[0]
    )

    if not test_files:
        print("❌ 실행할 테스트 파일이 없습니다.")
        sys.exit(1)

    total = len(test_files)
    failed_list = []       # (tc_id, reason, log_path)
    regenerated_ids = []   # 재생성이 시도된 tc_id 목록
    session_restores = []  # (기준 tc_id, 성공여부, 사유)

    # 케이스 기록은 NO 순서를 유지해야 리포트가 안정적이다.
    # 병렬 실행에서는 완료 순서가 뒤섞이므로 미리 만들어 두고 채운다.
    rec_by_tc = {}
    for test_file in test_files:
        _, tc_id = order_map.get(str(Path(test_file)), (0, Path(test_file).stem))
        meta = meta_map.get(tc_id, {})
        rec_by_tc[tc_id] = CaseRecord(
            tc_id=tc_id,
            feature=meta.get('feature', ''),
            expected=meta.get('expected', ''),
        )

    wave_a, wave_b, wave_c = classify_tests(test_files, order_map)
    c_total = sum(len(v) for v in wave_c.values())

    print(f"\n{'='*60}")
    print(f"🚀 1단계 — 전체 {total}개 실행 (실패 시 최대 {MAX_RETRIES}회까지 재시도)")
    print(f"{'='*60}")
    print(f"  세션 묶음 {len(wave_a)}개 (순차)"
          f"  /  읽기 전용 {len(wave_b)}개 (병렬 {workers})"
          f"  /  데이터 변경 {c_total}개 (영역 {len(wave_c)}개 병렬)")
    print()

    interrupted = False
    interrupted_tc = ''
    auth_blocked = False   # 인증 문제 확인 후 이어지는 재생성을 건너뛴다
    pending = []           # 1단계에서 실패해 재설계가 필요한 (rec, tc_id, result, reason)
    done = {'n': 0}
    state_lock = threading.Lock()

    def execute(test_file, tc_id):
        """케이스 1건 실행 후 결과를 공유 목록에 반영한다 (스레드 안전)."""
        rec = rec_by_tc[tc_id]
        with state_lock:
            done['n'] += 1
            label = f"[{done['n']}/{total}] "
        result, reason, lines = run_case(rec, tc_id, test_file, session_restores, label)
        emit(lines)
        if rec.status == 'failed':
            with state_lock:
                pending.append((rec, tc_id, result, reason))
        return tc_id

    def run_group(items):
        """한 영역의 케이스들을 순서대로 실행한다 (영역 내부는 순차)."""
        for test_file, tc_id in items:
            execute(test_file, tc_id)

    def run_parallel(jobs, n_workers):
        """jobs 를 병렬로 돌린다. Ctrl+C 가 들어오면 True 를 돌려준다."""
        if not jobs:
            return False
        with ThreadPoolExecutor(max_workers=max(1, n_workers)) as ex:
            futures = [ex.submit(fn, arg) for fn, arg in jobs]
            try:
                for fut in as_completed(futures):
                    fut.result()
            except KeyboardInterrupt:
                for fut in futures:
                    fut.cancel()
                ex.shutdown(wait=False, cancel_futures=True)
                return True
        return False

    # ── A. 세션 묶음 — 반드시 순차, 가장 먼저 ──
    if wave_a:
        print(f"── 세션 묶음 {len(wave_a)}개 (순차) ──")
    for test_file, tc_id in wave_a:
        try:
            execute(test_file, tc_id)
        except KeyboardInterrupt:
            interrupted, interrupted_tc = True, tc_id
            print(f"\n\n⛔ 사용자 중단 (Ctrl+C) — {tc_id} 실행 중 멈췄습니다.\n")
            break

    # ── B. 읽기 전용 — 병렬 ──
    if wave_b and not interrupted:
        print(f"\n── 읽기 전용 {len(wave_b)}개 (병렬 {workers}) ──")
        if run_parallel([(lambda a: execute(*a), (f, t)) for f, t in wave_b], workers):
            interrupted, interrupted_tc = True, '읽기 전용 묶음'
            print(f"\n\n⛔ 사용자 중단 (Ctrl+C)\n")

    # ── C. 데이터 변경 — 영역끼리 병렬, 영역 안에서는 순차 ──
    if wave_c and not interrupted:
        order = sorted(wave_c.items(), key=lambda kv: -len(kv[1]))
        names = ', '.join(f"{k}({len(v)})" for k, v in order)
        print(f"\n── 데이터 변경 {c_total}개 — 영역 {len(wave_c)}개 병렬: {names} ──")
        if run_parallel([(run_group, items) for _, items in order],
                        min(workers, len(order))):
            interrupted, interrupted_tc = True, '데이터 변경 묶음'
            print(f"\n\n⛔ 사용자 중단 (Ctrl+C)\n")

    # 실행된 케이스만 NO 순서대로 모은다 (test_files 는 이미 NO 순 정렬)
    ordered_tcs = [order_map.get(str(Path(f)), (0, Path(f).stem))[1] for f in test_files]
    records = [rec_by_tc[t] for t in ordered_tcs if rec_by_tc[t].attempt_durations]
    order_index = {t: i for i, t in enumerate(ordered_tcs)}
    pending.sort(key=lambda p: order_index.get(p[0].tc_id, 9999))

    if interrupted:
        total = len(records)

    # ───────────────────────── 1단계 중간 결과 ─────────────────────────
    stage1_success = len([r for r in records if r.status == 'success'])
    print(f"\n{'='*60}")
    print("📋 1단계 결과")
    print(f"{'='*60}")
    print(f"✅ 성공: {stage1_success}개  /  ❌ 실패: {len(pending)}개  /  전체: {total}개")

    if pending:
        print(f"\n재시도까지 실패한 케이스 {len(pending)}건:")
        for rec, tc_id, _, reason in pending:
            print(f"   ❌ {tc_id}  ({rec.attempts}회 실행)  →  {reason[:60]}")

    # ───────────────────────── 2단계: 실패분 일괄 재설계 ─────────────────────────
    if pending and not interrupted:
        print(f"\n{'='*60}")
        print(f"🔄 2단계 — 실패한 {len(pending)}개 스크립트 재설계 후 재실행")
        print(f"{'='*60}\n")

        for idx, (rec, tc_id, result, reason) in enumerate(pending, 1):
            print(f"[{idx}/{len(pending)}] {tc_id} 재생성 중...", end=' ', flush=True)
            try:
                if regenerate_case(rec, tc_id, result, reason, failed_list,
                                   regenerated_ids, skip_regen=auth_blocked):
                    auth_blocked = True
            except KeyboardInterrupt:
                interrupted = True
                interrupted_tc = tc_id
                print(f"\n\n⛔ 사용자 중단 (Ctrl+C) — {tc_id} 재생성 중 멈췄습니다.\n")
                # 아직 재설계하지 못한 케이스는 1단계 실패 그대로 남긴다
                for r, t, res, rsn in pending[idx - 1:]:
                    if not r.log_path:
                        log_path, _ = save_failure_log(t, res.stdout, res.stderr)
                        r.log_path = str(log_path)
                        failed_list.append((t, f"[재생성 미실행] {rsn}", log_path))
                break
    elif pending and interrupted:
        print("\nℹ️  실행이 중단되어 재설계를 진행하지 않습니다.")
        for rec, tc_id, result, reason in pending:
            log_path, _ = save_failure_log(tc_id, result.stdout, result.stderr)
            rec.log_path = str(log_path)
            failed_list.append((tc_id, f"[재생성 미실행] {reason}", log_path))

    success_count = len([r for r in records if r.status == 'success'])

    print(f"\n{'='*60}")
    print("📊 최종 결과")
    print(f"{'='*60}")
    print(f"✅ 성공: {success_count}개  /  ❌ 실패: {len(failed_list)}개  /  전체: {total}개")

    recovered = [r for r in records if r.regenerated and r.status == 'success']
    if recovered:
        print(f"   (그중 재설계로 되살린 케이스 {len(recovered)}개: "
              f"{', '.join(r.tc_id for r in recovered)})")

    unused_popups = [n for n in POPUP_NAMES if not POPUP_HITS.get(n)]
    if unused_popups and not interrupted:
        print(f"\n⚠️  이번 실행에서 한 번도 뜨지 않은 팝업: {', '.join(unused_popups)}")
        print(f"   기능이 없어졌다면 ui_helpers.py 의 POPUPS 에서 제거하세요.")

    if auth_blocked:
        print(f"\n🔑 인증 문제로 스크립트 재설계가 수행되지 않았습니다.")
        print(f"   {AUTH_GUIDE}")

    if failed_list:
        print(f"\n❌ 최종 실패한 케이스:")
        for tc_id, reason, log_path in failed_list:
            print(f"   {tc_id}  →  {reason}")
            print(f"           {log_path}")

    # 재생성이 1회라도 있었고, 최종 실패 케이스가 없을 때만 커밋·푸시
    # 중단된 실행은 전체 검증이 끝나지 않았으므로 푸시하지 않는다
    git_result = None
    if interrupted and regenerated_ids:
        print("\nℹ️  실행이 중단되어 Git 커밋·푸시를 건너뜁니다.")
        git_result = '실행 중단으로 커밋·푸시 생략'
    elif regenerated_ids and not failed_list:
        git_result = git_commit_and_push(regenerated_ids)
    elif regenerated_ids and failed_list:
        print("\nℹ️  실패한 케이스가 있어 Git 커밋·푸시를 건너뜁니다.")
        git_result = '실패 케이스가 있어 커밋·푸시 생략'

    # test_cases.json 에 있으나 실행 스크립트가 없는 케이스
    ran_ids = {r.tc_id for r in records}
    skipped = [(tc_id, meta['feature'])
               for tc_id, meta in sorted(meta_map.items(), key=lambda kv: kv[1]['no'])
               if tc_id not in ran_ids]

    finished_at = datetime.now()
    report = build_report(
        records,
        started_at,
        finished_at,
        skipped=skipped,
        session_restores=session_restores,
        git_result=git_result,
        max_retries=MAX_RETRIES,
        interrupted_at=interrupted_tc if interrupted else '',
        auth_blocked=auth_blocked,
        popup_hits=POPUP_HITS,
        popup_names=POPUP_NAMES,
    )
    latest, archived = write_report(LOGS_DIR, report, started_at)
    print(f"\n📄 실행 결과 요약: {latest}")
    print(f"   (이력 보관: {archived})")

    # 속도 분석 로그 (어디에 시간을 썼는지 — 요약 리포트와 목적이 다름)
    perf = build_perf_report(
        records,
        started_at,
        finished_at,
        max_retries=MAX_RETRIES,
        fixed_waits=scan_fixed_waits(),
    )
    perf_latest, perf_archived = write_perf_report(LOGS_DIR, perf, started_at)
    print(f"\n⏱️  실행 속도 분석: {perf_latest}")
    print(f"   (이력 보관: {perf_archived})")

    print()

    if interrupted:
        sys.exit(130)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='테스트 전체 실행')
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS,
                        help=f'병렬 워커 수 (기본 {DEFAULT_WORKERS}). 1이면 순차 실행')
    args = parser.parse_args()

    try:
        main(workers=max(1, args.workers))
    except KeyboardInterrupt:
        # 요약 생성 등 루프 밖에서 중단된 경우 트레이스백 없이 종료
        print("\n\n⛔ 사용자 중단 (Ctrl+C)\n")
        sys.exit(130)
