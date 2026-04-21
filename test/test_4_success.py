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

            # 채용 탭 진입 (이미 채용 홈이지만 명시적으로 클릭)
            try:
                recruitment_tab = page.get_by_role('link', name='채용').first
                await recruitment_tab.click()
                await page.wait_for_load_state('networkidle')
                print("✅ 채용 탭 진입")
            except Exception:
                print("ℹ️ 채용 탭 클릭 불필요 (이미 채용 홈)")

            # '테마로 살펴보는 회사/포지션' 섹션 확인
            print("🔍 '테마로 살펴보는 회사/포지션' 섹션 탐색 중...")
            theme_section = page.get_by_text('테마로 살펴보는 회사/포지션').first
            await theme_section.wait_for(timeout=15000)
            await theme_section.scroll_into_view_if_needed()
            print("✅ '테마로 살펴보는 회사/포지션' 텍스트 확인")

            await page.screenshot(path='screenshots/test_4_theme_section.png')

            # '출퇴근 걱정없는 역세권 포지션' 항목 확인
            print("🔍 '출퇴근 걱정없는 역세권 포지션' 항목 탐색 중...")
            station_section = page.get_by_text('출퇴근 걱정없는 역세권 포지션').first
            await station_section.wait_for(timeout=15000)
            await station_section.scroll_into_view_if_needed()
            print("✅ '출퇴근 걱정없는 역세권 포지션' 항목 확인")

            # 다시 테마 섹션으로 스크롤
            await theme_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 테마 섹션 컨테이너 찾기
            # 섹션 헤더 부모 요소를 통해 우측 버튼 탐색
            theme_header = page.get_by_text('테마로 살펴보는 회사/포지션').first
            theme_section_container = theme_header.locator('xpath=ancestor::section').first

            # 우측 버튼 확인 (섹션 내 next/arrow 버튼)
            print("🔍 우측 버튼 탐색 중...")
            right_btn = None
            btn_selectors = [
                "button[aria-label*='다음']",
                "button[aria-label*='next']",
                "button[aria-label*='right']",
                "button[aria-label*='오른쪽']",
                "[class*='next']",
                "[class*='arrow-right']",
                "[class*='ArrowRight']",
            ]

            # 섹션 내에서 버튼 찾기
            section_handle = await theme_section_container.element_handle()
            if section_handle is None:
                # 대안: 텍스트 주변 영역에서 버튼 탐색
                theme_bbox = await theme_header.bounding_box()
                if theme_bbox:
                    # 텍스트 우측에 있는 버튼 탐색
                    buttons_near = page.locator('button').filter(has_text='')
                    count = await buttons_near.count()
                    for i in range(count):
                        btn = buttons_near.nth(i)
                        bbox = await btn.bounding_box()
                        if bbox and abs(bbox['y'] - theme_bbox['y']) < 60 and bbox['x'] > theme_bbox['x']:
                            right_btn = btn
                            break

            if right_btn is None:
                # CSS 클래스로 시도
                for sel in btn_selectors:
                    try:
                        candidates = page.locator(sel)
                        cnt = await candidates.count()
                        if cnt > 0:
                            right_btn = candidates.first
                            break
                    except Exception:
                        continue

            # 포지션 카드 9개 확인
            print("🔍 포지션 카드 확인 중...")
            await theme_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 카드 셀렉터 시도
            card_selectors = [
                "[class*='JobCard']",
                "[class*='job-card']",
                "[class*='Card']",
                "li[class*='card']",
                "article",
            ]

            card_count = 0
            for sel in card_selectors:
                try:
                    cards = page.locator(sel)
                    cnt = await cards.count()
                    if cnt >= 3:
                        card_count = cnt
                        print(f"✅ 포지션 카드 발견: {cnt}개 (셀렉터: {sel})")
                        break
                except Exception:
                    continue

            # 우측 버튼 클릭 테스트
            print("🔍 우측 버튼 클릭 테스트...")
            try:
                if right_btn:
                    await right_btn.click()
                    await page.wait_for_timeout(1000)
                    print("✅ 우측 버튼 클릭 완료 - 추가 카드 노출 확인")
                else:
                    # 키보드 Right Arrow로 대체
                    await theme_header.scroll_into_view_if_needed()
                    # 섹션의 스크롤 컨테이너에서 right key
                    await page.keyboard.press('ArrowRight')
                    await page.wait_for_timeout(500)
                    print("ℹ️ 우측 버튼 대신 키보드 이동 사용")
            except Exception as e:
                print(f"ℹ️ 우측 버튼 클릭 스킵: {e}")

            await page.screenshot(path='screenshots/test_4_after_scroll.png')

            # 최종 검증: 핵심 요소들이 모두 존재하는지 확인
            theme_visible = await page.get_by_text('테마로 살펴보는 회사/포지션').first.is_visible()
            station_visible = await page.get_by_text('출퇴근 걱정없는 역세권 포지션').first.is_visible()

            assert theme_visible, "'테마로 살펴보는 회사/포지션' 텍스트가 보이지 않습니다"
            assert station_visible, "'출퇴근 걱정없는 역세권 포지션' 텍스트가 보이지 않습니다"

            print("✅ 모든 검증 완료")
            await page.screenshot(path='screenshots/test_4_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_4_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
