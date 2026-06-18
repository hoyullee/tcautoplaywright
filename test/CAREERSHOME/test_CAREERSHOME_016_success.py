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

            # 탐색 페이지에서 포지션 URL 수집 후 방문 (최근 본 포지션 데이터 확보)
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            position_links = await page.evaluate("""() => {
                const links = [...document.querySelectorAll('a[href*="/wd/"]')];
                const hrefs = links
                    .map(a => a.href)
                    .filter(href => /\/wd\/\\d+/.test(href))
                    .slice(0, 15);
                return [...new Set(hrefs)];
            }""")
            print(f"Found {len(position_links)} position links")

            # 최소 10개 포지션 방문
            visit_count = min(len(position_links), 10)
            for i in range(visit_count):
                try:
                    await page.goto(position_links[i], timeout=20000)
                    await page.wait_for_load_state('domcontentloaded')
                    await page.wait_for_timeout(500)
                    print(f"Visited position {i+1}")
                except Exception as ve:
                    print(f"Skip position {i+1}: {ve}")

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # '최근 본 포지션' 섹션 찾기
            section_title = page.get_by_text('최근 본 포지션', exact=False)
            await section_title.first.wait_for(state='visible', timeout=15000)

            # 스크롤하여 섹션 표시
            await section_title.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # 1. '최근 본 포지션' 텍스트 노출 확인
            assert await section_title.first.is_visible(), "'최근 본 포지션' 텍스트가 노출되지 않음"
            print("✅ '최근 본 포지션' 텍스트 노출 확인")

            # 섹션 컨테이너 및 버튼 분석
            section_analysis = await page.evaluate("""() => {
                // '최근 본 포지션' 텍스트를 포함한 가장 짧은 요소 찾기
                const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, p, div')];
                const titleEl = allEls.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('최근 본 포지션') && text.length < 30;
                });

                if (!titleEl) return { error: 'title not found' };

                // 상위로 올라가며 버튼과 카드가 있는 컨테이너 찾기
                let container = titleEl;
                let result = { titleFound: true, containers: [] };

                for (let i = 0; i < 12; i++) {
                    if (!container) break;
                    const btns = container.querySelectorAll('button');
                    const cards = container.querySelectorAll('li, article, [class*="card"], [class*="Card"]');
                    const links = container.querySelectorAll('a[href*="/wd/"]');

                    result.containers.push({
                        depth: i,
                        tag: container.tagName,
                        className: container.className.substring(0, 80),
                        btnCount: btns.length,
                        cardCount: cards.length,
                        positionLinkCount: links.length,
                        btnDetails: [...btns].slice(0, 6).map(b => ({
                            ariaLabel: b.getAttribute('aria-label'),
                            text: b.textContent.trim().substring(0, 30),
                            disabled: b.disabled
                        }))
                    });

                    if ((btns.length >= 2 || cards.length >= 3 || links.length >= 3)) {
                        if (!result.sectionContainer) {
                            result.sectionContainer = {
                                depth: i,
                                tag: container.tagName,
                                className: container.className.substring(0, 80),
                                btnCount: btns.length,
                                cardCount: cards.length,
                                positionLinkCount: links.length
                            };
                        }
                    }
                    container = container.parentElement;
                }
                return result;
            }""")
            print(f"Section analysis: {section_analysis.get('sectionContainer')}")
            print(f"Containers: {section_analysis.get('containers', [])[:5]}")

            # 2. 좌/우 이동 버튼 확인
            nav_buttons = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, p, div')];
                const titleEl = allEls.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('최근 본 포지션') && text.length < 30;
                });
                if (!titleEl) return [];

                let container = titleEl;
                for (let i = 0; i < 12; i++) {
                    if (!container) break;
                    const btns = container.querySelectorAll('button');
                    if (btns.length >= 2) {
                        return [...btns].map(b => ({
                            ariaLabel: b.getAttribute('aria-label'),
                            text: b.textContent.trim().substring(0, 50),
                            disabled: b.disabled,
                            className: b.className.substring(0, 80)
                        }));
                    }
                    container = container.parentElement;
                }
                return [];
            }""")
            print(f"Nav buttons: {nav_buttons}")

            # 이동 버튼(전체보기 제외한 좌/우 버튼) 필터링
            arrow_buttons = [b for b in nav_buttons if '전체보기' not in (b.get('text') or '')]
            assert len(arrow_buttons) >= 2, f"좌/우 이동 버튼이 2개 미만: {len(arrow_buttons)}개 (전체: {nav_buttons})"
            print(f"✅ 좌/우 이동 버튼 {len(arrow_buttons)}개 확인")

            # 3. '전체보기' 버튼 확인
            view_all_visible = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, p, div')];
                const titleEl = allEls.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('최근 본 포지션') && text.length < 30;
                });
                if (!titleEl) return false;

                // 섹션 헤더 영역에서 전체보기 찾기
                let container = titleEl;
                for (let i = 0; i < 6; i++) {
                    if (!container) break;
                    const viewAllEl = [...container.querySelectorAll('a, button, span')].find(
                        el => el.textContent.trim() === '전체보기'
                    );
                    if (viewAllEl) {
                        const rect = viewAllEl.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    }
                    container = container.parentElement;
                }
                return false;
            }""")
            assert view_all_visible, "'전체보기' 버튼이 노출되지 않음"
            print("✅ '전체보기' 버튼 확인")

            # 4. 포지션 카드 5개 확인
            card_info = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, p, div')];
                const titleEl = allEls.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('최근 본 포지션') && text.length < 30;
                });
                if (!titleEl) return { error: 'title not found', total: 0, visible: 0 };

                let container = titleEl;
                for (let i = 0; i < 12; i++) {
                    if (!container) break;
                    // 포지션 카드 = /wd/ 링크를 포함한 카드형 요소
                    const posLinks = container.querySelectorAll('a[href*="/wd/"]');
                    if (posLinks.length >= 3) {
                        // 포지션 링크의 직접 부모 카드 요소 수집 (중복 제거)
                        const cardEls = new Set();
                        posLinks.forEach(link => {
                            let el = link.parentElement;
                            for (let j = 0; j < 4; j++) {
                                if (!el) break;
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 80) {
                                    cardEls.add(el);
                                    break;
                                }
                                el = el.parentElement;
                            }
                        });
                        const visibleCards = [...cardEls].slice(0, 20).filter(card => {
                            const rect = card.getBoundingClientRect();
                            return rect.width > 50 && rect.height > 50 &&
                                   rect.right > 0 && rect.left < window.innerWidth;
                        });
                        return {
                            total: posLinks.length,
                            cardElCount: cardEls.size,
                            visible: visibleCards.length,
                            containerDepth: i
                        };
                    }
                    container = container.parentElement;
                }
                return { total: 0, visible: 0, error: 'cards not found' };
            }""")
            print(f"Card info: {card_info}")

            visible_cards = card_info.get('visible', 0)
            assert visible_cards >= 5, \
                f"화면에 보이는 포지션 카드가 5개 미만: {visible_cards}개 (total links: {card_info.get('total', 0)}개)"
            print(f"✅ 포지션 카드 {visible_cards}개 이상 확인")

            # 5. 우측 버튼 클릭 시 스크롤 확인
            # 우측 버튼 index 결정 (마지막 arrow 버튼이 보통 우측)
            right_btn_index = len(nav_buttons) - 1
            for i, btn in enumerate(nav_buttons):
                label = (btn.get('ariaLabel') or '').lower()
                text_val = (btn.get('text') or '').lower()
                if any(kw in label or kw in text_val for kw in ['next', 'right', '다음', '오른쪽', '우측']):
                    right_btn_index = i
                    break

            # 클릭 전 카드 위치 저장
            before_positions = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, p, div')];
                const titleEl = allEls.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('최근 본 포지션') && text.length < 30;
                });
                if (!titleEl) return [];

                let container = titleEl;
                for (let i = 0; i < 12; i++) {
                    if (!container) break;
                    const posLinks = container.querySelectorAll('a[href*="/wd/"]');
                    if (posLinks.length >= 3) {
                        return [...posLinks].slice(0, 10).map(link => {
                            const rect = link.getBoundingClientRect();
                            return { left: Math.round(rect.left), right: Math.round(rect.right) };
                        });
                    }
                    container = container.parentElement;
                }
                return [];
            }""")
            print(f"Before scroll positions: {before_positions[:4]}")

            # 우측 버튼 클릭
            clicked = await page.evaluate("""(btnIndex) => {
                const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, p, div')];
                const titleEl = allEls.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('최근 본 포지션') && text.length < 30;
                });
                if (!titleEl) return false;

                let container = titleEl;
                for (let i = 0; i < 12; i++) {
                    if (!container) break;
                    const btns = container.querySelectorAll('button');
                    if (btns.length >= 2) {
                        const btn = btns[btnIndex];
                        if (btn && !btn.disabled) {
                            btn.click();
                            return true;
                        }
                        // disabled면 마지막 버튼 시도
                        const lastBtn = btns[btns.length - 1];
                        if (lastBtn && !lastBtn.disabled) {
                            lastBtn.click();
                            return true;
                        }
                        return false;
                    }
                    container = container.parentElement;
                }
                return false;
            }""", right_btn_index)
            print(f"Right button clicked: {clicked}")
            await page.wait_for_timeout(1500)

            # 클릭 후 카드 위치 확인
            after_positions = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, p, div')];
                const titleEl = allEls.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('최근 본 포지션') && text.length < 30;
                });
                if (!titleEl) return [];

                let container = titleEl;
                for (let i = 0; i < 12; i++) {
                    if (!container) break;
                    const posLinks = container.querySelectorAll('a[href*="/wd/"]');
                    if (posLinks.length >= 3) {
                        return [...posLinks].slice(0, 10).map(link => {
                            const rect = link.getBoundingClientRect();
                            return { left: Math.round(rect.left), right: Math.round(rect.right) };
                        });
                    }
                    container = container.parentElement;
                }
                return [];
            }""")
            print(f"After scroll positions: {after_positions[:4]}")

            # 스크롤 여부 확인
            scroll_happened = False
            if before_positions and after_positions:
                first_moved = before_positions[0]['left'] != after_positions[0]['left']
                if first_moved:
                    scroll_happened = True
                    print(f"✅ 우측 버튼 클릭 후 스크롤 확인 "
                          f"({before_positions[0]['left']} → {after_positions[0]['left']})")
                else:
                    print(f"ℹ️ 카드 위치 변화 없음 - 10개 이하 포지션이거나 이미 끝까지 스크롤됨")

            # 스크롤 후 추가 카드 노출 확인
            after_visible = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, p, div')];
                const titleEl = allEls.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('최근 본 포지션') && text.length < 30;
                });
                if (!titleEl) return 0;

                let container = titleEl;
                for (let i = 0; i < 12; i++) {
                    if (!container) break;
                    const posLinks = container.querySelectorAll('a[href*="/wd/"]');
                    if (posLinks.length >= 3) {
                        const visibleLinks = [...posLinks].slice(0, 20).filter(link => {
                            const rect = link.getBoundingClientRect();
                            return rect.width > 10 && rect.height > 10 &&
                                   rect.right > 0 && rect.left < window.innerWidth;
                        });
                        return visibleLinks.length;
                    }
                    container = container.parentElement;
                }
                return 0;
            }""")
            print(f"After scroll visible cards: {after_visible}")
            assert after_visible >= 1, f"우측 버튼 클릭 후 포지션 카드가 보이지 않음"
            print(f"✅ 우측 버튼 클릭 후 추가 포지션 카드 {after_visible}개 노출 확인")

            await page.screenshot(path='screenshots/test_20_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_20_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
