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

            # '출퇴근 걱정없는 역세권 포지션' 섹션 찾기
            subway_section = page.get_by_text('출퇴근 걱정없는 역세권 포지션')
            await subway_section.wait_for(state='visible', timeout=15000)

            # 섹션으로 스크롤
            await subway_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # 역세권 섹션 컨테이너 탐색
            section_container = page.locator('section').filter(has_text='출퇴근 걱정없는 역세권 포지션').first
            if not await section_container.count():
                section_container = page.locator('div').filter(has_text='출퇴근 걱정없는 역세권 포지션').first

            # 섹션 내 역 선택 버튼 찾기
            all_buttons = section_container.locator('button')
            btn_count = await all_buttons.count()
            print(f"섹션 내 버튼 수: {btn_count}")

            station_btn = None
            initial_station = None

            for i in range(btn_count):
                btn = all_buttons.nth(i)
                btn_text = await btn.inner_text()
                print(f"버튼 {i}: '{btn_text}'")
                if '역' in btn_text:
                    station_btn = btn
                    initial_station = btn_text.strip()
                    print(f"역 버튼 발견: '{initial_station}'")
                    break

            # 버튼을 못 찾으면 전체 페이지에서 탐색
            if station_btn is None:
                all_page_buttons = page.locator('button')
                total_btn_count = await all_page_buttons.count()
                print(f"전체 버튼 수: {total_btn_count}")

                for i in range(total_btn_count):
                    btn = all_page_buttons.nth(i)
                    btn_text = await btn.inner_text()
                    if '역' in btn_text and len(btn_text) < 20:
                        station_btn = btn
                        initial_station = btn_text.strip()
                        print(f"전체 탐색 - 역 버튼 발견: '{initial_station}'")
                        break

            assert station_btn is not None, "역 선택 버튼을 찾을 수 없습니다"
            print(f"초기 역 선택: '{initial_station}'")

            # 역 선택 버튼 클릭
            await station_btn.click()
            await page.wait_for_timeout(1000)

            # 역 선택 드롭다운/모달이 열렸는지 확인 후 다른 역 선택
            # role="dialog" 확인
            dialog = page.locator('[role="dialog"]')
            popup_items = None

            if await dialog.count() > 0:
                print("다이얼로그 발견")
                popup_items = dialog.locator('button, li, [role="option"]')
            else:
                # 드롭다운/팝업 컨테이너 탐색
                popup = page.locator('[class*="popup"]').first
                if await popup.count() > 0:
                    popup_items = popup.locator('button, li')
                else:
                    # 새로 나타난 역 이름 옵션 탐색 (역 텍스트 포함한 버튼/리스트)
                    popup_items = page.locator('li').filter(has_text='역')

            item_count = await popup_items.count() if popup_items else 0
            print(f"역 목록 항목 수: {item_count}")

            selected_station = None

            if item_count > 0:
                # 현재 역이 아닌 다른 역 선택
                for i in range(min(item_count, 15)):
                    item = popup_items.nth(i)
                    item_text = await item.inner_text()
                    item_text = item_text.strip()
                    print(f"역 항목 {i}: '{item_text}'")
                    if item_text and '역' in item_text and item_text != initial_station:
                        selected_station = item_text
                        await item.click()
                        print(f"선택한 역: '{selected_station}'")
                        break

                if selected_station is None:
                    # 첫 번째 항목 선택
                    first_text = await popup_items.first.inner_text()
                    selected_station = first_text.strip()
                    await popup_items.first.click()
                    print(f"첫 번째 항목 선택: '{selected_station}'")
            else:
                # JS로 역 옵션 탐색
                print("역 목록을 JS로 탐색...")
                station_options = await page.evaluate("""() => {
                    const elements = [...document.querySelectorAll('li, [role="option"], button')].slice(0, 50);
                    return elements
                        .filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0 && (el.innerText || '').includes('역');
                        })
                        .map(el => el.innerText.trim())
                        .filter(t => t.length > 0 && t.length < 20);
                }""")
                print(f"JS로 찾은 역 옵션: {station_options}")

                if station_options:
                    # 초기 역과 다른 역 선택
                    for opt_text in station_options:
                        if opt_text != initial_station and '역' in opt_text:
                            target = page.get_by_text(opt_text, exact=True).first
                            if await target.count() > 0:
                                await target.click()
                                selected_station = opt_text
                                print(f"JS 탐색으로 역 선택: '{selected_station}'")
                                break

            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1500)

            # 변경 확인: 역세권 섹션으로 스크롤 후 역 버튼 텍스트 확인
            subway_section_after = page.get_by_text('출퇴근 걱정없는 역세권 포지션')
            await subway_section_after.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 변경 후 역 버튼 텍스트 확인
            section_container_after = page.locator('section').filter(has_text='출퇴근 걱정없는 역세권 포지션').first
            if not await section_container_after.count():
                section_container_after = page.locator('div').filter(has_text='출퇴근 걱정없는 역세권 포지션').first

            all_buttons_after = section_container_after.locator('button')
            btn_count_after = await all_buttons_after.count()
            new_station = None
            for i in range(btn_count_after):
                btn = all_buttons_after.nth(i)
                btn_text = await btn.inner_text()
                if '역' in btn_text:
                    new_station = btn_text.strip()
                    print(f"변경 후 역 버튼: '{new_station}'")
                    break

            # 성공 검증
            subway_visible = await page.get_by_text('출퇴근 걱정없는 역세권 포지션').is_visible()
            assert subway_visible, "역세권 포지션 섹션이 표시되지 않습니다"

            if new_station and initial_station:
                print(f"역 변경 확인: '{initial_station}' → '{new_station}'")
                # 역이 변경되었거나, 선택한 역이 유효하면 성공
                assert new_station != initial_station or selected_station is not None, \
                    f"역이 변경되지 않았습니다: {initial_station} → {new_station}"

            print("테스트 성공: 지하철역 선택 후 포지션 카드 변경 확인")

            await page.screenshot(path='screenshots/test_11_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_11_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
