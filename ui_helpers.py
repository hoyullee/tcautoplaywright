"""테스트 스크립트가 공유하는 화면 보조 동작.

검증 대상이 아닌 방해 요소(온보딩 팝업 등)를 치우는 코드를 한곳에 모은다.
각 테스트 스크립트가 같은 코드를 따로 들고 있으면 팝업이 늘거나 바뀔 때마다
모든 스크립트를 고쳐야 하므로, 여기에만 등록하고 호출해서 쓴다.

원칙
  - 검증하지 않는다. 팝업이 없으면 조용히 지나간다.
  - 팝업 자체가 검증 대상인 TC 에서는 절대 쓰지 않는다.
    (예: CAREERS-006 은 '희망 근무지 설정' 팝업이 뜨는 것을 확인하는 케이스)

사용법
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ui_helpers import dismiss_optional_popups

    await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
    await page.wait_for_load_state('domcontentloaded')
    await dismiss_optional_popups(page)
"""

# 검증 대상이 아닐 때 닫아야 하는 팝업 목록.
#   name    : 실행 리포트에 표시되는 이름
#   has_text: [role="dialog"] 안에서 이 팝업을 식별하는 텍스트
#   button  : 닫기 위해 누를 버튼 이름
#
# 새 팝업이 생기면 여기에 한 줄만 추가한다. 호출하는 스크립트는 고치지 않아도 된다.
# 기능이 없어져 더 이상 뜨지 않는 항목은 전체 실행 요약의 '미발동' 경고로 확인하고 지운다.
POPUPS = (
    {'name': '희망 근무지 설정', 'has_text': '근무지', 'button': '나중에 하기'},
)

POPUP_NAMES = tuple(p['name'] for p in POPUPS)

# 이 표시를 stdout 에 남기면 run_all_tests.py 가 집계한다.
# AUTOMATION_SUCCESS 와 같은 방식이라 별도 파일이나 프로세스 간 상태가 필요 없다.
DISMISS_MARKER = 'POPUP_DISMISSED:'


async def dismiss_optional_popups(page, timeout=3000):
    """검증 대상이 아닌 팝업이 떠 있으면 닫는다.

    팝업이 없으면 아무 일도 하지 않고 그대로 돌아온다. 실패하지 않는다.
    닫은 경우 stdout 에 'POPUP_DISMISSED: <이름>' 을 남긴다.

    timeout: 팝업 하나당 기다리는 시간(ms). 기본 3초.
    """
    for popup in POPUPS:
        dialog = page.locator('[role="dialog"]', has_text=popup['has_text'])
        try:
            await dialog.wait_for(state='visible', timeout=timeout)
        except Exception:
            continue  # 안 뜨는 게 정상일 수 있다

        try:
            button = dialog.get_by_role('button', name=popup['button'])
            await button.click()
            await dialog.wait_for(state='hidden', timeout=timeout)
        except Exception as e:
            # 닫기에 실패해도 본 검증을 막지 않는다. 원인만 남긴다.
            print(f"POPUP_DISMISS_FAILED: {popup['name']} ({e})")
            continue

        print(f"{DISMISS_MARKER} {popup['name']}")
