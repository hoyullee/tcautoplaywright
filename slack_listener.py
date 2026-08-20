#!/usr/bin/env python3
"""Slack 이모지 리액션으로 run_all_tests.py를 실행하고 결과를 같은 스레드에 답글로 남기는 리스너.

Socket Mode 기반이라 공개 URL이나 별도 서버가 필요 없다. 테스트가 이미 정상 동작하는
Mac 로컬에서 상시 실행하는 것을 전제로 한다.

흐름:
    1. 지정한 채널에서 지정한 이모지가 추가되면 reaction_added 이벤트 수신
    2. 해당 스레드에 "실행 시작" 답글을 남기고 (이후 진행률로 갱신)
    3. run_all_tests.py 를 자식 프로세스로 실행
    4. 종료 후 logs/run_summary.json 을 읽어 결과 요약을 스레드에 답글로 게시
    5. 실패 케이스가 있으면 마스킹 처리한 로그 파일을 첨부

필요 환경변수 (.env):
    SLACK_BOT_TOKEN         xoxb-... (필수)
    SLACK_APP_TOKEN         xapp-... (필수, Socket Mode 앱 레벨 토큰)
    SLACK_TRIGGER_CHANNELS  트리거를 허용할 채널 ID (필수, 쉼표로 복수 지정)
    SLACK_TRIGGER_EMOJIS    트리거 이모지 이름 (기본: rocket)
    SLACK_ALLOWED_USERS     트리거를 허용할 사용자 ID (미지정 시 전원 허용)
    TCAUTO_RUN_TIMEOUT      실행 타임아웃 초 (기본: 7200)
    TCAUTO_AUTO_PUSH        재생성 성공 시 자동 푸시 (기본: 1, 끄려면 0)
"""

import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

REPO_DIR = Path(__file__).resolve().parent
load_dotenv(REPO_DIR / '.env')

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# ========== 설정 ==========
BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN', '')
APP_TOKEN = os.getenv('SLACK_APP_TOKEN', '')


def _csv_env(name):
    return {v.strip() for v in os.getenv(name, '').split(',') if v.strip()}


TRIGGER_CHANNELS = _csv_env('SLACK_TRIGGER_CHANNELS')
TRIGGER_EMOJIS = _csv_env('SLACK_TRIGGER_EMOJIS') or {'rocket'}
ALLOWED_USERS = _csv_env('SLACK_ALLOWED_USERS')

RUN_TIMEOUT = int(os.getenv('TCAUTO_RUN_TIMEOUT', '7200'))
PROGRESS_INTERVAL = int(os.getenv('SLACK_PROGRESS_INTERVAL', '15'))
MAX_LOG_BYTES = int(os.getenv('SLACK_MAX_LOG_BYTES', '200000'))
MAX_LOG_FILES = int(os.getenv('SLACK_MAX_LOG_FILES', '5'))
MAX_FAILED_LINES = 20
EVENT_TTL = 600  # 동일 이벤트 재전달 무시 기간(초)

LOGS_DIR = REPO_DIR / 'logs'
SUMMARY_PATH = LOGS_DIR / 'run_summary.json'
LOCK_PATH = REPO_DIR / 'work' / '.tcauto_run.lock'
RUNNER = 'run_all_tests.py'

PROGRESS_RE = re.compile(r'^\[(\d+)/(\d+)\]\s+(\S+)')

# ========== 민감 정보 마스킹 ==========
_SECRET_ENV_KEYS = (
    'WANTED_TEST_EMAIL',
    'WANTED_TEST_PASSWORD',
    'CLAUDE_CODE_OAUTH_TOKEN',
    'SLACK_BOT_TOKEN',
    'SLACK_APP_TOKEN',
    'SLACK_SIGNING_SECRET',
    'GOOGLE_API_KEY',
)

_MASK_PATTERNS = (
    # Slack / Anthropic / Google 토큰 형태
    re.compile(r'xox[abposr]-[A-Za-z0-9-]{8,}'),
    re.compile(r'xapp-[A-Za-z0-9-]{8,}'),
    re.compile(r'sk-ant-[A-Za-z0-9_-]{8,}'),
    re.compile(r'ya29\.[A-Za-z0-9_-]{10,}'),
    # 이메일
    re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
    # password=... / token: ... 형태
    re.compile(
        r'(?i)\b(password|passwd|pwd|secret|token|authorization|api[_-]?key)\b'
        r'\s*[:=]\s*["\']?[^\s"\',;]{4,}'
    ),
    # auth_state.json 류의 쿠키 값
    re.compile(r'"value"\s*:\s*"[^"]{20,}"'),
)


