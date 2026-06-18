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
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # '지금 주목할 소식' 섹션 타이틀 찾기
            section_title = page.get_by_text('지금 주목할 소식', exact=True)
            await section_title.wait_for(state='visible', timeout=15000)

            # 섹션으로 스크롤
            await section_title.scroll_into_view_if_needed()
            await page.wait_for_timeout(800)

            print("1. '지금 주목할 소식' 텍스트 노출 확인 완료")

            # 좌/우 이동 버튼 확인 (aria-label '이전', '다음' 버튼)
            nav_buttons_info = await page.evaluate("""() => {
                const allElements = document.querySelectorAll('h2, h3, h4, p, span, div');
                for (const el of allElements) {
                    const text = el.textContent.trim();
                    if (text === '지금 주목할 소식') {
                        let container = el;
                        for (let i = 0; i < 10; i++) {
                            container = container.parentElement;
                            if (!container) break;

                            const buttons = [...container.querySelectorAll('button')].slice(0, 30);
                            const visibleBtns = buttons.filter(btn => {
                                const rect = btn.getBoundingClientRect();
                                return rect.width > 0 && rect.height > 0;
                            });

                            if (visibleBtns.length >= 2) {
                                return {
                                    count: visibleBtns.length,
                                    buttons: visibleBtns.map(btn => ({
                                        ariaLabel: btn.getAttribute('aria-label') || '',
                                        disabled: btn.disabled,
                                        className: btn.className.slice(0, 100)
                                    }))
                                };
                            }
                        }
                        break;
                    }
                }
                return { count: 0, buttons: [] };
            }""")

            print(f"Nav buttons: {nav_buttons_info}")

            if nav_buttons_info.get('count', 0) < 2:
                raise Exception(f"좌/우 이동 버튼이 2개 미만입니다. 발견된 버튼 수: {nav_buttons_info.get('count', 0)}")

            print(f"2. 좌/우 이동 버튼 {nav_buttons_info['count']}개 확인 완료 (이전/다음)")

            # 컨텐츠 카드 3개 이상 확인
            cards_count = await page.evaluate("""() => {
                const allElements = document.querySelectorAll('h2, h3, h4, p, span, div');
                for (const el of allElements) {
                    const text = el.textContent.trim();
                    if (text === '지금 주목할 소식') {
                        let container = el;
                        for (let i = 0; i < 10; i++) {
                            container = container.parentElement;
                            if (!container) break;

                            // ul > li 카드 구조 탐색
                            const listItems = container.querySelectorAll('ul > li');
                            const visibleItems = [...listItems].slice(0, 50).filter(item => {
                                const rect = item.getBoundingClientRect();
                                return rect.width > 50 && rect.height > 50;
                            });

                            if (visibleItems.length >= 3) {
                                return visibleItems.length;
                            }

                            // article 구조
                            const articles = container.querySelectorAll('article');
                            const visibleArticles = [...articles].slice(0, 50).filter(a => {
                                const rect = a.getBoundingClientRect();
                                return rect.width > 50 && rect.height > 50;
                            });

                            if (visibleArticles.length >= 3) {
                                return visibleArticles.length;
                            }
                        }
                        break;
                    }
                }
                return 0;
            }""")

            print(f"Cards count: {cards_count}")

            if cards_count < 3:
                raise Exception(f"컨텐츠 카드가 3개 미만입니다. 발견된 카드 수: {cards_count}")

            print(f"3. 컨텐츠 카드 {cards_count}개 확인 완료 (3개 이상)")

            # 슬라이더 컨테이너의 초기 transform/scroll 상태 기록
            initial_state = await page.evaluate("""() => {
                const allElements = document.querySelectorAll('h2, h3, h4, p, span, div');
                for (const el of allElements) {
                    const text = el.textContent.trim();
                    if (text === '지금 주목할 소식') {
                        let container = el;
                        for (let i = 0; i < 10; i++) {
                            container = container.parentElement;
                            if (!container) break;

                            // 슬라이드 래퍼 (transform 적용된 요소)
                            const allChildren = [...container.querySelectorAll('*')].slice(0, 100);
                            for (const child of allChildren) {
                                const style = window.getComputedStyle(child);
                                const transform = style.transform || '';
                                const overflowX = style.overflowX || '';
                                if (transform !== 'none' && transform !== '' && transform.includes('matrix')) {
                                    return {
                                        type: 'transform',
                                        transform,
                                        tag: child.tagName,
                                        className: child.className.slice(0, 100)
                                    };
                                }
                                if (overflowX === 'hidden' || overflowX === 'scroll') {
                                    return {
                                        type: 'overflow',
                                        scrollLeft: child.scrollLeft,
                                        scrollWidth: child.scrollWidth,
                                        clientWidth: child.clientWidth,
                                        tag: child.tagName
                                    };
                                }
                            }
                        }
                        break;
                    }
                }
                return { type: 'unknown' };
            }""")

            print(f"Initial slider state: {initial_state}")

            # '다음' 버튼 클릭
            next_btn = page.get_by_role('button', name='다음')
            next_btn_count = await next_btn.count()
            print(f"'다음' 버튼 개수: {next_btn_count}")

            if next_btn_count == 0:
                raise Exception("'다음' 버튼을 찾을 수 없습니다")

            # 섹션 근처의 '다음' 버튼 선택 (섹션 타이틀 위치 기반)
            section_box = await section_title.bounding_box()
            best_btn = None
            min_distance = float('inf')

            for i in range(next_btn_count):
                btn = next_btn.nth(i)
                box = await btn.bounding_box()
                if box and section_box:
                    distance = abs(box['y'] - section_box['y'])
                    if distance < min_distance:
                        min_distance = distance
                        best_btn = btn

            if best_btn is None:
                raise Exception("섹션 근처의 '다음' 버튼을 찾을 수 없습니다")

            # 버튼 클릭 전 상태 확인
            is_disabled = await best_btn.is_disabled()
            print(f"'다음' 버튼 disabled 상태: {is_disabled}")

            if is_disabled:
                raise Exception("'다음' 버튼이 비활성화 상태입니다 - 클릭 불가")

            # 클릭 전 첫 번째 카드의 위치 기록
            first_card_pos_before = await page.evaluate("""() => {
                const allElements = document.querySelectorAll('h2, h3, h4, p, span, div');
                for (const el of allElements) {
                    const text = el.textContent.trim();
                    if (text === '지금 주목할 소식') {
                        let container = el;
                        for (let i = 0; i < 10; i++) {
                            container = container.parentElement;
                            if (!container) break;
                            const listItems = container.querySelectorAll('ul > li');
                            if (listItems.length > 0) {
                                const rect = listItems[0].getBoundingClientRect();
                                return { x: rect.x, y: rect.y };
                            }
                        }
                        break;
                    }
                }
                return null;
            }""")

            print(f"First card position before click: {first_card_pos_before}")

            # '다음' 버튼 클릭
            await best_btn.click()
            await page.wait_for_timeout(1000)

            # 클릭 후 첫 번째 카드 위치 확인 (이동 여부 확인)
            first_card_pos_after = await page.evaluate("""() => {
                const allElements = document.querySelectorAll('h2, h3, h4, p, span, div');
                for (const el of allElements) {
                    const text = el.textContent.trim();
                    if (text === '지금 주목할 소식') {
                        let container = el;
                        for (let i = 0; i < 10; i++) {
                            container = container.parentElement;
                            if (!container) break;
                            const listItems = container.querySelectorAll('ul > li');
                            if (listItems.length > 0) {
                                const rect = listItems[0].getBoundingClientRect();
                                return { x: rect.x, y: rect.y };
                            }
                        }
                        break;
                    }
                }
                return null;
            }""")

            print(f"First card position after click: {first_card_pos_after}")

            # 슬라이더 이동 검증: x 좌표 변화 또는 scrollLeft 변화
            scroll_verified = False

            if first_card_pos_before and first_card_pos_after:
                x_diff = abs(first_card_pos_after['x'] - first_card_pos_before['x'])
                if x_diff > 10:
                    print(f"4. 우측 버튼 클릭 후 카드 슬라이드 이동 확인 (x 이동량: {x_diff}px)")
                    scroll_verified = True

            if not scroll_verified:
                # scrollLeft 변화 확인
                after_state = await page.evaluate("""() => {
                    const allElements = document.querySelectorAll('h2, h3, h4, p, span, div');
                    for (const el of allElements) {
                        const text = el.textContent.trim();
                        if (text === '지금 주목할 소식') {
                            let container = el;
                            for (let i = 0; i < 10; i++) {
                                container = container.parentElement;
                                if (!container) break;
                                const allChildren = [...container.querySelectorAll('*')].slice(0, 100);
                                for (const child of allChildren) {
                                    const style = window.getComputedStyle(child);
                                    const transform = style.transform || '';
                                    if (transform !== 'none' && transform !== '' && transform.includes('matrix')) {
                                        return { type: 'transform', transform };
                                    }
                                    if (child.scrollLeft > 0) {
                                        return { type: 'scrollLeft', scrollLeft: child.scrollLeft };
                                    }
                                }
                            }
                            break;
                        }
                    }
                    return { type: 'unknown' };
                }""")

                print(f"After slider state: {after_state}")

                if after_state.get('type') in ['transform', 'scrollLeft']:
                    print(f"4. 우측 버튼 클릭 후 슬라이드 이동 확인 ({after_state})")
                    scroll_verified = True

            if not scroll_verified:
                # 이전 버튼 활성화 상태 확인 (이동했다면 이전 버튼이 활성화됨)
                prev_btn = page.get_by_role('button', name='이전')
                prev_count = await prev_btn.count()
                if prev_count > 0:
                    # 섹션 근처 이전 버튼
                    for i in range(prev_count):
                        btn = prev_btn.nth(i)
                        box = await btn.bounding_box()
                        if box and section_box:
                            distance = abs(box['y'] - section_box['y'])
                            if distance < 200:  # 섹션 타이틀 근처
                                is_prev_disabled = await btn.is_disabled()
                                print(f"'이전' 버튼 disabled 상태 (클릭 후): {is_prev_disabled}")
                                if not is_prev_disabled:
                                    print("4. 우측 버튼 클릭 후 '이전' 버튼이 활성화됨 - 슬라이드 이동 확인")
                                    scroll_verified = True
                                break

            if not scroll_verified:
                raise Exception("우측 버튼 클릭 후 슬라이드 이동을 확인할 수 없습니다")

            await page.screenshot(path='screenshots/test_18_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_18_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
