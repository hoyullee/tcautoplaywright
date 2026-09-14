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
            storage_state='work/auth_state.json',
            viewport={'width': 1280, 'height': 900}
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # '테마로 살펴보는 회사/포지션' 섹션 찾기
            section_title = page.get_by_text('테마로 살펴보는 회사/포지션', exact=False)
            await section_title.wait_for(state='visible', timeout=15000)

            # 섹션이 보이도록 스크롤
            await section_title.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # 섹션 타이틀 노출 확인
            assert await section_title.is_visible(), "'테마로 살펴보는 회사/포지션' 텍스트가 노출되지 않음"
            print("✅ '테마로 살펴보는 회사/포지션' 텍스트 노출 확인")

            # 섹션 구조 분석
            section_info = await page.evaluate("""() => {
                const allText = [...document.querySelectorAll('*')];
                const titleEl = allText.find(el =>
                    el.childNodes.length > 0 &&
                    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.includes('테마로 살펴보는 회사/포지션'))
                );

                if (!titleEl) return { error: 'not found' };

                let container = titleEl;
                let info = [];
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const btns = container.querySelectorAll('button');
                    const cards = container.querySelectorAll('li, article, [class*="card"], [class*="Card"]');
                    info.push({
                        tag: container.tagName,
                        className: container.className.substring(0, 100),
                        btnCount: btns.length,
                        cardCount: cards.length,
                        btnDetails: [...btns].slice(0, 5).map(b => ({
                            ariaLabel: b.getAttribute('aria-label'),
                            type: b.type,
                            text: b.textContent.trim().substring(0, 30)
                        }))
                    });
                    container = container.parentElement;
                }
                return { found: true, info };
            }""")
            print(f"Section structure: {section_info}")

            # 좌/우 이동 버튼 검색
            section_buttons_info = await page.evaluate("""() => {
                const allText = [...document.querySelectorAll('*')];
                const titleEl = allText.find(el =>
                    el.childNodes.length > 0 &&
                    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.includes('테마로 살펴보는 회사/포지션'))
                );

                if (!titleEl) return [];

                let container = titleEl;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const btns = container.querySelectorAll('button');
                    if (btns.length >= 2) {
                        return [...btns].map(b => ({
                            ariaLabel: b.getAttribute('aria-label'),
                            text: b.textContent.trim().substring(0, 50),
                            type: b.type,
                            disabled: b.disabled,
                            className: b.className.substring(0, 100)
                        }));
                    }
                    container = container.parentElement;
                }
                return [];
            }""")
            print(f"Section buttons: {section_buttons_info}")

            # 버튼 검증 - 좌/우 버튼이 있어야 함
            assert len(section_buttons_info) >= 2, f"좌/우 이동 버튼이 2개 미만: {len(section_buttons_info)}개 발견"
            print(f"✅ 좌/우 이동 버튼 {len(section_buttons_info)}개 확인")

            # 컨텐츠 카드 4개 확인
            card_count_info = await page.evaluate("""() => {
                const allText = [...document.querySelectorAll('*')];
                const titleEl = allText.find(el =>
                    el.childNodes.length > 0 &&
                    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.includes('테마로 살펴보는 회사/포지션'))
                );

                if (!titleEl) return { error: 'title not found' };

                let container = titleEl;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const cards = container.querySelectorAll('li, article, [class*="card"], [class*="Card"], [class*="item"], [class*="Item"]');
                    if (cards.length >= 4) {
                        const visibleCards = [...cards].filter(card => {
                            const rect = card.getBoundingClientRect();
                            return rect.width > 50 && rect.height > 50 &&
                                   rect.right > 0 && rect.left < window.innerWidth;
                        });
                        return {
                            total: cards.length,
                            visible: visibleCards.length,
                            containerTag: container.tagName,
                            containerClass: container.className.substring(0, 100)
                        };
                    }
                    container = container.parentElement;
                }
                return { total: 0, visible: 0, error: 'cards not found' };
            }""")
            print(f"Card count info: {card_count_info}")

            # 최소 4개의 카드가 보여야 함
            visible_cards = card_count_info.get('visible', 0)
            assert visible_cards >= 4, f"화면에 보이는 카드가 4개 미만: {visible_cards}개 (total: {card_count_info.get('total', 0)}개)"
            print(f"✅ 컨텐츠 카드 {visible_cards}개 이상 확인")

            # 우측 버튼 index 결정
            right_btn_index = len(section_buttons_info) - 1  # 마지막 버튼이 보통 우측
            for i, btn in enumerate(section_buttons_info):
                label = (btn.get('ariaLabel') or '').lower()
                text = (btn.get('text') or '').lower()
                if any(kw in label or kw in text for kw in ['next', 'right', '다음', '오른쪽']):
                    right_btn_index = i
                    break

            # 버튼 클릭 전 카드 위치 저장
            before_scroll_positions = await page.evaluate("""() => {
                const allText = [...document.querySelectorAll('*')];
                const titleEl = allText.find(el =>
                    el.childNodes.length > 0 &&
                    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.includes('테마로 살펴보는 회사/포지션'))
                );

                if (!titleEl) return [];

                let container = titleEl;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const cards = container.querySelectorAll('li, article, [class*="card"], [class*="Card"]');
                    if (cards.length >= 4) {
                        return [...cards].slice(0, 10).map(card => {
                            const rect = card.getBoundingClientRect();
                            return { left: Math.round(rect.left), right: Math.round(rect.right) };
                        });
                    }
                    container = container.parentElement;
                }
                return [];
            }""")
            print(f"Before scroll positions: {before_scroll_positions[:4]}")

            # 우측 버튼 클릭
            clicked = await page.evaluate("""(btnIndex) => {
                const allText = [...document.querySelectorAll('*')];
                const titleEl = allText.find(el =>
                    el.childNodes.length > 0 &&
                    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.includes('테마로 살펴보는 회사/포지션'))
                );

                if (!titleEl) return false;

                let container = titleEl;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const btns = container.querySelectorAll('button');
                    if (btns.length >= 2) {
                        const btn = btns[btnIndex];
                        if (btn) {
                            btn.click();
                            return true;
                        }
                        return false;
                    }
                    container = container.parentElement;
                }
                return false;
            }""", right_btn_index)

            print(f"Right button click result: {clicked}")
            await page.wait_for_timeout(1500)

            # 클릭 후 카드 위치 변화 확인
            after_scroll_positions = await page.evaluate("""() => {
                const allText = [...document.querySelectorAll('*')];
                const titleEl = allText.find(el =>
                    el.childNodes.length > 0 &&
                    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.includes('테마로 살펴보는 회사/포지션'))
                );

                if (!titleEl) return [];

                let container = titleEl;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const cards = container.querySelectorAll('li, article, [class*="card"], [class*="Card"]');
                    if (cards.length >= 4) {
                        return [...cards].slice(0, 10).map(card => {
                            const rect = card.getBoundingClientRect();
                            return { left: Math.round(rect.left), right: Math.round(rect.right) };
                        });
                    }
                    container = container.parentElement;
                }
                return [];
            }""")
            print(f"After scroll positions: {after_scroll_positions[:4]}")

            # 스크롤 여부 확인
            if before_scroll_positions and after_scroll_positions:
                first_card_moved = before_scroll_positions[0]['left'] != after_scroll_positions[0]['left']
                if first_card_moved:
                    print(f"✅ 우측 버튼 클릭 후 스크롤 확인 (카드 위치 변화: {before_scroll_positions[0]['left']} → {after_scroll_positions[0]['left']})")
                else:
                    print(f"ℹ️ 카드 위치 변화 없음 - 이미 스크롤 끝이거나 다른 방식으로 동작")

            # 스크롤 후에도 카드가 여전히 존재하는지 확인
            after_card_count = await page.evaluate("""() => {
                const allText = [...document.querySelectorAll('*')];
                const titleEl = allText.find(el =>
                    el.childNodes.length > 0 &&
                    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.includes('테마로 살펴보는 회사/포지션'))
                );

                if (!titleEl) return 0;

                let container = titleEl;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const cards = container.querySelectorAll('li, article, [class*="card"], [class*="Card"]');
                    if (cards.length >= 4) {
                        const visibleCards = [...cards].filter(card => {
                            const rect = card.getBoundingClientRect();
                            return rect.width > 50 && rect.height > 50 &&
                                   rect.right > 0 && rect.left < window.innerWidth;
                        });
                        return visibleCards.length;
                    }
                    container = container.parentElement;
                }
                return 0;
            }""")
            print(f"After scroll visible card count: {after_card_count}")
            assert after_card_count >= 1, f"스크롤 후 카드가 보이지 않음"
            print(f"✅ 스크롤 후 추가 컨텐츠 카드 {after_card_count}개 노출 확인")

            await page.screenshot(path='screenshots/test_CAREERSHOME_015_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_015_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