def mask(text):
    """Slack으로 내보내기 전에 계정·토큰·세션 값을 가린다."""
    if not text:
        return text

    # 1) .env 등에 들어있는 실제 값은 정확히 치환
    for key in _SECRET_ENV_KEYS:
        value = os.getenv(key, '')
        if value and len(value) >= 4:
            text = text.replace(value, '***')

    # 2) 패턴 기반 치환
    for pattern in _MASK_PATTERNS:
        text = pattern.sub(lambda m: _mask_match(m.group(0)), text)

    return text


def _mask_match(matched):
    """키 이름은 남기고 값만 가린다."""
    for sep in (':', '='):
        if sep in matched:
            head, _, _tail = matched.partition(sep)
            if len(head) <= 40:
                return f'{head}{sep} ***'
    return '***'


def truncate(text, limit):
    if len(text) <= limit:
        return text
    half = limit // 2
    return (
        text[:half]
        + f'\n\n... (중략: {len(text) - limit:,}자 생략) ...\n\n'
        + text[-half:]
    )


def fmt_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f'{seconds}초'
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f'{minutes}분 {sec}초'
    hours, minutes = divmod(minutes, 60)
    return f'{hours}시간 {minutes}분'


# ========== 동시 실행 방지 ==========
class RunLock:
    """파일 락 — 리스너가 중복 실행되거나 수동 실행과 겹치는 것을 막는다.

    이벤트 핸들러 스레드와 워커 스레드가 함께 접근하므로 내부 상태를
    뮤텍스로 보호한다. 이미 보유 중이면 새 fd를 열지 않고 바로 False를
    반환한다 (fd 누수 및 상태 손상 방지).
    """

    def __init__(self, path):
        self.path = path
        self._fh = None
        self._held = False
        self._guard = threading.Lock()

    def acquire(self):
        with self._guard:
            if self._held:
                return False

            self.path.parent.mkdir(parents=True, exist_ok=True)
            # 'a+' — 락을 못 얻었을 때 보유자가 기록한 PID를 지우지 않도록 truncate 회피
            fh = open(self.path, 'a+')
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fh.close()
                return False

            fh.seek(0)
            fh.truncate()
            fh.write(f'{os.getpid()}\n')
            fh.flush()
            self._fh = fh
            self._held = True
            return True

    def release(self):
        with self._guard:
            fh, self._fh, self._held = self._fh, None, False
            if fh is None:
                return
            try:
                fcntl.flock(fh, fcntl.LOCK_UN)
            except (OSError, ValueError):
                pass
            try:
                fh.close()
            except (OSError, ValueError):
                pass

    def is_held(self):
        with self._guard:
            return self._held


run_lock = RunLock(LOCK_PATH)
_seen_events = {}
_seen_lock = threading.Lock()


def already_handled(key):
    """Socket Mode 재전달로 같은 이벤트가 두 번 오는 것을 무시한다."""
    now = time.monotonic()
    with _seen_lock:
        for k, ts in list(_seen_events.items()):
            if now - ts > EVENT_TTL:
                del _seen_events[k]
        if key in _seen_events:
            return True
        _seen_events[key] = now
        return False


# ========== 테스트 실행 ==========
def build_command():
    """가능하면 caffeinate로 감싸 실행 중 Mac이 절전에 들어가지 않게 한다."""
    base = [sys.executable, '-u', RUNNER]
    caffeinate = shutil.which('caffeinate')
    if caffeinate:
        return [caffeinate, '-i', '-s'] + base
    return base


def run_tests(on_progress):
    """run_all_tests.py 실행. (returncode, tail_lines, timed_out) 반환"""
    cmd = build_command()
    print(f'[run] {" ".join(cmd)}', flush=True)

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        start_new_session=True,
    )

    timed_out = threading.Event()

    def kill_on_timeout():
        timed_out.set()
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(10)
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    watchdog = threading.Timer(RUN_TIMEOUT, kill_on_timeout)
    watchdog.daemon = True
    watchdog.start()

    tail = []
    try:
        for line in proc.stdout:
            line = line.rstrip('\n')
            print(line, flush=True)
            tail.append(line)
            if len(tail) > 60:
                tail.pop(0)
            on_progress(line)
        proc.wait()
    finally:
        watchdog.cancel()
        if proc.stdout:
            proc.stdout.close()

    return proc.returncode, tail, timed_out.is_set()


def load_summary():
    if not SUMMARY_PATH.exists():
        return None
    try:
        with open(SUMMARY_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f'[warn] 요약 파일 파싱 실패: {e}', flush=True)
        return None


