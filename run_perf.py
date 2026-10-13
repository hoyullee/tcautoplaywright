"""실행 속도 분석 로그 생성 모듈.

run_all_tests.py 가 수집한 케이스별 시간 기록을 받아
'어디에 시간을 썼고, 무엇부터 손대면 되는지' 를 한 장으로 정리한다.

요약 리포트(run_report.py)와 목적이 다르다.
  - 요약 리포트 : 무엇이 성공/실패했는가
  - 속도 로그   : 시간이 어디로 갔는가
"""

import re
import statistics
from pathlib import Path

WIDTH = 78
SEP = '=' * WIDTH
SUB = '-' * WIDTH


def _fmt(sec):
    """초를 사람이 읽는 형태로"""
    sec = max(0.0, float(sec))
    if sec < 60:
        return f"{sec:.0f}초"
    m, s = divmod(int(round(sec)), 60)
    if m < 60:
        return f"{m}분 {s}초"
    h, m = divmod(m, 60)
    return f"{h}시간 {m}분 {s}초"


def _bar(value, total, width=28):
    """비중을 막대로. total 이 0이면 빈 막대"""
    if total <= 0:
        return ' ' * width
    filled = int(round(width * value / total))
    return '█' * filled + '·' * (width - filled)


def _title(lines, no, text):
    lines.append('')
    lines.append(SUB)
    lines.append(f" [{no}] {text}")
    lines.append(SUB)


def scan_fixed_waits(test_dir='test'):
    """스크립트에 박힌 고정 대기(wait_for_timeout) 를 정적으로 합산한다.

    실행 로그가 아니라 코드를 읽어서 구한 값이다.
    반복문 안의 대기는 1회로만 세므로 실제보다 작게 나온다(하한).
    반환: [(초, 호출수, 파일명)] 내림차순
    """
    rows = []
    for f in sorted(Path(test_dir).glob('*/test_*_success.py')):
        try:
            src = f.read_text(encoding='utf-8')
        except OSError:
            continue
        ms = [int(x) for x in re.findall(r'wait_for_timeout\((\d+)\)', src)]
        if ms:
            rows.append((sum(ms) / 1000, len(ms), f.name))
    rows.sort(reverse=True)
    return rows


