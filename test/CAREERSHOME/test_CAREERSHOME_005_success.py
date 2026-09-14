import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 스크롤하면서 '출퇴근 편한 포지션' 섹션 탐색
            # (테스트 케이스에서는 '출퇴근 걱정없는 역세권 포지션'으로 명시되어 있으나
            #  실제 UI는 '출퇴근 편한 포지션'으로 표기됨 - 같은 섹션)
            found_section = False
            for i in range(15):
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(400)

                found = await page.evaluate("""() => {
                    const body = document.body.innerText || '';
                    return body.includes('출퇴근 편한 포지션') || body.includes('출퇴근 걱정없는');
                }""")
                if found:
                    print(f"스크롤 {i+1}번째에 섹션 발견")
                    found_section = True
                    break

            assert found_section, "출퇴근 편한 포지션(역세권) 섹션을 찾을 수 없습니다"

            # 섹션 헤더 텍스트 요소로 스크롤
            section_title = page.locator('h2').filter(has_text='출퇴근 편한 포지션').first
            if not await section_title.count():
                section_title = page.get_by_text('출퇴근 편한 포지션', exact=False).first
            await section_title.scroll_into_view_if_needed()
            await page.wait_for_timeout(800)

            print("역세권(출퇴근 편한) 포지션 섹션 확인 완료")

            # 역 선택 버튼 찾기 (예: '강남역')
            station_btn = page.locator('button').filter(has_text='역').first
            initial_station = await station_btn.inner_text()
            initial_station = initial_station.strip()
            print(f"초기 역 버튼 텍스트: '{initial_station}'")

            assert '역' in initial_station, f"역 선택 버튼을 찾을 수 없습니다: '{initial_station}'"

            # 초기 포지션 카드 수집 (섹션 변경 확인용)
            initial_cards = await page.evaluate("""() => {
                const cards = [...document.querySelectorAll('a[href*="/wd/"]')];
                return cards.slice(0, 15).map(c => c.href);
            }""")
            print(f"초기 포지션 카드 수: {len(initial_cards)}")

            # 역 선택 버튼 클릭 → 드롭다운 열기
            await station_btn.click()
            await page.wait_for_timeout(1500)

            # 다이얼로그에서 역 목록 확인
            dialog = page.locator('[role="dialog"]').first
            dialog_visible = await dialog.is_visible()
            print(f"다이얼로그 표시 여부: {dialog_visible}")
            assert dialog_visible, "역 선택 드롭다운이 열리지 않았습니다"

            # 다이얼로그 내 역 옵션 목록 추출 (li[role="menuitemradio"] 사용)
            station_items = dialog.locator('[role="menuitemradio"]')
            item_count = await station_items.count()
            print(f"다이얼로그 내 역 항목 수: {item_count}")

            station_options = []
            for i in range(item_count):
                item = station_items.nth(i)
                item_text = (await item.inner_text()).strip()
                station_options.append(item_text)
            print(f"다이얼로그 내 역 옵션: {station_options}")

            # 초기 역이 아닌 다른 역 선택
            target_station = None
            target_idx = None
            for i, station_name in enumerate(station_options):
                if station_name and station_name != initial_station and '역' in station_name:
                    target_station = station_name
                    target_idx = i
                    break

            if target_station is None and station_options:
                target_station = station_options[0]
                target_idx = 0

            assert target_station is not None, "선택 가능한 역이 없습니다"
            print(f"선택할 역: '{target_station}' (index: {target_idx})")

            # 역 클릭 - li[role="menuitemradio"] 직접 클릭
            await station_items.nth(target_idx).click()
            print(f"역 선택 클릭 완료: '{target_station}'")

            # 페이지 업데이트 대기
            await page.wait_for_timeout(2000)
            await page.wait_for_load_state('domcontentloaded')

            # 섹션으로 다시 스크롤
            section_title_after = page.locator('h2').filter(has_text='출퇴근 편한 포지션').first
            if await section_title_after.count():
                await section_title_after.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 변경 후 역 버튼 텍스트 확인
            new_station_btn = page.locator('button').filter(has_text='역').first
            new_station_text = await new_station_btn.inner_text()
            new_station_text = new_station_text.strip()
            print(f"변경 후 역 버튼 텍스트: '{new_station_text}'")

            # 변경 후 포지션 카드 수집
            after_cards = await page.evaluate("""() => {
                const cards = [...document.querySelectorAll('a[href*="/wd/"]')];
                return cards.slice(0, 15).map(c => c.href);
            }""")
            print(f"변경 후 포지션 카드 수: {len(after_cards)}")

            # 검증: 역이 변경되었거나 포지션 카드가 새로 로드됨
            station_changed = new_station_text != initial_station
            cards_changed = set(after_cards) != set(initial_cards)
            print(f"역 변경 여부: {station_changed} ('{initial_station}' → '{new_station_text}')")
            print(f"카드 변경 여부: {cards_changed}")

            assert station_changed or cards_changed, (
                f"역 선택 후 변경이 없습니다: 역='{initial_station}'→'{new_station_text}', "
                f"카드수={len(initial_cards)}→{len(after_cards)}"
            )

            print(f"테스트 성공: '{initial_station}' → '{new_station_text}' 역 변경 및 포지션 카드 업데이트 확인")

            await page.screenshot(path='screenshots/test_CAREERSHOME_005_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_005_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
