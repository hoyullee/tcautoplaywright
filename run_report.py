"""실행 결과 요약 리포트 생성 모듈.

run_all_tests.py 가 수집한 케이스별 기록을 받아
'한 장으로 읽히는' 요약 로그를 만든다.

원칙: 코드/스택트레이스/원본 로그를 옮기지 않고
      "어떤 기능이 → 어떤 문제로 → 어떻게 되었다" 한 줄로 정리한다.
"""

import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

WIDTH = 78
SEP = '=' * WIDTH
SUB = '-' * WIDTH

# ─────────────────────────────────────────────────────────────
# 케이스 기록
# ─────────────────────────────────────────────────────────────

@dataclass
class CaseRecord:
    tc_id: str
    feature: str = ''            # 기능영역
    expected: str = ''           # 기대결과
    attempts: int = 1            # 총 실행 시도 횟수
    retry_reasons: list = field(default_factory=list)   # 재시도를 유발한 사유(요약)
    regenerated: bool = False    # 재설계(스크립트 재생성) 시도 여부
    regen_trigger: str = ''      # 재설계를 유발한 사유(요약)
    regen_built: bool = False    # 재설계 스크립트 생성 성공 여부
    regen_note: str = ''         # 재설계 결과 한 줄 요약(생성 실패 사유 등)
    status: str = 'success'      # success | failed
    outcome: str = ''            # 최초 성공 / 재시도 후 성공 / 재설계 후 성공 / 실패
    fail_reason: str = ''        # 최종 실패 사유(요약)
    log_path: str = ''           # 상세 로그 경로
    duration: float = 0.0        # 소요 시간(초)

    @property
    def retried(self):
        return self.attempts > 1


# ─────────────────────────────────────────────────────────────
# 실패 사유 요약
# ─────────────────────────────────────────────────────────────

_ACTION_KO = {
    'click': '클릭',
    'dblclick': '더블클릭',
    'fill': '입력',
    'type': '입력',
    'press': '키 입력',
    'check': '체크',
    'uncheck': '체크 해제',
    'hover': '마우스 오버',
    'select_option': '옵션 선택',
    'goto': '페이지 이동',
    'wait_for': '표시 대기',
    'wait_for_selector': '표시 대기',
    'wait_for_load_state': '로딩 완료 대기',
    'wait_for_url': 'URL 전환 대기',
    'inner_text': '텍스트 읽기',
    'text_content': '텍스트 읽기',
    'get_attribute': '속성 읽기',
    'is_visible': '표시 확인',
    'is_enabled': '활성 확인',
    'screenshot': '스크린샷 저장',
    'scroll_into_view_if_needed': '스크롤',
    'set_input_files': '파일 업로드',
    'count': '개수 확인',
}

_ROLE_KO = {
    'button': '버튼',
    'link': '링크',
    'textbox': '입력란',
    'checkbox': '체크박스',
    'radio': '라디오 버튼',
    'tab': '탭',
    'heading': '제목',
    'option': '옵션',
    'combobox': '선택 상자',
    'listitem': '목록 항목',
    'img': '이미지',
    'dialog': '다이얼로그',
}


def _subject(word):
    """한글 종성 유무에 따라 주격 조사(이/가)를 붙인다."""
    if not word:
        return word
    last = word[-1]
    if '가' <= last <= '힣':
        has_final = (ord(last) - 0xAC00) % 28 != 0
        return word + ('이' if has_final else '가')
    return word + '이'


def _display_width(text):
    """한글·전각 문자를 2칸으로 계산한 표시 폭"""
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)


def _pad(text, width):
    """표시 폭 기준 좌측 정렬 패딩"""
    return text + ' ' * max(0, width - _display_width(text))