def build_perf_report(records, started_at, finished_at, *, max_retries=0,
                      fixed_waits=None, workers_hint=4):
    """속도 분석 로그 본문(문자열)을 만든다."""
    fixed_waits = fixed_waits if fixed_waits is not None else []
    wall = (finished_at - started_at).total_seconds()

    # 구간별 합계
    first_try_sec = sum(r.attempt_durations[0] for r in records if r.attempt_durations)
    retry_sec = sum(sum(r.attempt_durations[1:]) for r in records if len(r.attempt_durations) > 1)
    regen_sec = sum(r.regen_duration for r in records)
    rerun_sec = sum(r.rerun_duration for r in records)
    measured = first_try_sec + retry_sec + regen_sec + rerun_sec
    other_sec = max(0.0, wall - measured)

    durations = [r.duration for r in records if r.duration > 0]
    retried = [r for r in records if len(r.attempt_durations) > 1]
    regenerated = [r for r in records if r.regen_duration > 0]

    L = []
    L.append(SEP)
    L.append(' 실행 속도 분석')
    L.append(SEP)
    L.append(f" 실행 시각 : {started_at:%Y-%m-%d %H:%M:%S} ~ {finished_at:%H:%M:%S}")
    L.append(f" 전체 소요 : {_fmt(wall)}   |   케이스 {len(records)}개")
    if durations:
        L.append(f" 케이스당  : 평균 {_fmt(statistics.mean(durations))}"
                 f" / 중앙값 {_fmt(statistics.median(durations))}"
                 f" / 최대 {_fmt(max(durations))}")

    # [1] 시간이 어디로 갔는가
    _title(L, 1, '시간 분해')
    buckets = [
        ('첫 시도 실행', first_try_sec),
        ('재시도 실행', retry_sec),
        ('스크립트 재설계', regen_sec),
        ('재설계 후 재실행', rerun_sec),
        ('기타(오케스트레이션)', other_sec),
    ]
    # 구간 합계가 전체 소요를 넘지 않는 것이 정상이지만,
    # 측정 오차가 있어도 비율이 100%를 넘지 않도록 분모를 보정한다.
    denom = max(wall, measured) or 1.0
    for label, sec in buckets:
        L.append(f" {label:<22} {_bar(sec, denom)} {_fmt(sec):>10}  {sec / denom * 100:5.1f}%")
    L.append('')
    waste = retry_sec + regen_sec
    L.append(f" → 실패로 인해 추가로 쓴 시간(재시도+재설계) : {_fmt(waste)}"
             f" ({waste / denom * 100:.1f}%)")

    # [2] 오래 걸린 케이스
    _title(L, 2, '오래 걸린 케이스 Top 15')
    slow = sorted(records, key=lambda r: -r.duration)[:15]
    L.append(f" {'TC':<18} {'소요':>10}  {'시도':>4}  상태")
    for r in slow:
        if r.duration <= 0:
            continue
        mark = '✅' if r.status == 'success' else '❌'
        extra = ''
        if r.regen_duration:
            extra = f"  (재설계 {_fmt(r.regen_duration)} 포함)"
        L.append(f" {r.tc_id:<18} {_fmt(r.duration):>10}  {r.attempts:>3}회  {mark}{extra}")

    # [3] 재시도가 먹은 시간 — 가장 손쉬운 절감 대상
    _title(L, 3, f'재시도로 추가 소모한 시간 ({len(retried)}건)')
    if not retried:
        L.append(' 없음 — 모든 케이스가 첫 시도에 끝났습니다.')
    else:
        L.append(f" {'TC':<18} {'추가 소모':>10}  회차별 시간")
        for r in sorted(retried, key=lambda r: -sum(r.attempt_durations[1:])):
            extra = sum(r.attempt_durations[1:])
            each = ' / '.join(_fmt(d) for d in r.attempt_durations)
            L.append(f" {r.tc_id:<18} {_fmt(extra):>10}  {each}")
        L.append('')
        L.append(f" → 이 {len(retried)}건을 안정화하면 {_fmt(retry_sec)} 를 회수합니다.")

    # [4] 재설계 비용
    _title(L, 4, f'스크립트 재설계 비용 ({len(regenerated)}건)')
    if not regenerated:
        L.append(' 없음 — 재설계가 발생하지 않았습니다.')
    else:
        for r in sorted(regenerated, key=lambda r: -r.regen_duration):
            built = '생성 성공' if r.regen_built else '생성 실패'
            L.append(f" {r.tc_id:<18} {_fmt(r.regen_duration):>10}  ({built})")
        L.append('')
        L.append(' → 재설계는 Claude CLI 호출이라 한 건당 수 분이 듭니다.')
        L.append('   반복 실패하는 케이스를 먼저 고치면 이 구간이 통째로 사라집니다.')

    # [5] 기능영역별
    _title(L, 5, '기능영역별 소요')
    areas = {}
    for r in records:
        key = r.feature or '미분류'
        total, cnt = areas.get(key, (0.0, 0))
        areas[key] = (total + r.duration, cnt + 1)
    for key in sorted(areas, key=lambda k: -areas[k][0]):
        total, cnt = areas[key]
        avg = total / cnt if cnt else 0
        L.append(f" {key[:28]:<30} {_bar(total, wall, 20)} {_fmt(total):>10}"
                 f"  ({cnt}건, 평균 {_fmt(avg)})")

    # [6] 코드에 박힌 고정 대기
    _title(L, 6, '고정 대기(wait_for_timeout) 상위 15')
    if not fixed_waits:
        L.append(' 측정 대상 없음')
    else:
        total_fixed = sum(s for s, _, _ in fixed_waits)
        calls = sum(n for _, n, _ in fixed_waits)
        L.append(f" 전체 합계 {_fmt(total_fixed)} (호출 {calls}회)"
                 f" — 반복문 내부는 1회로만 계산한 하한값")
        L.append('')
        for sec, n, name in fixed_waits[:15]:
            L.append(f" {name:<46} {_fmt(sec):>8}  ({n}회)")
        L.append('')
        L.append(' → 고정 대기를 조건 대기로 바꾸면 이 시간의 상당 부분을 회수합니다.')
        L.append('   단, 화면 전환 애니메이션을 기다리는 대기가 섞여 있으니 일괄 치환은 위험합니다.')

    # [7] 병렬 실행 시 기대치
    _title(L, 7, '병렬 실행 시 기대 시간')
    if durations:
        longest = max(durations)
        total_work = sum(durations)
        L.append(f" 전체 작업량 합계 : {_fmt(total_work)}")
        L.append(f" 가장 긴 케이스   : {_fmt(longest)}  ← 병렬화해도 이보다 빨라질 수 없음")
        L.append('')
        L.append(f" {'워커 수':<8} {'이론 최소':>12}")
        for w in (2, 3, 4, 6):
            ideal = max(longest, total_work / w)
            mark = '  ← 현재 검토안' if w == workers_hint else ''
            L.append(f" {w:<8} {_fmt(ideal):>12}{mark}")
        L.append('')
        L.append(' 주의: 계정이 하나라 데이터를 바꾸는 케이스는 동시에 돌리면 서로 간섭합니다.')
        L.append('       세션 파일을 쓰는 LOGIN 계열은 순차로 묶어야 합니다.')

    L.append('')
    L.append(SEP)
    hints = []
    if retry_sec > wall * 0.1:
        hints.append(f"재시도가 전체의 {retry_sec / wall * 100:.0f}% — 불안정 케이스 안정화가 1순위")
    if regen_sec > wall * 0.1:
        hints.append(f"재설계가 전체의 {regen_sec / wall * 100:.0f}% — 반복 실패 케이스 정리 필요")
    if durations and sum(durations) / 4 < wall * 0.5:
        hints.append('병렬 실행으로 절반 이하까지 줄일 여지 있음')
    if not hints:
        hints.append('눈에 띄는 낭비 구간 없음 — 개별 케이스의 고정 대기부터 검토')
    L.append(' 우선 순위')
    for i, h in enumerate(hints, 1):
        L.append(f"   {i}. {h}")
    L.append(SEP)
    L.append('')
    return '\n'.join(L)


def write_perf_report(logs_dir, text, started_at):
    """속도 분석 로그를 최신본 + 이력본으로 저장하고 (최신본, 이력본) 경로를 반환."""
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(exist_ok=True)
    archive_dir = logs_dir / 'perf'
    archive_dir.mkdir(exist_ok=True)

    latest = logs_dir / 'perf_latest.log'
    archived = archive_dir / f"run_{started_at:%Y%m%d_%H%M%S}.log"
    for path in (latest, archived):
        path.write_text(text, encoding='utf-8')
    return latest, archived