# ========== Slack 메시지 구성 ==========
def build_result_text(summary, returncode, tail, timed_out, elapsed):
    if timed_out:
        return (
            f'⏱️ *실행 타임아웃* — {fmt_duration(RUN_TIMEOUT)} 초과로 중단했습니다.\n'
            f'```{mask(truncate(chr(10).join(tail[-25:]), 2000))}```'
        )

    if summary is None:
        return (
            f'⚠️ *실행이 끝났지만 결과 요약을 읽지 못했습니다* '
            f'(exit={returncode}, {fmt_duration(elapsed)})\n'
            f'마지막 출력:\n```{mask(truncate(chr(10).join(tail[-25:]), 2000))}```'
        )

    total = summary.get('total', 0)
    ok = summary.get('success_count', 0)
    ng = summary.get('failed_count', 0)
    regenerated = summary.get('regenerated', [])
    push = summary.get('push') or {}

    icon = '✅' if ng == 0 else '⚠️'
    lines = [
        f'{icon} *자동화 실행 완료* — {ok}/{total} 성공 ({fmt_duration(elapsed)})',
        f'✅ 성공 {ok}    ❌ 실패 {ng}    전체 {total}',
    ]

    if regenerated:
        lines.append(f'🔄 재생성 시도: {", ".join(regenerated)}')

    if push.get('pushed'):
        branch = push.get('branch', 'master')
        commit = push.get('commit', '')
        suffix = f' (`{commit}`)' if commit else ''
        lines.append(f'📦 `{branch}` 브랜치에 자동 푸시 완료{suffix}')
    elif push.get('detail'):
        lines.append(f'📦 푸시 안 함 — {push["detail"]}')

    failed = summary.get('failed', [])
    if failed:
        lines.append('')
        lines.append('*실패 케이스*')
        for item in failed[:MAX_FAILED_LINES]:
            reason = mask(str(item.get('reason', ''))).replace('\n', ' ')
            lines.append(f'• `{item.get("tc_id", "?")}` — {reason[:200]}')
        if len(failed) > MAX_FAILED_LINES:
            lines.append(f'_... 외 {len(failed) - MAX_FAILED_LINES}건_')

    return truncate('\n'.join(lines), 3500)


def upload_failure_logs(client, channel, thread_ts, summary):
    """실패 로그를 마스킹한 사본으로 스레드에 첨부한다."""
    failed = (summary or {}).get('failed', [])
    if not failed:
        return

    for item in failed[:MAX_LOG_FILES]:
        raw = item.get('log')
        if not raw:
            continue
        log_path = REPO_DIR / raw
        if not log_path.exists():
            continue
        try:
            content = log_path.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            print(f'[warn] 로그 읽기 실패 {log_path}: {e}', flush=True)
            continue

        safe = mask(truncate(content, MAX_LOG_BYTES))
        try:
            client.files_upload_v2(
                channel=channel,
                thread_ts=thread_ts,
                filename=log_path.name,
                title=f'{item.get("tc_id", "?")} 실패 로그',
                content=safe,
            )
        except Exception as e:  # noqa: BLE001 - Slack SDK 예외 전부 로깅만
            print(f'[warn] 로그 업로드 실패 {log_path.name}: {e}', flush=True)


def resolve_thread_ts(client, channel, ts):
    """리액션이 스레드 답글에 달린 경우 부모 메시지의 thread_ts를 찾는다."""
    try:
        resp = client.conversations_replies(channel=channel, ts=ts, limit=1)
        messages = resp.get('messages') or []
        if messages:
            first = messages[0]
            return first.get('thread_ts') or first.get('ts') or ts
    except Exception as e:  # noqa: BLE001
        print(f'[warn] thread_ts 확인 실패, 원본 ts 사용: {e}', flush=True)
    return ts


# ========== 이벤트 핸들러 ==========
def handle_reaction_added(event, client):
    reaction = (event.get('reaction') or '').split('::')[0]
    if reaction not in TRIGGER_EMOJIS:
        return

    item = event.get('item') or {}
    if item.get('type') != 'message':
        return

    channel = item.get('channel')
    ts = item.get('ts')
    user = event.get('user')

    if channel not in TRIGGER_CHANNELS:
        print(f'[skip] 허용되지 않은 채널: {channel}', flush=True)
        return

    if ALLOWED_USERS and user not in ALLOWED_USERS:
        print(f'[skip] 허용되지 않은 사용자: {user}', flush=True)
        return

    if already_handled(f'{channel}:{ts}:{reaction}:{event.get("event_ts")}'):
        print('[skip] 중복 이벤트', flush=True)
        return

    thread_ts = resolve_thread_ts(client, channel, ts)

    if not run_lock.acquire():
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text='⏳ 이미 다른 자동화 실행이 진행 중입니다. 끝난 뒤 다시 시도해 주세요.',
        )
        return

    worker = threading.Thread(
        target=execute_run,
        args=(client, channel, thread_ts, user),
        daemon=True,
    )
    worker.start()


