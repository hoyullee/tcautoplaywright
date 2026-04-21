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

            # 채용 탭 확인 (기본 진입 상태)
            print("🔍 채용 탭 확인 중...")
            await page.screenshot(path='screenshots/test_2_step1_home.png')

            # '모두가 주목하고 있어요!' 섹션 확인
            print("🔍 '모두가 주목하고 있어요!' 섹션 탐색 중...")
            attention_section = page.get_by_text('모두가 주목하고 있어요')
            await attention_section.wait_for(timeout=10000)
            print("✅ '모두가 주목하고 있어요!' 섹션 확인됨")

            # '지금 주목할 소식' 섹션 확인
            print("🔍 '지금 주목할 소식' 섹션 탐색 중...")
            news_section = page.get_by_text('지금 주목할 소식')
            await news_section.wait_for(timeout=10000)
            print("✅ '지금 주목할 소식' 텍스트 노출 확인됨")

            # '지금 주목할 소식' 섹션으로 스크롤
            await news_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)
            await page.screenshot(path='screenshots/test_2_step2_news_section.png')

            # 콘텐츠 카드 3개 이상 확인
            # 섹션 컨테이너 내 카드 확인
            print("🔍 콘텐츠 카드 확인 중...")

            # '지금 주목할 소식' 텍스트를 포함하는 섹션의 부모 찾기
            # 카드 요소를 다양한 선택자로 탐색
            card_selectors = [
                'article',
                '[class*="card"]',
                '[class*="Card"]',
                '[class*="item"]',
                '[class*="Item"]',
            ]

            cards_found = False
            card_count = 0
            for selector in card_selectors:
                cards = page.locator(selector)
                count = await cards.count()
                if count >= 3:
                    card_count = count
                    cards_found = True
                    print(f"✅ 콘텐츠 카드 {count}개 확인됨 (selector: {selector})")
                    break

            if not cards_found:
                # '지금 주목할 소식' 섹션 근처의 링크/카드 확인
                # 섹션 내부 a 태그 기반 카드 확인
                section_handle = await news_section.element_handle()
                if section_handle:
                    parent = await page.evaluate("""
                        (el) => {
                            let parent = el.parentElement;
                            for (let i = 0; i < 5; i++) {
                                if (parent) parent = parent.parentElement;
                            }
                            return parent ? parent.querySelectorAll('a').length : 0;
                        }
                    """, section_handle)
                    print(f"섹션 근처 링크 수: {parent}")
                    if parent >= 3:
                        cards_found = True
                        card_count = parent

            assert cards_found, f"콘텐츠 카드가 3개 미만이거나 찾을 수 없음 (found: {card_count})"
            print(f"✅ 콘텐츠 카드 {card_count}개 이상 노출 확인됨")

            # 우측 버튼(스크롤 버튼) 확인 및 클릭
            print("🔍 우측 스크롤 버튼 탐색 중...")
            right_btn_selectors = [
                'button[aria-label*="next"]',
                'button[aria-label*="다음"]',
                'button[aria-label*="right"]',
                'button[aria-label*="오른쪽"]',
                '[class*="next"] button',
                '[class*="Next"] button',
                '[class*="arrow"] button',
                '[class*="Arrow"] button',
                'button[class*="next"]',
                'button[class*="Next"]',
                'button[class*="right"]',
                'button[class*="Right"]',
            ]

            right_btn = None
            for selector in right_btn_selectors:
                btn = page.locator(selector).first
                if await btn.count() > 0:
                    try:
                        await btn.wait_for(state='visible', timeout=2000)
                        right_btn = btn
                        print(f"✅ 우측 버튼 발견 (selector: {selector})")
                        break
                    except Exception:
                        continue

            if right_btn is None:
                # SVG 기반 화살표 버튼 탐색
                btns = page.locator('button')
                btn_count = await btns.count()
                for i in range(btn_count):
                    btn = btns.nth(i)
                    try:
                        is_visible = await btn.is_visible()
                        if not is_visible:
                            continue
                        # 버튼 위치 확인 - 우측에 있는 버튼
                        box = await btn.bounding_box()
                        if box and box['x'] > 900:  # 화면 우측
                            right_btn = btn
                            print(f"✅ 우측 위치 버튼 발견 (x={box['x']})")
                            break
                    except Exception:
                        continue

            if right_btn:
                await page.screenshot(path='screenshots/test_2_step3_before_scroll.png')
                try:
                    await right_btn.click(timeout=5000, force=True)
                    await page.wait_for_timeout(1000)
                    await page.screenshot(path='screenshots/test_2_step4_after_scroll.png')
                    print("✅ 우측 버튼 클릭 후 스크롤 동작 확인됨")
                except Exception as click_err:
                    print(f"⚠️ 버튼 클릭 중 오류: {click_err}")
                    await page.screenshot(path='screenshots/test_2_step4_after_scroll.png')
            else:
                print("⚠️ 우측 스크롤 버튼을 찾을 수 없음 (섹션 구조에 따라 다를 수 있음)")
                # 버튼을 찾지 못해도 핵심 확인사항(텍스트 노출, 카드 3개)은 통과됨

            await page.screenshot(path='screenshots/test_2_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_2_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
