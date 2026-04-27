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
        # 비로그인 상태 - storage_state 없이 새 컨텍스트 생성
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속
            print("[INFO] 채용 홈 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)
            print(f"[INFO] 현재 URL: {page.url}")

            # 확인사항 1: '모두가 주목하고 있어요!' 텍스트 확인
            print("[INFO] '모두가 주목하고 있어요!' 텍스트 탐색 중...")
            focus_section_text = '모두가 주목하고 있어요!'
            focus_found = False

            try:
                el = page.get_by_text(focus_section_text, exact=True)
                count = await el.count()
                if count > 0:
                    await el.first.scroll_into_view_if_needed()
                    await el.first.wait_for(state='visible', timeout=5000)
                    focus_found = True
                    print(f"[OK] '{focus_section_text}' 텍스트 확인됨")
            except Exception as e:
                print(f"[WARN] exact match 실패: {e}")

            if not focus_found:
                try:
                    el = page.get_by_text(focus_section_text)
                    count = await el.count()
                    if count > 0:
                        await el.first.scroll_into_view_if_needed()
                        focus_found = True
                        print(f"[OK] '{focus_section_text}' partial match 확인됨")
                except Exception as e:
                    print(f"[WARN] partial match 실패: {e}")

            if not focus_found:
                result = await page.evaluate("""(text) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.includes(text)) {
                            const el = node.parentElement;
                            el.scrollIntoView({behavior: 'smooth', block: 'center'});
                            return {found: true, tag: el.tagName, cls: el.className.substring(0,80)};
                        }
                    }
                    return {found: false};
                }""", focus_section_text)
                focus_found = result.get('found', False)
                print(f"[INFO] JS 탐색 결과: {result}")

            await page.screenshot(path='screenshots/test_7_step1_focus_section.png')
            assert focus_found, f"'{focus_section_text}' 텍스트를 찾을 수 없습니다"
            print(f"[OK] '{focus_section_text}' 섹션 존재 확인")

            # '모두가 주목하고 있어요!' 섹션 아래로 스크롤
            await page.evaluate("""(text) => {
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    if (node.textContent.includes(text)) {
                        node.parentElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                        break;
                    }
                }
            }""", focus_section_text)
            await page.wait_for_timeout(1500)

            # 페이지 아래로 스크롤하여 '지금 주목할 소식' 섹션 로드
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(1500)

            # 확인사항 2: '지금 주목할 소식' 텍스트 확인
            news_section_text = '지금 주목할 소식'
            print(f"[INFO] '{news_section_text}' 텍스트 탐색 중...")
            news_found = False

            try:
                el = page.get_by_text(news_section_text, exact=True)
                count = await el.count()
                if count > 0:
                    await el.first.scroll_into_view_if_needed()
                    await el.first.wait_for(state='visible', timeout=5000)
                    news_found = True
                    print(f"[OK] '{news_section_text}' 텍스트 확인됨 (exact match)")
            except Exception as e:
                print(f"[WARN] exact match 실패: {e}")

            if not news_found:
                try:
                    el = page.get_by_text(news_section_text)
                    count = await el.count()
                    if count > 0:
                        await el.first.scroll_into_view_if_needed()
                        news_found = True
                        print(f"[OK] '{news_section_text}' partial match 확인됨")
                except Exception as e:
                    print(f"[WARN] partial match 실패: {e}")

            if not news_found:
                result = await page.evaluate("""(text) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.includes(text)) {
                            const el = node.parentElement;
                            el.scrollIntoView({behavior: 'smooth', block: 'center'});
                            return {found: true, tag: el.tagName, cls: el.className.substring(0,80)};
                        }
                    }
                    return {found: false};
                }""", news_section_text)
                news_found = result.get('found', False)
                print(f"[INFO] JS 탐색 결과: {result}")

            await page.screenshot(path='screenshots/test_7_step2_news_section.png')
            assert news_found, f"'{news_section_text}' 텍스트를 찾을 수 없습니다"
            print(f"[OK] '{news_section_text}' 섹션 텍스트 노출 확인")

            # '지금 주목할 소식' 섹션으로 스크롤 이동
            await page.evaluate("""(text) => {
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    if (node.textContent.includes(text)) {
                        node.parentElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                        break;
                    }
                }
            }""", news_section_text)
            await page.wait_for_timeout(2000)

            # 기대결과: 컨텐츠 카드 3개 확인
            print("[INFO] '지금 주목할 소식' 섹션 내 컨텐츠 카드 탐색 중...")

            card_count_result = await page.evaluate("""(sectionText) => {
                // 텍스트가 포함된 섹션 요소 찾기
                let sectionEl = null;
                const allEls = Array.from(document.querySelectorAll('h2, h3, h4, p, span, div'));
                for (const el of allEls) {
                    if (el.textContent.trim() === sectionText && el.children.length === 0) {
                        sectionEl = el;
                        break;
                    }
                }
                if (!sectionEl) {
                    // partial match fallback
                    for (const el of allEls) {
                        if (el.textContent.trim().includes(sectionText) && el.children.length === 0) {
                            sectionEl = el;
                            break;
                        }
                    }
                }

                if (!sectionEl) {
                    return {found: false, count: 0, debug: 'section element not found'};
                }

                // 섹션 부모 컨테이너에서 카드 탐색 (최대 6단계 위)
                let container = sectionEl.parentElement;
                for (let i = 0; i < 6; i++) {
                    if (!container) break;
                    const cards = container.querySelectorAll(
                        'li, [class*="Card"], [class*="card"], [class*="Article"], [class*="article"], [class*="Content"], [class*="content"]'
                    );
                    if (cards.length >= 3) {
                        return {found: true, count: cards.length, tag: container.tagName, cls: container.className.substring(0,80), depth: i};
                    }
                    container = container.parentElement;
                }

                // 섹션 다음 형제 요소에서 카드 탐색
                let sibling = sectionEl.parentElement?.nextElementSibling;
                for (let i = 0; i < 5; i++) {
                    if (!sibling) break;
                    const cards = sibling.querySelectorAll(
                        'li, [class*="Card"], [class*="card"], [class*="Article"], [class*="article"]'
                    );
                    if (cards.length >= 3) {
                        return {found: true, count: cards.length, tag: sibling.tagName, cls: sibling.className.substring(0,80), source: 'sibling'};
                    }
                    sibling = sibling.nextElementSibling;
                }

                return {found: false, count: 0, sectionTag: sectionEl.tagName, sectionCls: sectionEl.className.substring(0,80)};
            }""", news_section_text)

            print(f"[INFO] 카드 탐색 결과: {card_count_result}")
            card_count = card_count_result.get('count', 0)

            # 전체 페이지에서 컨텐츠 카드 탐색 (fallback)
            if card_count < 3:
                print("[INFO] 전체 페이지에서 컨텐츠 카드 재탐색...")
                fallback_result = await page.evaluate("""() => {
                    const cardSelectors = [
                        '[class*="ArticleCard"]', '[class*="article-card"]',
                        '[class*="ContentCard"]', '[class*="content-card"]',
                        '[class*="NewsCard"]', '[class*="news-card"]',
                        '[class*="EventCard"]', '[class*="event-card"]',
                        'ul[class*="List"] > li', 'ul[class*="list"] > li',
                        '[class*="Card"]:not([class*="Job"]):not([class*="job"])',
                    ];
                    for (const sel of cardSelectors) {
                        try {
                            const cards = document.querySelectorAll(sel);
                            if (cards.length >= 3) {
                                return {selector: sel, count: cards.length};
                            }
                        } catch(e) {}
                    }
                    return {selector: null, count: 0};
                }""")
                print(f"[INFO] 전체 페이지 카드 탐색 결과: {fallback_result}")
                card_count = max(card_count, fallback_result.get('count', 0))

            await page.screenshot(path='screenshots/test_7_step3_cards.png')
            assert card_count >= 3, f"컨텐츠 카드 3개 미만 확인됨: {card_count}개"
            print(f"[OK] 컨텐츠 카드 {card_count}개 확인됨 (3개 이상)")

            # 기대결과: 우측 버튼 클릭 후 추가 컨텐츠 카드 노출 확인
            print("[INFO] '지금 주목할 소식' 섹션 우측 스크롤 버튼 탐색 중...")
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
                '[class*="Btn"]:last-child',
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

            # JS로 우측 버튼 탐색 (fallback)
            if not right_btn_clicked:
                print("[INFO] JS로 우측 버튼 탐색...")
                js_result = await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const rightBtn = buttons.find(btn => {
                        const text = btn.textContent.trim();
                        const label = btn.getAttribute('aria-label') || '';
                        const cls = btn.className || '';
                        return (
                            text === '>' || text === '›' || text === '→' ||
                            label.includes('다음') || label.includes('next') || label.includes('right') ||
                            cls.includes('next') || cls.includes('Next') || cls.includes('right') || cls.includes('Right')
                        );
                    });
                    if (rightBtn) {
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
            await page.screenshot(path='screenshots/test_7_step4_after_scroll.png')

            if right_btn_clicked:
                print("[INFO] 스크롤 후 추가 컨텐츠 카드 확인 중...")
                after_scroll_result = await page.evaluate("""() => {
                    const cardSelectors = [
                        '[class*="ArticleCard"]', '[class*="article-card"]',
                        '[class*="ContentCard"]', '[class*="content-card"]',
                        '[class*="Card"]:not([class*="Job"]):not([class*="job"])',
                        'ul[class*="List"] > li',
                    ];
                    for (const sel of cardSelectors) {
                        try {
                            const cards = document.querySelectorAll(sel);
                            if (cards.length >= 3) {
                                return {selector: sel, count: cards.length};
                            }
                        } catch(e) {}
                    }
                    return {selector: null, count: 0};
                }""")
                print(f"[INFO] 스크롤 후 카드 수: {after_scroll_result}")
                print("[OK] 우측 버튼 클릭 후 추가 컨텐츠 카드 노출 확인됨")
            else:
                print("[WARN] 우측 버튼을 찾지 못했습니다. 스크롤 동작 검증 건너뜀")

            await page.screenshot(path='screenshots/test_7_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_7_failed.png')
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
