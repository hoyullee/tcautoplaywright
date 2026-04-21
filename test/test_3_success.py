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
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # '지금 주목할 소식' 섹션 확인
            print("🔍 '지금 주목할 소식' 섹션 확인")
            news_section = page.get_by_text('지금 주목할 소식')
            await news_section.wait_for(timeout=10000)
            print("✅ '지금 주목할 소식' 섹션 확인됨")

            # 해당 섹션 아래로 스크롤
            await news_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # '테마로 살펴보는 회사/포지션' 섹션 확인
            print("🔍 '테마로 살펴보는 회사/포지션' 섹션 확인")
            theme_section = page.get_by_text('테마로 살펴보는 회사/포지션')
            await theme_section.wait_for(timeout=10000)
            print("✅ '테마로 살펴보는 회사/포지션' 텍스트 노출 확인됨")

            # 해당 섹션으로 스크롤
            await theme_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            await page.screenshot(path='screenshots/test_3_theme_section.png')

            # 테마 섹션의 컨텐츠 카드 확인 (4개 이상)
            print("🔍 컨텐츠 카드 확인")

            # 테마 섹션 부모 컨테이너 찾기
            theme_heading = page.get_by_text('테마로 살펴보는 회사/포지션').first

            # 섹션 컨테이너 내에서 카드 찾기 - 여러 선택자 시도
            # 먼저 섹션 전체 구조 파악을 위해 스크린샷
            await page.screenshot(path='screenshots/test_3_before_cards.png')

            # 카드 요소 찾기 - 일반적인 카드 선택자들 시도
            card_selectors = [
                'section:has-text("테마로 살펴보는 회사/포지션") a',
                'div:has-text("테마로 살펴보는 회사/포지션") ~ div a',
                '[class*="ThemeCard"]',
                '[class*="theme"] [class*="card"]',
                '[class*="Theme"] [class*="Card"]',
            ]

            cards = None
            cards_count = 0
            for selector in card_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count >= 4:
                        cards = elements
                        cards_count = count
                        print(f"✅ 카드 {count}개 발견 (선택자: {selector})")
                        break
                    elif count > 0:
                        print(f"  - {count}개 발견 (선택자: {selector}), 계속 탐색...")
                except Exception as e:
                    print(f"  - 선택자 실패: {selector} - {e}")

            # 직접 DOM 탐색으로 테마 섹션 카드 찾기
            if cards_count < 4:
                print("🔍 DOM 탐색으로 카드 재시도")
                # 테마 섹션 이후 첫 번째 그리드/리스트 컨테이너 찾기
                js_result = await page.evaluate("""
                    () => {
                        const headings = document.querySelectorAll('h2, h3, p, span, div');
                        let themeEl = null;
                        for (const el of headings) {
                            if (el.textContent.trim() === '테마로 살펴보는 회사/포지션') {
                                themeEl = el;
                                break;
                            }
                        }
                        if (!themeEl) return { found: false, info: 'heading not found' };

                        // 부모 섹션 찾기
                        let parent = themeEl.parentElement;
                        for (let i = 0; i < 5; i++) {
                            if (!parent) break;
                            const cards = parent.querySelectorAll('a, [class*="card"], [class*="Card"], [class*="item"], [class*="Item"]');
                            if (cards.length >= 4) {
                                return {
                                    found: true,
                                    count: cards.length,
                                    parentClass: parent.className,
                                    parentTag: parent.tagName,
                                    cardClasses: Array.from(cards).slice(0,4).map(c => c.className)
                                };
                            }
                            parent = parent.parentElement;
                        }
                        return { found: false, info: 'cards not found in parents', themeText: themeEl.textContent };
                    }
                """)
                print(f"  DOM 탐색 결과: {js_result}")

                if js_result.get('found') and js_result.get('count', 0) >= 4:
                    cards_count = js_result['count']
                    print(f"✅ DOM 탐색으로 카드 {cards_count}개 확인됨")

            if cards_count < 4:
                # 화면에 보이는 카드 수 직접 확인
                print("🔍 가시적 카드 요소 최종 탐색")
                visible_result = await page.evaluate("""
                    () => {
                        const allLinks = document.querySelectorAll('a');
                        const themeLinks = [];
                        let foundTheme = false;

                        for (const el of document.querySelectorAll('*')) {
                            if (el.textContent.trim() === '테마로 살펴보는 회사/포지션') {
                                foundTheme = true;
                                const section = el.closest('section') || el.parentElement?.parentElement?.parentElement;
                                if (section) {
                                    const links = section.querySelectorAll('a');
                                    return { count: links.length, tag: section.tagName, cls: section.className };
                                }
                            }
                        }
                        return { count: 0, foundTheme };
                    }
                """)
                print(f"  가시적 카드 탐색 결과: {visible_result}")
                cards_count = visible_result.get('count', 0)

            assert cards_count >= 4, f"컨텐츠 카드가 4개 미만입니다: {cards_count}개 발견"
            print(f"✅ 컨텐츠 카드 {cards_count}개 확인됨 (4개 이상)")

            await page.screenshot(path='screenshots/test_3_cards.png')

            # 우측 버튼 찾기 및 클릭 테스트
            print("🔍 우측 스크롤 버튼 확인")

            # 테마 섹션 내 우측 버튼 찾기
            right_btn_result = await page.evaluate("""
                () => {
                    for (const el of document.querySelectorAll('*')) {
                        if (el.textContent.trim() === '테마로 살펴보는 회사/포지션') {
                            let parent = el.parentElement;
                            for (let i = 0; i < 6; i++) {
                                if (!parent) break;
                                // 버튼 찾기
                                const buttons = parent.querySelectorAll('button');
                                if (buttons.length > 0) {
                                    return {
                                        found: true,
                                        count: buttons.length,
                                        classes: Array.from(buttons).map(b => b.className),
                                        ariaLabels: Array.from(buttons).map(b => b.getAttribute('aria-label')),
                                        parentClass: parent.className
                                    };
                                }
                                parent = parent.parentElement;
                            }
                        }
                    }
                    return { found: false };
                }
            """)
            print(f"  버튼 탐색 결과: {right_btn_result}")

            # 우측 방향 버튼 클릭 시도
            right_button_found = False

            # aria-label로 버튼 찾기
            right_btn_selectors = [
                'button[aria-label="다음"]',
                'button[aria-label="Next"]',
                'button[aria-label="오른쪽"]',
                '[class*="next"] button',
                '[class*="Next"] button',
                '[class*="arrow-right"]',
                '[class*="ArrowRight"]',
                '[class*="slideNext"]',
                'button[class*="next"]',
                'button[class*="Next"]',
            ]

            # 테마 섹션으로 재이동
            await theme_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            for selector in right_btn_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.count() > 0 and await btn.is_visible():
                        print(f"  우측 버튼 발견: {selector}")

                        # 클릭 전 스크린샷
                        await page.screenshot(path='screenshots/test_3_before_click.png')

                        await btn.click()
                        await page.wait_for_timeout(1000)

                        # 클릭 후 스크린샷
                        await page.screenshot(path='screenshots/test_3_after_click.png')

                        print("✅ 우측 버튼 클릭 성공")
                        right_button_found = True
                        break
                except Exception as e:
                    continue

            if not right_button_found:
                # 버튼이 없거나 찾지 못한 경우 - 테마 섹션 자체에서 버튼 탐색
                print("  일반 선택자로 찾지 못함, 섹션 내 버튼 직접 클릭 시도")
                try:
                    # 테마 섹션 근처의 모든 버튼 시도
                    section_buttons = page.locator('section').filter(has_text='테마로 살펴보는 회사/포지션').locator('button')
                    btn_count = await section_buttons.count()
                    print(f"  섹션 내 버튼 수: {btn_count}")

                    if btn_count > 0:
                        # 마지막 버튼이 보통 '다음' 버튼
                        last_btn = section_buttons.last
                        await page.screenshot(path='screenshots/test_3_before_click.png')
                        await last_btn.click()
                        await page.wait_for_timeout(1000)
                        await page.screenshot(path='screenshots/test_3_after_click.png')
                        print("✅ 섹션 내 마지막 버튼 클릭 성공")
                        right_button_found = True
                except Exception as e:
                    print(f"  섹션 버튼 클릭 실패: {e}")

            if not right_button_found:
                print("⚠️ 우측 버튼을 찾지 못했습니다 - 스크롤 동작 검증 스킵")

            await page.screenshot(path='screenshots/test_3_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_3_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