def _pretty_target(raw):
    """playwright 로케이터 표현식을 사람이 읽는 대상 이름으로 바꾼다."""
    if not raw:
        return ''
    raw = raw.strip().rstrip('.')

    m = re.search(r'get_by_role\(["\'](\w+)["\']\s*,\s*name=["\'](.+?)["\']', raw)
    if m:
        return f"'{m.group(2)}' {_ROLE_KO.get(m.group(1), m.group(1))}"
    m = re.search(r'get_by_role\(["\'](\w+)["\']', raw)
    if m:
        return f"{_ROLE_KO.get(m.group(1), m.group(1))} 요소"
    for fn, label in (('get_by_text', ''), ('get_by_label', '라벨'),
                      ('get_by_placeholder', '입력란'), ('get_by_title', '제목'),
                      ('get_by_test_id', '요소')):
        m = re.search(rf'{fn}\(["\'](.+?)["\']', raw)
        if m:
            name = m.group(1)
            return f"'{name}' {label}".strip() if label else f"'{name}' 텍스트"
    m = re.search(r'locator\(["\'](.+?)["\']', raw)
    if m:
        sel = m.group(1)
        return f"요소({sel[:40]})"
    m = re.search(r'navigation to ["\'](.+?)["\']', raw)
    if m:
        return m.group(1)[:60]
    return raw[:60]


def _ms_to_sec(ms):
    try:
        s = int(ms) / 1000
        return f"{s:g}초"
    except (TypeError, ValueError):
        return f"{ms}ms"


def summarize_failure(head, block):
    """예외 첫 줄(head)과 그 뒤 로그 블록(block)을 한 문장으로 요약."""
    head = (head or '').strip()
    block = block or ''
    if not head:
        return '알 수 없는 오류'
    # head 와 block 을 붙일 때 반드시 개행으로 구분 (토큰이 이어붙어 오인식되는 것 방지)
    combined = f"{head}\n{block}"

    # 1) 네트워크 오류
    m = re.search(r'net::(ERR_[A-Z_]+)', combined)
    if m:
        code = m.group(1)
        label = {
            'ERR_NAME_NOT_RESOLVED': '도메인 주소를 확인할 수 없음',
            'ERR_CONNECTION_REFUSED': '서버가 연결을 거부함',
            'ERR_CONNECTION_TIMED_OUT': '서버 응답이 없음',
            'ERR_INTERNET_DISCONNECTED': '네트워크가 끊김',
            'ERR_ABORTED': '요청이 중단됨',
        }.get(code, code)
        return f"네트워크 오류({label})로 페이지를 열지 못함"

    # 2) 브라우저/페이지 비정상 종료
    if 'has been closed' in head or 'TargetClosedError' in head or 'Browser closed' in head:
        return '브라우저 또는 페이지가 실행 중 예기치 않게 종료됨'

    # 3) strict mode 위반 (선택자가 여러 요소에 매칭)
    if 'strict mode violation' in combined:
        m = re.search(r'resolved to (\d+) elements', combined)
        cnt = f"{m.group(1)}개" if m else '여러 개'
        loc = re.search(r'violation: (.+?) resolved', combined)
        target = _pretty_target(loc.group(1) if loc else '')
        who = f"{target} " if target else ''
        return f"{who}선택자가 {cnt} 요소에 동시에 매칭되어 대상을 특정하지 못함"

    # 4) playwright 타임아웃 (동작 + 대상 + 대기시간)
    m = re.match(r'(?:Locator|Page|Frame|ElementHandle|FrameLocator|Keyboard|Mouse)\.'
                 r'(\w+):\s*Timeout (\d+)ms exceeded', head)
    if m:
        action = _ACTION_KO.get(m.group(1), m.group(1))
        wait = _ms_to_sec(m.group(2))
        w = re.search(r'waiting for (.+)', block)
        target = _pretty_target(w.group(1)) if w else ''
        if target:
            return f"{target} {_subject(action)} {wait} 내 완료되지 않아 대기 시간 초과"
        return f"{action} 동작이 {wait} 내 완료되지 않아 대기 시간 초과"

    m = re.search(r'Timeout (\d+)ms exceeded', head)
    if m:
        w = re.search(r'waiting for (.+)', block)
        target = _pretty_target(w.group(1)) if w else ''
        who = f"{target} 대기 중 " if target else ''
        return f"{who}{_ms_to_sec(m.group(1))} 대기 시간 초과"

    # 5) 검증 실패
    if head.startswith('AssertionError') or head.startswith('assert '):
        msg = head.split(':', 1)[1].strip() if ':' in head else head
        msg = re.sub(r'\s+', ' ', msg)
        return f"기대 결과 검증 실패 — {msg[:120]}" if msg else '기대 결과 검증 실패'

    # 6) 스크립트/환경 오류
    script_errors = {
        'ModuleNotFoundError': '실행에 필요한 패키지가 설치되지 않음',
        'ImportError': '모듈을 불러오지 못함',
        'SyntaxError': '테스트 스크립트 문법 오류',
        'IndentationError': '테스트 스크립트 들여쓰기 오류',
        'FileNotFoundError': '실행에 필요한 파일이 없음',
        'PermissionError': '파일 접근 권한 부족',
        'JSONDecodeError': '저장된 데이터 형식이 올바르지 않음',
    }
    for key, label in script_errors.items():
        if head.startswith(key):
            detail = head.split(':', 1)[1].strip() if ':' in head else ''
            return f"{label}{f' ({detail[:60]})' if detail else ''}"

    for key, label in (('KeyError', '데이터에 필요한 키가 없음'),
                       ('AttributeError', '없는 속성/메서드 호출'),
                       ('TypeError', '잘못된 타입으로 호출'),
                       ('ValueError', '잘못된 값으로 호출'),
                       ('IndexError', '없는 순번의 요소 참조')):
        if head.startswith(key):
            detail = head.split(':', 1)[1].strip() if ':' in head else ''
            return f"스크립트 실행 오류 — {label}{f' ({detail[:50]})' if detail else ''}"

    # 7) 그 외
    return re.sub(r'\s+', ' ', head)[:140]


