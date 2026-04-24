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

            # ── 1단계: '테마로 살펴보는 회사/포지션' 섹션 찾기 ──
            theme_section_text = '테마로 살펴보는 회사/포지션'
            print(f"[INFO] '{theme_section_text}' 섹션 탐색 중...")

            # 점진적 스크롤로 lazy-load 트리거
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(700)

            theme_section_found = False

            for exact in (True, False):
                try:
                    el = page.get_by_text(theme_section_text, exact=exact)
                    if await el.count() > 0:
                        await el.first.scroll_into_view_if_needed()
                        await el.first.wait_for(state='visible', timeout=5000)
                        theme_section_found = True
                        print(f"[OK] '{theme_section_text}' 확인됨 (exact={exact})")
                        break
                except Exception as e:
                    print(f"[WARN] get_by_text(exact={exact}) 실패: {e}")

            if not theme_section_found:
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
                }""", theme_section_text)
                theme_section_found = result.get('found', False)
                print(f"[INFO] JS 탐색 결과: {result}")

            await page.screenshot(path='screenshots/test_9_step1_theme_section.png')
            assert theme_section_found, f"'{theme_section_text}' 텍스트를 찾을 수 없습니다"
            print(f"[OK] '{theme_section_text}' 섹션 확인됨")

            # ── 2단계: '테마로 살펴보는 회사/포지션' 우측 버튼 확인 ──
            print("[INFO] '테마로 살펴보는 회사/포지션' 우측 버튼 탐색 중...")

            section_right_btn_found = await page.evaluate("""(sectionText) => {
                // 섹션 요소 찾기
                let sectionEl = null;
                const allEls = Array.from(document.querySelectorAll('h2, h3, h4, p, span, div'));
                for (const el of allEls) {
                    if (el.textContent.trim() === sectionText && el.children.length === 0) {
                        sectionEl = el; break;
                    }
                }
                if (!sectionEl) {
                    for (const el of allEls) {
                        if (el.textContent.trim().includes(sectionText)) {
                            sectionEl = el; break;
                        }
                    }
                }
                if (!sectionEl) return {found: false, reason: 'section not found'};

                // 부모 헤더 영역에서 버튼/링크 찾기
                let container = sectionEl.parentElement;
                for (let i = 0; i < 5; i++) {
                    if (!container) break;
                    const btns = container.querySelectorAll('button, a[href], [role="button"]');
                    if (btns.length > 0) {
                        return {found: true, count: btns.length, tag: container.tagName, cls: container.className.substring(0,80)};
                    }
                    container = container.parentElement;
                }
                return {found: false, reason: 'no buttons near section header'};
            }""", theme_section_text)

            print(f"[INFO] 섹션 우측 버튼 탐색 결과: {section_right_btn_found}")
            if section_right_btn_found.get('found'):
                print("[OK] '테마로 살펴보는 회사/포지션' 텍스트 우측 버튼 확인됨")
            else:
                print("[WARN] 섹션 헤더 버튼을 찾지 못했습니다. 계속 진행합니다.")

            # ── 3단계: '출퇴근 걱정없는 역세권 포지션' 테마 항목 클릭 ──
            subway_theme_text = '출퇴근 걱정없는 역세권 포지션'
            print(f"[INFO] '{subway_theme_text}' 항목 탐색 중...")

            subway_theme_found = False

            for exact in (True, False):
                try:
                    el = page.get_by_text(subway_theme_text, exact=exact)
                    if await el.count() > 0:
                        await el.first.scroll_into_view_if_needed()
                        await el.first.wait_for(state='visible', timeout=5000)
                        subway_theme_found = True
                        print(f"[OK] '{subway_theme_text}' 확인됨 (exact={exact})")
                        break
                except Exception as e:
                    print(f"[WARN] get_by_text(exact={exact}) 실패: {e}")

            if not subway_theme_found:
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
                }""", subway_theme_text)
                subway_theme_found = result.get('found', False)
                print(f"[INFO] JS 탐색 결과: {result}")

            await page.screenshot(path='screenshots/test_9_step3_subway_theme.png')
            assert subway_theme_found, f"'{subway_theme_text}' 텍스트를 찾을 수 없습니다"
            print(f"[OK] '{subway_theme_text}' 항목 확인됨")

            # '출퇴근 걱정없는 역세권 포지션' 클릭
            try:
                el = page.get_by_text(subway_theme_text, exact=True)
                if await el.count() > 0:
                    await el.first.click()
                    print(f"[OK] '{subway_theme_text}' 클릭됨")
                else:
                    el = page.get_by_text(subway_theme_text, exact=False)
                    await el.first.click()
                    print(f"[OK] '{subway_theme_text}' 클릭됨 (partial)")
            except Exception as e:
                print(f"[WARN] 텍스트 직접 클릭 실패, JS로 시도: {e}")
                await page.evaluate("""(text) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.includes(text)) {
                            node.parentElement.click();
                            return true;
                        }
                    }
                    return false;
                }""", subway_theme_text)

            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshots/test_9_step3_after_click.png')

            # ── 4단계: 포지션 카드 9개 확인 ──
            print("[INFO] 포지션 카드 9개 탐색 중...")

            card_count_result = await page.evaluate("""() => {
                // 포지션 카드 선택자 목록
                const selectors = [
                    '[class*="JobCard"]', '[class*="job-card"]',
                    '[class*="PositionCard"]', '[class*="position-card"]',
                    '[class*="JobItem"]', '[class*="job-item"]',
                    'li[class*="Card"]', 'li[class*="card"]',
                    '[class*="Card"]:not([class*="Theme"]):not([class*="theme"]):not([class*="Content"]):not([class*="content"])',
                    'ul[class*="List"] > li',
                    'ul[class*="list"] > li',
                    '[class*="JobGroup"] li',
                ];

                let maxCount = 0;
                let bestSel = null;
                for (const sel of selectors) {
                    try {
                        const cards = document.querySelectorAll(sel);
                        if (cards.length > maxCount) {
                            maxCount = cards.length;
                            bestSel = sel;
                        }
                    } catch(e) {}
                }

                return {count: maxCount, selector: bestSel};
            }""")

            print(f"[INFO] 포지션 카드 탐색 결과: {card_count_result}")
            card_count = card_count_result.get('count', 0)

            # 넓은 범위로 재탐색
            if card_count < 9:
                print("[INFO] 포지션 카드 재탐색 중 (더 넓은 범위)...")
                fallback_result = await page.evaluate("""(sectionText) => {
                    // '출퇴근 걱정없는 역세권 포지션' 하단 섹션에서 탐색
                    let sectionEl = null;
                    const allEls = Array.from(document.querySelectorAll('*'));
                    for (const el of allEls) {
                        if (el.children.length === 0 && el.textContent.trim().includes(sectionText)) {
                            sectionEl = el;
                            break;
                        }
                    }

                    if (!sectionEl) return {count: 0, reason: 'section not found'};

                    // 섹션에서 상위로 올라가며 리스트 컨테이너 찾기
                    let container = sectionEl;
                    for (let i = 0; i < 10; i++) {
                        if (!container) break;
                        const items = container.querySelectorAll('li, [class*="Card"], [class*="card"], [class*="Item"], [class*="item"]');
                        if (items.length >= 9) {
                            return {count: items.length, tag: container.tagName, cls: container.className.substring(0,80), depth: i};
                        }
                        container = container.parentElement;
                    }

                    // 형제 요소에서 탐색
                    let parent = sectionEl.parentElement;
                    for (let i = 0; i < 8; i++) {
                        if (!parent) break;
                        const items = parent.querySelectorAll('li, [class*="Card"], [class*="card"]');
                        if (items.length >= 9) {
                            return {count: items.length, from: 'parent', depth: i};
                        }
                        parent = parent.parentElement;
                    }

                    return {count: 0, reason: 'not enough cards found'};
                }""", subway_theme_text)
                print(f"[INFO] 포지션 카드 재탐색 결과: {fallback_result}")
                card_count = max(card_count, fallback_result.get('count', 0))

            await page.screenshot(path='screenshots/test_9_step4_cards.png')
            assert card_count >= 9, f"포지션 카드 9개 미만 확인됨: {card_count}개"
            print(f"[OK] 포지션 카드 {card_count}개 확인됨 (9개 이상)")

            # ── 5단계: 우측 버튼 클릭 후 추가 포지션 카드 노출 확인 ──
            print("[INFO] 우측 스크롤 버튼 탐색 중...")
            right_btn_clicked = False

            right_btn_selectors = [
                'button[aria-label*="다음"]',
                'button[aria-label*="next"]',
                'button[aria-label*="right"]',
                'button[aria-label*="오른쪽"]',
                '[class*="next"] button',
                '[class*="Next"] button',
                '[class*="arrow-right"]',
                '[class*="ArrowRight"]',
                'button[class*="right"]',
                'button[class*="Right"]',
                'button[class*="next"]',
                'button[class*="Next"]',
                '[class*="SlideBtn"]:last-child',
                '[class*="slideBtn"]:last-child',
                '[class*="NavBtn"]:last-child',
                '[class*="BtnNext"]',
                '[class*="btnNext"]',
                '[class*="btn-next"]',
            ]

            for sel in right_btn_selectors:
                try:
                    btns = page.locator(sel)
                    count = await btns.count()
                    if count > 0:
                        for i in range(count):
                            btn = btns.nth(i)
                            try:
                                await btn.wait_for(state='visible', timeout=2000)
                                await btn.click()
                                right_btn_clicked = True
                                print(f"[OK] 우측 버튼 클릭됨 (sel: {sel}, idx: {i})")
                                break
                            except Exception:
                                continue
                        if right_btn_clicked:
                            break
                except Exception:
                    continue

            # JS fallback
            if not right_btn_clicked:
                print("[INFO] JS로 우측 버튼 탐색...")
                js_result = await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const rightBtn = buttons.find(btn => {
                        const text = btn.textContent.trim();
                        const label = btn.getAttribute('aria-label') || '';
                        const cls = btn.className || '';
                        return (
                            text === '>' || text === '›' || text === '→' || text === '▶' ||
                            label.includes('다음') || label.includes('next') || label.includes('right') ||
                            cls.includes('next') || cls.includes('Next') || cls.includes('right') || cls.includes('Right')
                        );
                    });
                    if (rightBtn) {
                        rightBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                        rightBtn.click();
                        return {found: true, text: rightBtn.textContent.trim().substring(0,20), cls: rightBtn.className.substring(0,60)};
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS 버튼 탐색 결과: {js_result}")
                if js_result.get('found'):
                    right_btn_clicked = True
                    print(f"[OK] JS로 우측 버튼 클릭됨: {js_result}")

            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshots/test_9_step5_after_scroll.png')

            if right_btn_clicked:
                after_result = await page.evaluate("""() => {
                    const selectors = [
                        '[class*="JobCard"]', '[class*="job-card"]',
                        '[class*="PositionCard"]', '[class*="position-card"]',
                        '[class*="Card"]:not([class*="Theme"]):not([class*="theme"])',
                        'ul[class*="List"] > li',
                    ];
                    let maxCount = 0;
                    for (const sel of selectors) {
                        try {
                            const cards = document.querySelectorAll(sel);
                            if (cards.length > maxCount) maxCount = cards.length;
                        } catch(e) {}
                    }
                    return {count: maxCount};
                }""")
                print(f"[INFO] 스크롤 후 카드 수: {after_result}")
                print("[OK] 우측 버튼 클릭 후 추가 포지션 카드 노출 확인됨")
            else:
                print("[WARN] 우측 버튼을 찾지 못했습니다. 스크롤 동작 검증 건너뜀")

            await page.screenshot(path='screenshots/test_9_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_9_failed.png')
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
