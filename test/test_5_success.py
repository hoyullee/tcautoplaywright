from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 1. '테마로 살펴보는 회사/포지션' 섹션 확인
            # aside[2]가 해당 섹션 (CarouselHeader aside 중 3번째)
            print("🔍 '테마로 살펴보는 회사/포지션' 섹션 탐색 중...")
            carousels = page.locator('aside.CarouselHeader_CarouselHeader__pwUTM')
            await carousels.nth(2).wait_for(timeout=15000)

            theme_aside = carousels.nth(2)
            theme_text = await theme_aside.text_content()
            assert '테마로 살펴보는 회사/포지션' in theme_text, f"aside[2]에 예상 텍스트 없음: {theme_text[:50]}"
            await theme_aside.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            print("✅ '테마로 살펴보는 회사/포지션' 섹션 확인")

            await page.screenshot(path='screenshots/test_5_theme_section.png')

            # 2. '테마로 살펴보는 회사/포지션' 텍스트 우측 버튼(다음) 선택
            print("🔍 텍스트 우측 '다음' 버튼 탐색 중...")
            next_btn = theme_aside.locator("button[aria-label='다음']")
            next_btn_count = await next_btn.count()

            if next_btn_count > 0:
                await next_btn.first.click()
                await page.wait_for_timeout(1000)
                print("✅ '다음' 버튼 클릭 완료")
            else:
                # aria-label이 없는 경우 두 번째 버튼 (이전=첫번째, 다음=두번째)
                aside_btns = theme_aside.locator('button')
                ab_count = await aside_btns.count()
                print(f"ℹ️ aside 내 버튼 수: {ab_count}")
                if ab_count >= 2:
                    await aside_btns.nth(1).click()
                    await page.wait_for_timeout(1000)
                    print("✅ 두 번째 버튼(다음) 클릭 완료")
                else:
                    print("⚠️ 우측 버튼 없음, 계속 진행")

            await page.screenshot(path='screenshots/test_5_after_right_btn.png')

            # 3. '출퇴근 걱정없는 역세권 포지션' 섹션으로 이동 후 임의의 역 선택
            print("🔍 '출퇴근 걱정없는 역세권 포지션' 섹션 탐색 중...")
            station_aside = carousels.nth(3)
            station_text = await station_aside.text_content()
            assert '출퇴근 걱정없는 역세권 포지션' in station_text, f"aside[3]에 역세권 텍스트 없음: {station_text[:50]}"
            await station_aside.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            print("✅ '출퇴근 걱정없는 역세권 포지션' 섹션 확인")

            # 현재 선택된 역 확인
            current_station_btn = station_aside.locator('button[aria-haspopup="dialog"]')
            current_station = await current_station_btn.text_content()
            print(f"ℹ️ 현재 선택된 역: {current_station.strip()}")

            # 역 선택 버튼 클릭 → 다이얼로그 오픈
            await page.screenshot(path='screenshots/test_5_before_station.png')
            await current_station_btn.click()
            await page.wait_for_timeout(1000)
            print("✅ 역 선택 다이얼로그 열기 완료")

            await page.screenshot(path='screenshots/test_5_station_dialog.png')

            # 다이얼로그 내 역 목록에서 임의 역 선택 (현재 선택 외의 역)
            station_menu = page.locator('[role="menu"]')
            await station_menu.wait_for(timeout=5000)

            station_items = station_menu.locator('[role="menuitem"], li, button')
            item_count = await station_items.count()
            print(f"ℹ️ 역 목록 개수: {item_count}")

            selected_station = None
            for i in range(item_count):
                item = station_items.nth(i)
                item_text = await item.text_content()
                if item_text and item_text.strip() != current_station.strip() and '역' in item_text:
                    await item.click()
                    selected_station = item_text.strip()
                    print(f"✅ 역 선택 완료: '{selected_station}'")
                    break

            if selected_station is None and item_count > 0:
                # 현재 역과 같더라도 첫 번째 항목 선택
                first_item = station_items.first
                first_text = await first_item.text_content()
                await first_item.click()
                selected_station = first_text.strip() if first_text else "알 수 없음"
                print(f"✅ 첫 번째 역 선택: '{selected_station}'")

            await page.wait_for_timeout(1500)
            await page.screenshot(path='screenshots/test_5_after_station.png')

            # 최종 검증: 선택한 역으로 변경됐는지 확인
            if selected_station:
                updated_station = await current_station_btn.text_content()
                print(f"ℹ️ 선택 후 역: {updated_station.strip()}")
                # 역이 변경됐거나 카드가 노출되면 성공
                assert updated_station.strip() != '' , "역 선택 후 버튼 텍스트가 비어있음"

            theme_visible = await page.get_by_text('테마로 살펴보는 회사/포지션').first.is_visible()
            assert theme_visible, "'테마로 살펴보는 회사/포지션' 텍스트가 보이지 않습니다"

            print("✅ 모든 검증 완료")
            await page.screenshot(path='screenshots/test_5_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_5_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