# ─────────────────────────────────────────────────────────────
# 리포트 작성
# ─────────────────────────────────────────────────────────────

def _fmt_duration(sec):
    sec = int(round(sec))
    if sec < 60:
        return f"{sec}초"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}분 {s}초"
    h, m = divmod(m, 60)
    return f"{h}시간 {m}분 {s}초"


def _one_line(text, limit=70):
    text = re.sub(r'\s+', ' ', (text or '').strip())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def _git_head():
    try:
        branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                capture_output=True, text=True, timeout=5).stdout.strip()
        sha = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        return f"{branch} @ {sha}" if branch and sha else '알 수 없음'
    except Exception:
        return '알 수 없음'


def _title(lines, no, text, count=None):
    lines.append('')
    lines.append(SUB)
    label = f" [{no}] {text}"
    if count is not None:
        label += f" ({count}건)"
    lines.append(label)
    lines.append(SUB)


def build_report(records, started_at, finished_at, *,
                 skipped=None, session_restores=None, git_result=None,
                 max_retries=0, interrupted_at='', auth_blocked=False,
                 popup_hits=None, popup_names=()):
    """요약 리포트 본문(문자열)을 만든다."""
    skipped = skipped or []
    session_restores = session_restores or []

    total = len(records)
    success = [r for r in records if r.status == 'success']
    failed = [r for r in records if r.status == 'failed']
    retried = [r for r in records if r.retried]
    regenerated = [r for r in records if r.regenerated]

    first_try = [r for r in success if not r.retried and not r.regenerated]
    retry_ok = [r for r in success if r.retried and not r.regenerated]
    regen_ok = [r for r in success if r.regenerated]

    rate = f"{len(success) / total * 100:.1f}%" if total else '-'
    elapsed = _fmt_duration((finished_at - started_at).total_seconds())

    L = []
    L.append(SEP)
    L.append(' 자동화 테스트 실행 결과 요약')
    L.append(SEP)
    L.append(f" 실행 시각 : {started_at:%Y-%m-%d %H:%M:%S} ~ {finished_at:%H:%M:%S}"
             f"  (소요 {elapsed})")
    L.append(f" 실행 환경 : Python {sys.version.split()[0]} / {sys.platform}"
             f" / git {_git_head()}")
    L.append(f" 재시도 정책 : 실패 시 최대 {max_retries}회 실행 → 계속 실패하면 스크립트 재설계 후 1회 재실행")
    if interrupted_at:
        L.append(f" ⛔ 중단 알림 : 사용자가 실행을 중단했습니다 ({interrupted_at} 진행 중)."
                 f" 아래 결과는 완료된 케이스만 집계한 것입니다.")
    if auth_blocked:
        L.append(" 🔑 인증 알림 : Claude CLI 인증 문제로 스크립트 재설계가 수행되지 않았습니다."
                 " claude /login 으로 재로그인 후 다시 실행하세요.")

    # [1] 전체 결과
    _title(L, 1, '전체 결과')
    L.append(f" 전체 {total}개   |   성공 {len(success)}개 ({rate})   |   실패 {len(failed)}개")
    L.append('')
    L.append(f"   · 첫 시도에 성공      : {len(first_try)}개")
    L.append(f"   · 재시도 후 성공      : {len(retry_ok)}개")
    L.append(f"   · 재설계 후 성공      : {len(regen_ok)}개")
    L.append(f"   · 최종 실패           : {len(failed)}개")
    L.append('')
    L.append(f" 재시도 발생 {len(retried)}건 / 재설계 발생 {len(regenerated)}건"
             f" → 불안정 케이스 {len(retried) + len([r for r in regenerated if not r.retried])}건")
    if failed:
        L.append(f" 실패 케이스 : {', '.join(r.tc_id for r in failed)}")

    # [2] 재설계된 케이스
    _title(L, 2, '재설계(스크립트 재생성)된 케이스', len(regenerated))
    if not regenerated:
        L.append(' 없음 — 스크립트를 다시 생성한 케이스가 없습니다.')
    for r in regenerated:
        icon = '✅' if r.status == 'success' else '❌'
        L.append(f" {icon} {r.tc_id}  ({_one_line(r.feature, 50)})")
        L.append(f"      · 재설계 사유 : {r.attempts}회 실행 모두 실패 — {_one_line(r.regen_trigger, 55)}")
        if not r.regen_built:
            note = f" — {_one_line(r.regen_note, 55)}" if r.regen_note else ''
            L.append(f"      → 최종 결과 : 스크립트 재생성 자체가 실패해 재실행하지 못함{note} (실패)")
        elif r.status == 'success':
            L.append('      → 최종 결과 : 재생성한 스크립트로 재실행하여 성공')
        else:
            L.append(f"      → 최종 결과 : 재생성 후 재실행도 실패 — {_one_line(r.fail_reason, 55)}")
        L.append('')

    # [3] 최종 실패한 케이스
    _title(L, 3, '최종 실패한 케이스', len(failed))
    if not failed:
        L.append(' 없음 — 모든 케이스가 성공했습니다.')
    for r in failed:
        L.append(f" ❌ {r.tc_id}  ({_one_line(r.feature, 50)})")
        if r.expected:
            L.append(f"      · 기대 결과 : {_one_line(r.expected, 60)}")
        L.append(f"      · 문제      : {_one_line(r.fail_reason, 60)}")
        course = f"{r.attempts}회 실행 실패"
        if r.regenerated:
            course += ' → 재설계 후 재실행도 실패' if r.regen_built else ' → 재설계 생성 실패'
        L.append(f"      · 조치 경과 : {course}")
        if r.log_path:
            L.append(f"      · 상세 로그 : {r.log_path}")
        L.append('')

    # [4] 기능영역별 결과
    areas = {}
    for r in records:
        key = _one_line(r.feature or '미분류', 40)
        ok, ng = areas.get(key, (0, 0))
        areas[key] = (ok + (1 if r.status == 'success' else 0),
                      ng + (1 if r.status == 'failed' else 0))
    _title(L, 4, '기능영역별 결과')
    for key in sorted(areas, key=lambda k: (-areas[k][1], k)):
        ok, ng = areas[key]
        flag = '❌' if ng else '✅'
        L.append(f" {flag} {_pad(key, 44)} 성공 {ok:>2} / 실패 {ng:>2}")

    # [5] 미실행 케이스
    if interrupted_at:
        skip_title = '미실행 케이스 (스크립트 없음 + 중단으로 실행하지 못한 케이스)'
        skip_note = '실행되지 않음'
    else:
        skip_title = '미실행 케이스 (스크립트 없음)'
        skip_note = '실행 스크립트가 없어 제외됨'
    _title(L, 5, skip_title, len(skipped))
    if not skipped:
        L.append(' 없음 — test_cases.json의 모든 케이스에 실행 스크립트가 있습니다.')
    for tc_id, feature in skipped[:15]:
        L.append(f" · {tc_id}  ({_one_line(feature, 50)}) — {skip_note}")
    if len(skipped) > 15:
        L.append(f" · … 외 {len(skipped) - 15}건 "
                 f"({', '.join(tc for tc, _ in skipped[15:])[:200]})")

    # [6] 부가 동작
    _title(L, 6, '부가 동작')
    if session_restores:
        for tc_id, ok, reason in session_restores:
            if ok:
                L.append(f" ✅ 세션 복원 : {tc_id} 완료 후 재로그인 성공")
            else:
                L.append(f" ⚠️  세션 복원 : {tc_id} 완료 후 재로그인 실패 — {_one_line(reason, 50)}")
    else:
        L.append(' · 세션 복원 : 해당 없음')
    L.append(f" · Git 반영  : {git_result or '해당 없음 (재설계 없음)'}")

    # 공용 헬퍼가 닫은 팝업 집계.
    # 한 번도 발동하지 않은 항목은 기능이 없어졌을 수 있으므로 정리 대상으로 알린다.
    if popup_names:
        hits = popup_hits or {}
        for name in popup_names:
            n = hits.get(name, 0)
            if n:
                L.append(f" · 팝업 정리 : '{name}' {n}회 닫음")
            else:
                L.append(f" ⚠️  팝업 정리 : '{name}' 이 이번 실행에서 한 번도 뜨지 않았습니다."
                         f" 기능이 없어졌다면 ui_helpers.py 의 POPUPS 에서 제거하세요.")
        unknown = [k for k in hits if k not in popup_names]
        for name in unknown:
            L.append(f" · 팝업 정리 : '{name}' {hits[name]}회 닫음 (POPUPS 미등록)")

    # 가장 오래 걸린 케이스
    slow = sorted(records, key=lambda r: -r.duration)[:5]
    if slow and slow[0].duration > 0:
        _title(L, 7, '오래 걸린 케이스 Top 5')
        for r in slow:
            L.append(f" · {_pad(r.tc_id, 16)} {_pad(_fmt_duration(r.duration), 10)}"
                     f"  ({_one_line(r.feature, 40)})")

    L.append('')
    L.append(SEP)
    verdict = '전체 성공' if not failed else f"{len(failed)}건 실패 — 위 [3]항 확인 필요"
    L.append(f" 결론 : {verdict}")
    L.append(SEP)
    L.append('')
    return '\n'.join(L)


def write_report(logs_dir, report_text, started_at):
    """요약 리포트를 최신본 + 이력본으로 저장하고 (최신본, 이력본) 경로를 반환."""
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(exist_ok=True)
    archive_dir = logs_dir / 'summary'
    archive_dir.mkdir(exist_ok=True)

    latest = logs_dir / 'summary_latest.log'
    archived = archive_dir / f"run_{started_at:%Y%m%d_%H%M%S}.log"
    for path in (latest, archived):
        path.write_text(report_text, encoding='utf-8')
    return latest, archived
