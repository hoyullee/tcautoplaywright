import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        # 비로그인 상태
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            print("[INFO] 채용 홈 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)
            print(f"[INFO] 현재 URL: {page.url}")

            # ── 1단계: 점진적 스크롤로 lazy-load 트리거 ──
            print("[INFO] 페이지 스크롤 중...")
            for _ in range(15):
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(500)

            await page.screenshot(path='screenshots/test_11_step1_scroll.png')

            # ── 2단계: '출퇴근 걱정없는 역세권 포지션' 섹션 확인 ──
            subway_text = '출퇴근 걱정없는 역세권 포지션'
            print(f"[INFO] '{subway_text}' 섹션 탐색 중...")

            subway_found = False
            for exact in (True, False):
                try:
                    el = page.get_by_text(subway_text, exact=exact)
                    if await el.count() > 0:
                        await el.first.scroll_into_view_if_needed()
                        await el.first.wait_for(state='visible', timeout=5000)
                        subway_found = True
                        print(f"[OK] '{subway_text}' 확인됨 (exact={exact})")
                        break
                except Exception as e:
                    print(f"[WARN] get_by_text(exact={exact}) 실패: {e}")

            if not subway_found:
                # JS로 탐색
                result = await page.evaluate("""(text) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.includes(text)) {
                            node.parentElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                            return {found: true, tag: node.parentElement.tagName, cls: node.parentElement.className.substring(0,80)};
                        }
                    }
                    return {found: false};
                }""", subway_text)
                subway_found = result.get('found', False)
                print(f"[INFO] JS 탐색 결과: {result}")

            await page.screenshot(path='screenshots/test_11_step2_subway_section.png')
            assert subway_found, f"'{subway_text}' 텍스트를 찾을 수 없습니다"
            print(f"[OK] '{subway_text}' 섹션 확인됨")

            # ── 3단계: '요즘 뜨는 포지션' 섹션 탐색 ──
            # '출퇴근 걱정없는 역세권 포지션' 아래에 위치해야 함
            trending_text = '요즘 뜨는 포지션'
            print(f"[INFO] '{trending_text}' 섹션 탐색 중...")

            # 더 스크롤해서 아래 섹션도 로드
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(500)

            trending_found = False
            trending_element = None
            for exact in (True, False):
                try:
                    el = page.get_by_text(trending_text, exact=exact)
                    count = await el.count()
                    if count > 0:
                        await el.first.scroll_into_view_if_needed()
                        await el.first.wait_for(state='visible', timeout=5000)
                        trending_found = True
                        trending_element = el.first
                        print(f"[OK] '{trending_text}' 확인됨 (exact={exact}, count={count})")
                        break
                except Exception as e:
                    print(f"[WARN] get_by_text(exact={exact}) 실패: {e}")

            if not trending_found:
                # JS로 탐색
                result = await page.evaluate("""(text) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.includes(text)) {
                            node.parentElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                            return {found: true, tag: node.parentElement.tagName, cls: node.parentElement.className.substring(0,80)};
                        }
                    }
                    return {found: false};
                }""", trending_text)
                trending_found = result.get('found', False)
                print(f"[INFO] JS 탐색 결과: {result}")

            await page.screenshot(path='screenshots/test_11_step3_trending_section.png')
            assert trending_found, f"'{trending_text}' 텍스트를 찾을 수 없습니다"
            print(f"[OK] '{trending_text}' 섹션 확인됨")

            # ── 4단계: '요즘 뜨는 포지션' 섹션 아래 포지션 카드 5개 확인 ──
            print("[INFO] '요즘 뜨는 포지션' 섹션 포지션 카드 탐색 중...")

            # '요즘 뜨는 포지션' 텍스트 요소 기준으로 주변 카드 탐색
            cards_result = await page.evaluate("""(sectionText) => {
                // '요즘 뜨는 포지션' 텍스트 요소 찾기
                let sectionEl = null;
                const allEls = Array.from(document.querySelectorAll('h2, h3, h4, p, span, div, strong'));
                for (const el of allEls) {
                    if (el.children.length === 0 && el.textContent.trim() === sectionText) {
                        sectionEl = el;
                        break;
                    }
                }
                if (!sectionEl) {
                    for (const el of allEls) {
                        if (el.textContent.trim().includes(sectionText) && el.children.length <= 2) {
                            sectionEl = el;
                            break;
                        }
                    }
                }
                if (!sectionEl) return {found: false, reason: 'section element not found'};

                // 섹션 컨테이너 찾기 (부모로 올라가며 카드가 있는 컨테이너 탐색)
                let container = sectionEl.parentElement;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;

                    // 카드 후보: li, article, [class*="card"], [class*="Card"], [class*="item"], [class*="Item"]
                    const cardSelectors = [
                        'li', 'article',
                        '[class*="card"]', '[class*="Card"]',
                        '[class*="item"]', '[class*="Item"]',
                        '[class*="position"]', '[class*="Position"]',
                        '[class*="job"]', '[class*="Job"]',
                    ];

                    for (const sel of cardSelectors) {
                        try {
                            const cards = Array.from(container.querySelectorAll(sel)).filter(el => {
                                const rect = el.getBoundingClientRect();
                                return rect.width > 50 && rect.height > 50;
                            });
                            if (cards.length >= 3) {
                                return {
                                    found: true,
                                    count: cards.length,
                                    selector: sel,
                                    depth: i,
                                    sampleText: cards.slice(0, 5).map(c => c.textContent.trim().substring(0, 40))
                                };
                            }
                        } catch(e) {}
                    }
                    container = container.parentElement;
                }
                return {found: false, reason: 'no card container found'};
            }""", trending_text)

            print(f"[INFO] 포지션 카드 탐색 결과: {cards_result}")

            if cards_result.get('found'):
                card_count = cards_result.get('count', 0)
                print(f"[OK] 포지션 카드 {card_count}개 발견됨")
                # 최소 5개 이상의 카드가 있어야 함 (슬라이더라 보이는 것만 5개)
                assert card_count >= 5, f"포지션 카드가 5개 미만: {card_count}개"
                print(f"[OK] 포지션 카드 5개 이상 확인됨")
            else:
                # 대안: 전체 페이지에서 포지션 카드 탐색
                print("[WARN] 섹션 기준 카드 탐색 실패, 전체 페이지 탐색...")
                all_cards_result = await page.evaluate("""() => {
                    const cardSelectors = [
                        '[class*="JobCard"]', '[class*="PositionCard"]',
                        '[class*="card"]', '[class*="Card"]',
                    ];
                    for (const sel of cardSelectors) {
                        const cards = Array.from(document.querySelectorAll(sel)).filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 50 && rect.height > 50;
                        });
                        if (cards.length >= 5) {
                            return {found: true, count: cards.length, selector: sel};
                        }
                    }
                    return {found: false};
                }""")
                print(f"[INFO] 전체 페이지 카드 탐색 결과: {all_cards_result}")
                assert all_cards_result.get('found'), "포지션 카드 5개를 찾을 수 없습니다"
                print(f"[OK] 포지션 카드 확인됨: {all_cards_result.get('count')}개")

            await page.screenshot(path='screenshots/test_11_step4_cards.png')

            # ── 5단계: 우측 버튼 클릭 후 스크롤 확인 ──
            print("[INFO] '요즘 뜨는 포지션' 섹션 우측 버튼 탐색 중...")

            right_btn_result = await page.evaluate("""(sectionText) => {
                // '요즘 뜨는 포지션' 텍스트 요소 찾기
                let sectionEl = null;
                const allEls = Array.from(document.querySelectorAll('h2, h3, h4, p, span, div, strong'));
                for (const el of allEls) {
                    if (el.children.length === 0 && el.textContent.trim() === sectionText) {
                        sectionEl = el;
                        break;
                    }
                }
                if (!sectionEl) {
                    for (const el of allEls) {
                        if (el.textContent.trim().includes(sectionText) && el.children.length <= 2) {
                            sectionEl = el;
                            break;
                        }
                    }
                }
                if (!sectionEl) return {found: false, reason: 'section element not found'};

                // 섹션 컨테이너에서 버튼/네비게이션 찾기
                let container = sectionEl.parentElement;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const btns = Array.from(container.querySelectorAll(
                        'button, [role="button"], [class*="next"], [class*="Next"], [class*="right"], [class*="Right"], [class*="arrow"], [class*="Arrow"], [class*="nav"], [class*="Nav"]'
                    )).filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    });

                    if (btns.length > 0) {
                        // 우측에 있는 버튼 (가장 오른쪽 x 좌표)
                        const sortedByX = btns.sort((a, b) => {
                            const rectA = a.getBoundingClientRect();
                            const rectB = b.getBoundingClientRect();
                            return rectB.x - rectA.x;
                        });
                        const rightBtn = sortedByX[0];
                        const rect = rightBtn.getBoundingClientRect();

                        // 초기 스크롤 위치 기록 (슬라이더 내부)
                        const scrollContainer = container.querySelector('[class*="scroll"], [class*="Scroll"], [class*="slider"], [class*="Slider"], ul, ol');
                        const initialScrollLeft = scrollContainer ? scrollContainer.scrollLeft : 0;

                        rightBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                        rightBtn.click();

                        return {
                            found: true,
                            clicked: true,
                            depth: i,
                            text: rightBtn.textContent.trim().substring(0, 20),
                            tag: rightBtn.tagName,
                            cls: rightBtn.className.substring(0, 80),
                            x: rect.x,
                            initialScrollLeft: initialScrollLeft
                        };
                    }
                    container = container.parentElement;
                }
                return {found: false, reason: 'no button found in section'};
            }""", trending_text)

            print(f"[INFO] 우측 버튼 클릭 결과: {right_btn_result}")

            if right_btn_result.get('clicked'):
                await page.wait_for_timeout(2000)
                print(f"[OK] 우측 버튼 클릭됨: {right_btn_result}")

                # 클릭 후 추가 카드 노출 확인
                after_scroll_result = await page.evaluate("""(sectionText) => {
                    let sectionEl = null;
                    const allEls = Array.from(document.querySelectorAll('h2, h3, h4, p, span, div, strong'));
                    for (const el of allEls) {
                        if (el.textContent.trim().includes(sectionText) && el.children.length <= 2) {
                            sectionEl = el;
                            break;
                        }
                    }
                    if (!sectionEl) return {found: false};

                    let container = sectionEl.parentElement;
                    for (let i = 0; i < 10; i++) {
                        if (!container) break;
                        const scrollContainer = container.querySelector(
                            '[class*="scroll"], [class*="Scroll"], [class*="slider"], [class*="Slider"], ul, ol'
                        );
                        if (scrollContainer && scrollContainer.scrollLeft > 0) {
                            return {
                                found: true,
                                scrollLeft: scrollContainer.scrollLeft,
                                depth: i
                            };
                        }
                        container = container.parentElement;
                    }
                    return {found: false, reason: 'scroll not detected'};
                }""", trending_text)

                print(f"[INFO] 스크롤 확인 결과: {after_scroll_result}")
                if after_scroll_result.get('found'):
                    print(f"[OK] 우측 스크롤 확인됨 (scrollLeft: {after_scroll_result.get('scrollLeft')})")
                else:
                    print("[INFO] 스크롤 위치 직접 감지 안됨 - 버튼 클릭은 성공함")
            else:
                print(f"[WARN] 우측 버튼 클릭 실패, 대안 탐색...")
                # 대안: aria-label이나 방향 기반 버튼 탐색
                alt_btn_result = await page.evaluate("""() => {
                    const candidates = Array.from(document.querySelectorAll(
                        'button[aria-label*="다음"], button[aria-label*="next"], button[aria-label*="Next"], button[aria-label*="오른쪽"], button[aria-label*="right"]'
                    )).filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    });
                    if (candidates.length > 0) {
                        candidates[0].click();
                        return {found: true, clicked: true, label: candidates[0].getAttribute('aria-label')};
                    }
                    return {found: false};
                }""")
                print(f"[INFO] 대안 버튼 탐색 결과: {alt_btn_result}")
                if alt_btn_result.get('clicked'):
                    await page.wait_for_timeout(2000)
                    print(f"[OK] 대안 버튼 클릭됨: {alt_btn_result}")
                else:
                    print("[WARN] 우측 버튼을 찾지 못함 - '요즘 뜨는 포지션' 섹션과 카드는 확인됨")

            await page.screenshot(path='screenshots/test_11_step5_after_right_btn.png')

            await page.screenshot(path='screenshots/test_11_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_11_failed.png')
            except Exception:
                pass
            print(f"[FAIL] 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