def execute_run(client, channel, thread_ts, user):
    started = time.monotonic()
    try:
        posted = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f'🚀 자동화 실행을 시작합니다. (요청: <@{user}>)',
        )
        progress_ts = posted.get('ts')

        state = {'last_update': 0.0, 'line': ''}

        def on_progress(line):
            m = PROGRESS_RE.match(line)
            if m:
                idx, total, tc_id = m.group(1), m.group(2), m.group(3)
                state['line'] = f'[{idx}/{total}] {tc_id}'
            elif '재생성 시도' in line:
                state['line'] = f'{state["line"]} — 재생성 중'
            else:
                return

            now = time.monotonic()
            if now - state['last_update'] < PROGRESS_INTERVAL:
                return
            state['last_update'] = now
            try:
                client.chat_update(
                    channel=channel,
                    ts=progress_ts,
                    text=(
                        f'🚀 자동화 실행 중… (요청: <@{user}>)\n'
                        f'진행: `{state["line"]}`  ·  경과 {fmt_duration(now - started)}'
                    ),
                )
            except Exception as e:  # noqa: BLE001
                print(f'[warn] 진행률 갱신 실패: {e}', flush=True)

        returncode, tail, timed_out = run_tests(on_progress)
        elapsed = time.monotonic() - started
        summary = load_summary()

        try:
            client.chat_update(
                channel=channel,
                ts=progress_ts,
                text=f'🚀 자동화 실행 완료 (요청: <@{user}>) · 소요 {fmt_duration(elapsed)}',
            )
        except Exception as e:  # noqa: BLE001
            print(f'[warn] 진행 메시지 마감 실패: {e}', flush=True)

        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=build_result_text(summary, returncode, tail, timed_out, elapsed),
        )

        if not timed_out:
            upload_failure_logs(client, channel, thread_ts, summary)

    except Exception as e:  # noqa: BLE001 - 워커 스레드에서 예외 유실 방지
        print(f'[error] 실행 중 예외: {e}', flush=True)
        try:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f'❌ 자동화 실행 중 오류가 발생했습니다: `{mask(str(e))[:500]}`',
            )
        except Exception:  # noqa: BLE001
            pass
    finally:
        run_lock.release()


def validate_config():
    missing = []
    if not BOT_TOKEN.startswith('xoxb-'):
        missing.append('SLACK_BOT_TOKEN (xoxb-로 시작)')
    if not APP_TOKEN.startswith('xapp-'):
        missing.append('SLACK_APP_TOKEN (xapp-로 시작)')
    if not TRIGGER_CHANNELS:
        missing.append('SLACK_TRIGGER_CHANNELS (채널 ID)')
    if missing:
        print('❌ 설정이 누락되었습니다. .env를 확인하세요:', file=sys.stderr)
        for m in missing:
            print(f'   - {m}', file=sys.stderr)
        sys.exit(1)

    if not (REPO_DIR / RUNNER).exists():
        print(f'❌ {RUNNER} 를 찾을 수 없습니다: {REPO_DIR}', file=sys.stderr)
        sys.exit(1)


def main():
    validate_config()
    print('=' * 60)
    print('🔌 TC 자동화 Slack 리스너 (Socket Mode)')
    print('=' * 60)
    print(f'저장소       : {REPO_DIR}')
    print(f'트리거 채널  : {", ".join(sorted(TRIGGER_CHANNELS))}')
    print(f'트리거 이모지: {", ".join(sorted(":" + e + ":" for e in TRIGGER_EMOJIS))}')
    print(f'허용 사용자  : {", ".join(sorted(ALLOWED_USERS)) if ALLOWED_USERS else "전원"}')
    print(f'자동 푸시    : {"ON" if os.getenv("TCAUTO_AUTO_PUSH", "1").lower() not in ("0", "false", "no") else "OFF"}')
    print(f'타임아웃     : {fmt_duration(RUN_TIMEOUT)}')
    print('=' * 60)
    print('이모지 대기 중… (종료: Ctrl+C)', flush=True)

    # App 생성 시 토큰 검증(auth.test)이 일어나므로 설정 확인 이후에 만든다.
    app = App(token=BOT_TOKEN)
    app.event('reaction_added')(handle_reaction_added)
    SocketModeHandler(app, APP_TOKEN).start()


if __name__ == '__main__':
    main()
