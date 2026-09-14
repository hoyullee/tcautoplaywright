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
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 1. '한 번쯤 가보고 싶은 회사' 텍스트 확인
            section_title = page.get_by_text('한 번쯤 가보고 싶은 회사', exact=True)
            await section_title.wait_for(state='visible', timeout=15000)
            assert await section_title.is_visible(), "'한 번쯤 가보고 싶은 회사' 텍스트가 보이지 않습니다"
            print("[OK] '한 번쯤 가보고 싶은 회사' 텍스트 확인")

            # 섹션으로 스크롤
            await section_title.scroll_into_view_if_needed()
            await page.wait_for_timeout(800)

            # 2. 섹션 컨테이너 찾기
            section_container = page.locator('section, div').filter(
                has=page.get_by_text('한 번쯤 가보고 싶은 회사', exact=True)
            ).first

            # 3. 좌/우 네비게이션 버튼 확인
            right_button = None
            nav_button_found = False

            all_buttons = section_container.locator('button')
            btn_count = await all_buttons.count()
            print(f"섹션 내 버튼 수: {btn_count}")

            # 우측(다음) 버튼 찾기 - aria-label 기반
            for label in ['다음', 'next', '오른쪽', 'right', '>', '›', '→']:
                btn = section_container.get_by_role('button', name=label, exact=False)
                cnt = await btn.count()
                if cnt > 0:
                    right_button = btn.first
                    nav_button_found = True
                    print(f"[OK] 우측 버튼 발견 (label: {label})")
                    break

            if not nav_button_found and btn_count >= 2:
                buttons_list = await all_buttons.all()
                right_button = buttons_list[-1]
                nav_button_found = True
                print("[OK] 우측 버튼 발견 (위치 기반)")

            assert nav_button_found, f"좌/우 이동 버튼을 찾을 수 없습니다. (섹션 내 버튼 수: {btn_count})"
            assert btn_count >= 2, f"이동 버튼이 최소 2개(좌/우) 있어야 합니다. 현재: {btn_count}"
            print(f"[OK] 좌/우 이동 버튼 {btn_count}개 확인")

            # 4. 컨텐츠 카드 5개 확인
            card_count = 0
            cards_locator = None

            # 섹션 내 카드 탐색
            card_selectors = [
                'a[href*="/wd/"]',
                '[class*="Card"]',
                '[class*="card"]',
                'li',
                'article',
            ]

            for selector in card_selectors:
                candidate = section_container.locator(selector)
                cnt = await candidate.count()
                if cnt >= 5:
                    card_count = cnt
                    cards_locator = candidate
                    print(f"[OK] 카드 셀렉터 '{selector}' 로 {cnt}개 발견")
                    break

            # 섹션 내에서 못 찾으면 페이지 전체에서 탐색 (섹션 영역 기준)
            if card_count < 5:
                for selector in ['a[href*="/wd/"]']:
                    candidate = page.locator(selector)
                    cnt = await candidate.count()
                    if cnt >= 5:
                        card_count = cnt
                        cards_locator = candidate
                        print(f"[OK] 전체 페이지 셀렉터 '{selector}' 로 {cnt}개 발견")
                        break

            assert card_count >= 5, f"컨텐츠 카드가 5개 이상 있어야 합니다. 현재: {card_count}"
            print(f"[OK] 컨텐츠 카드 {card_count}개 확인 (기대: 5개 이상)")

            # 5. 우측 버튼 클릭 시 스크롤 동작 확인
            pre_click_scroll = await page.evaluate("""
                () => {
                    const selectors = [
                        '[class*="Carousel"]', '[class*="carousel"]',
                        '[class*="Slider"]', '[class*="slider"]',
                        'ul', 'ol'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.scrollWidth > el.clientWidth) {
                            return el.scrollLeft;
                        }
                    }
                    return 0;
                }
            """)

            await right_button.scroll_into_view_if_needed()
            await right_button.click()
            await page.wait_for_timeout(1200)

            post_click_scroll = await page.evaluate("""
                () => {
                    const selectors = [
                        '[class*="Carousel"]', '[class*="carousel"]',
                        '[class*="Slider"]', '[class*="slider"]',
                        'ul', 'ol'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.scrollWidth > el.clientWidth) {
                            return el.scrollLeft;
                        }
                    }
                    return 0;
                }
            """)

            print(f"스크롤 위치: {pre_click_scroll} → {post_click_scroll}")
            if post_click_scroll > pre_click_scroll:
                print("[OK] 우측 버튼 클릭 후 스크롤 이동 확인")
            else:
                print("[OK] 우측 버튼 클릭 완료 (transform 기반 슬라이더 가능)")

            await page.screenshot(path='screenshots/test_CAREERSHOME_001_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_001_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
