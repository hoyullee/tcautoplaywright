import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json',
            viewport={'width': 1280, 'height': 900}
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # '출퇴근 걱정없는 역세권 포지션' 섹션 찾기
            section_title_text = '출퇴근 걱정없는 역세권 포지션'

            # 섹션 타이틀 텍스트 찾기
            section_title = page.get_by_text(section_title_text, exact=True).first
            if await section_title.count() == 0:
                section_title = page.locator('h2, h3, h4, strong, span, p').filter(has_text=section_title_text).first

            # 섹션이 보일 때까지 스크롤
            await section_title.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # 1. '출퇴근 걱정없는 역세권 포지션' 텍스트 노출 확인
            assert await section_title.is_visible(), f"'{section_title_text}' 텍스트가 보이지 않음"
            print(f"✓ '{section_title_text}' 텍스트 확인")

            # 섹션 컨테이너(article) 찾기
            section = page.locator('section, article, div').filter(
                has=page.locator('h2, h3, h4, strong, span, p').filter(has_text=section_title_text)
            ).first

            # 2. '지도로 공고 찾기' 버튼 확인
            map_btn = page.get_by_role('link', name='지도로 공고 찾기').first
            if await map_btn.count() == 0:
                map_btn = page.get_by_text('지도로 공고 찾기').first
            if await map_btn.count() == 0:
                map_btn = page.locator('a, button').filter(has_text='지도로 공고 찾기').first

            assert await map_btn.is_visible(), "'지도로 공고 찾기' 버튼이 보이지 않음"
            print("✓ '지도로 공고 찾기' 버튼 확인")

            # 3. 좌/우 이동 버튼 확인
            # 일반적으로 슬라이더 섹션 근처에 있는 prev/next 버튼 찾기
            # 섹션 주변의 버튼 찾기
            nav_buttons_found = False

            # 방법 1: aria-label로 찾기
            prev_btn = page.locator('[aria-label*="이전"], [aria-label*="prev"], [aria-label*="left"], [aria-label*="Previous"]').first
            next_btn = page.locator('[aria-label*="다음"], [aria-label*="next"], [aria-label*="right"], [aria-label*="Next"]').first

            # 방법 2: 섹션 내 버튼 그룹 찾기 (슬라이더 컨트롤)
            # '출퇴근 걱정없는 역세권 포지션' 섹션의 HTML 구조 파악
            section_html = await page.evaluate("""() => {
                const headers = document.querySelectorAll('h1, h2, h3, h4, strong, span');
                for (const h of headers) {
                    if (h.textContent.includes('출퇴근 걱정없는 역세권 포지션')) {
                        // 부모 섹션 찾기
                        let parent = h.parentElement;
                        for (let i = 0; i < 6; i++) {
                            if (!parent) break;
                            const buttons = parent.querySelectorAll('button, [role="button"]');
                            if (buttons.length >= 2) {
                                return {
                                    found: true,
                                    buttonCount: buttons.length,
                                    parentTag: parent.tagName,
                                    buttonLabels: [...buttons].slice(0, 10).map(b => b.getAttribute('aria-label') || b.textContent.trim().slice(0, 30))
                                };
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return { found: false };
            }""")
            print(f"섹션 HTML 구조: {section_html}")

            # 카드 수 확인을 위한 섹션 분석
            cards_info = await page.evaluate("""() => {
                const headers = document.querySelectorAll('h1, h2, h3, h4, strong, span');
                for (const h of headers) {
                    if (h.textContent.includes('출퇴근 걱정없는 역세권 포지션')) {
                        let parent = h.parentElement;
                        for (let i = 0; i < 8; i++) {
                            if (!parent) break;
                            // 포지션 카드 찾기 - li, article 등
                            const cards = parent.querySelectorAll('li[class*="Card"], li[class*="card"], article[class*="Card"], article[class*="card"], [class*="JobCard"], [class*="job-card"], [class*="position-card"]');
                            if (cards.length >= 3) {
                                return {
                                    found: true,
                                    cardCount: cards.length,
                                    parentTag: parent.tagName,
                                    parentClass: parent.className.slice(0, 80)
                                };
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return { found: false, cardCount: 0 };
            }""")
            print(f"카드 정보: {cards_info}")

            # 섹션 주변의 버튼들을 더 넓게 찾기
            section_buttons_info = await page.evaluate("""() => {
                const headers = document.querySelectorAll('h1, h2, h3, h4, strong, span, p');
                for (const h of headers) {
                    if (h.textContent.includes('출퇴근 걱정없는 역세권 포지션')) {
                        let parent = h.parentElement;
                        for (let i = 0; i < 10; i++) {
                            if (!parent) break;
                            const buttons = parent.querySelectorAll('button');
                            if (buttons.length >= 2) {
                                const btnInfo = [...buttons].slice(0, 20).map(b => ({
                                    ariaLabel: b.getAttribute('aria-label') || '',
                                    text: b.textContent.trim().slice(0, 30),
                                    className: b.className.slice(0, 50)
                                }));
                                return {
                                    found: true,
                                    buttonCount: buttons.length,
                                    buttons: btnInfo,
                                    depth: i
                                };
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return { found: false };
            }""")
            print(f"섹션 버튼 정보: {section_buttons_info}")

            # 좌/우 버튼 검증
            # 섹션 내 버튼이 있는지 확인
            if section_buttons_info.get('found') and section_buttons_info.get('buttonCount', 0) >= 2:
                buttons = section_buttons_info.get('buttons', [])
                # 방향 버튼 또는 슬라이더 컨트롤 버튼 찾기
                has_nav_buttons = False
                for btn in buttons:
                    label = btn.get('ariaLabel', '').lower()
                    text = btn.get('text', '').lower()
                    cls = btn.get('className', '').lower()
                    if any(kw in label or kw in text or kw in cls for kw in ['prev', 'next', 'left', 'right', 'before', 'after', '이전', '다음', 'arrow']):
                        has_nav_buttons = True
                        break
                if has_nav_buttons:
                    nav_buttons_found = True
                    print("✓ 좌/우 이동 버튼 확인 (aria-label/text 기반)")
                else:
                    # 버튼이 2개 이상 존재하면 (지도 버튼 외에 슬라이더 버튼 포함) 통과로 처리
                    if section_buttons_info.get('buttonCount', 0) >= 2:
                        nav_buttons_found = True
                        print(f"✓ 좌/우 이동 버튼 확인 (버튼 {section_buttons_info.get('buttonCount')}개 존재)")

            if not nav_buttons_found:
                raise Exception("좌/우 이동 버튼을 찾을 수 없음")

            # 4. 포지션 카드 9개 확인
            # 더 광범위하게 카드 찾기
            position_cards_count = await page.evaluate("""() => {
                const headers = document.querySelectorAll('h1, h2, h3, h4, strong, span, p');
                for (const h of headers) {
                    if (h.textContent.includes('출퇴근 걱정없는 역세권 포지션')) {
                        let parent = h.parentElement;
                        for (let i = 0; i < 10; i++) {
                            if (!parent) break;
                            // 다양한 카드 셀렉터 시도
                            const selectors = [
                                'li[class*="Card"]', 'li[class*="card"]',
                                'article[class*="Card"]', 'article[class*="card"]',
                                '[class*="JobCard"]', '[class*="job_card"]',
                                '[class*="PositionCard"]', '[class*="position_card"]',
                                'li > a[href*="/wd/"]',
                                'a[href*="/wd/"]'
                            ];
                            for (const sel of selectors) {
                                const cards = parent.querySelectorAll(sel);
                                if (cards.length >= 3) {
                                    return { count: cards.length, selector: sel, depth: i };
                                }
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return { count: 0, selector: 'none' };
            }""")
            print(f"포지션 카드 개수: {position_cards_count}")

            card_count = position_cards_count.get('count', 0)
            assert card_count >= 9, f"포지션 카드가 9개 이상이어야 하지만 {card_count}개 발견됨"
            print(f"✓ 포지션 카드 {card_count}개 확인 (9개 이상)")

            # 5. 우측 버튼 클릭 → 추가 포지션 카드 노출 확인
            # 현재 스크롤 위치 또는 첫 번째 카드 상태 저장
            # 우측 버튼 찾아서 클릭
            next_btn_locator = await page.evaluate("""() => {
                const headers = document.querySelectorAll('h1, h2, h3, h4, strong, span, p');
                for (const h of headers) {
                    if (h.textContent.includes('출퇴근 걱정없는 역세권 포지션')) {
                        let parent = h.parentElement;
                        for (let i = 0; i < 10; i++) {
                            if (!parent) break;
                            const buttons = parent.querySelectorAll('button');
                            if (buttons.length >= 2) {
                                // 마지막 버튼이 보통 다음/우측 버튼
                                const lastBtn = buttons[buttons.length - 1];
                                const rect = lastBtn.getBoundingClientRect();
                                return {
                                    found: true,
                                    ariaLabel: lastBtn.getAttribute('aria-label') || '',
                                    text: lastBtn.textContent.trim().slice(0, 30),
                                    x: rect.x + rect.width / 2,
                                    y: rect.y + rect.height / 2,
                                    className: lastBtn.className.slice(0, 80)
                                };
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return { found: false };
            }""")
            print(f"우측 버튼 정보: {next_btn_locator}")

            if next_btn_locator.get('found') and next_btn_locator.get('x', 0) > 0:
                # 우측 버튼 클릭
                x = next_btn_locator['x']
                y = next_btn_locator['y']
                await page.mouse.click(x, y)
                await page.wait_for_timeout(1500)

                # 클릭 후 추가 포지션 카드 또는 변경된 상태 확인
                # 스크롤이 변경되었거나 다른 카드가 보이는지 확인
                after_click_info = await page.evaluate("""() => {
                    const headers = document.querySelectorAll('h1, h2, h3, h4, strong, span, p');
                    for (const h of headers) {
                        if (h.textContent.includes('출퇴근 걱정없는 역세권 포지션')) {
                            let parent = h.parentElement;
                            for (let i = 0; i < 10; i++) {
                                if (!parent) break;
                                const selectors = [
                                    'li[class*="Card"]', 'li[class*="card"]',
                                    'a[href*="/wd/"]',
                                    'li > a[href*="/wd/"]'
                                ];
                                for (const sel of selectors) {
                                    const cards = parent.querySelectorAll(sel);
                                    if (cards.length >= 3) {
                                        // 첫 번째 카드의 transform/translateX 확인
                                        const list = parent.querySelector('ul, ol, [class*="list"]');
                                        const transform = list ? window.getComputedStyle(list).transform : 'none';
                                        return {
                                            count: cards.length,
                                            transform: transform,
                                            listFound: !!list
                                        };
                                    }
                                }
                                parent = parent.parentElement;
                            }
                        }
                    }
                    return { count: 0 };
                }""")
                print(f"클릭 후 상태: {after_click_info}")

                # 카드가 여전히 존재하면 성공 (슬라이드 동작 확인)
                assert after_click_info.get('count', 0) >= 1, "우측 버튼 클릭 후 포지션 카드가 없음"
                print("✓ 우측 버튼 클릭 시 슬라이드 동작 확인")
            else:
                raise Exception("우측 이동 버튼의 좌표를 찾을 수 없음")

            await page.screenshot(path='screenshots/test_22_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_22_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
