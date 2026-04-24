"""
테스트 케이스 #29
환경: PC
기능영역: GNB > 채용 > 탐색
사전조건:
  1. 로그인 상태 (auth_state.json 세션 사용)
  2. 탐색 페이지 진입 상태
확인사항:
  1. 리스트 영역 상단
  2. '적극 채용 중인 회사' 항목 확인
기대결과: 회사 카드 5개 노출
"""
import sys
import os
import re
import asyncio
from playwright.async_api import async_playwright

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

AUTH_STATE = 'work/auth_state.json'
TARGET_TEXT = '적극 채용 중인 회사'
EXPECTED_CARD_COUNT = 5

# 탐색 페이지 URL: wdlist 가 채용 > 탐색 페이지
EXPLORE_URLS = [
    'https://www.wanted.co.kr/wdlist',          # 채용 탐색 페이지 (리다이렉트 포함)
    'https://www.wanted.co.kr/wdlist/explore',  # 대안 1
    'https://www.wanted.co.kr/explore',         # 대안 2
]


async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            storage_state=AUTH_STATE,
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # ── 1단계: 탐색 페이지 접속 ──
            print("[INFO] 탐색 페이지(wdlist) 접속 중...")
            explore_url = None

            for url in EXPLORE_URLS:
                print(f"[INFO] {url} 시도...")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                current_url = page.url

                # 페이지 텍스트 확인
                page_text = await page.evaluate('() => document.body.innerText')
                if TARGET_TEXT in page_text:
                    explore_url = current_url
                    print(f"[OK] 탐색 페이지에서 섹션 발견 - URL: {current_url}")
                    break
                else:
                    print(f"[INFO] {current_url} 에서 섹션 미발견")

            if not explore_url:
                print("[WARN] 기본 URL에서 섹션 미발견, 현재 페이지 유지")
                explore_url = page.url

            await page.screenshot(path='screenshots/test_29_step1_explore.png')

            # ── 2단계: 로그인 상태 확인 ──
            login_status = await page.evaluate("""() => {
                const allEls = Array.from(document.querySelectorAll('a, button'));
                for (const el of allEls) {
                    const text = el.textContent.trim();
                    const rect = el.getBoundingClientRect();
                    if (text === '로그인' && rect.width > 0) {
                        return {loggedIn: false, reason: '로그인 버튼 발견'};
                    }
                }
                return {loggedIn: true, reason: '로그인 버튼 없음'};
            }""")
            print(f"[INFO] 로그인 상태: {login_status}")

            # ── 3단계: 페이지 스크롤 (lazy-load 트리거) ──
            print("[INFO] 페이지 스크롤 중...")
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(400)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1500)

            await page.screenshot(path='screenshots/test_29_step2_scrolled.png')

            # ── 4단계: '적극 채용 중인 회사' 섹션 탐색 ──
            print(f"[INFO] '{TARGET_TEXT}' 섹션 및 카드 탐색 중...")

            card_result = await page.evaluate("""(targetText) => {
                // 1. 텍스트 워커로 섹션 헤딩 찾기
                let sectionEl = null;
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    const text = node.textContent.trim();
                    if (text.includes(targetText)) {
                        sectionEl = node.parentElement;
                        break;
                    }
                }

                if (!sectionEl) {
                    return {
                        sectionFound: false,
                        cardCount: 0,
                        reason: '섹션 헤딩 미발견',
                    };
                }

                // 2. 섹션 헤딩이 visible한지 확인
                const sectionRect = sectionEl.getBoundingClientRect();
                const sectionVisible = sectionRect.width > 0 && sectionRect.height > 0;

                // 3. 섹션 컨테이너 찾기 (상위 요소 탐색)
                let container = sectionEl;
                let companyCards = [];
                let foundSelector = '';

                for (let depth = 0; depth < 15; depth++) {
                    container = container.parentElement;
                    if (!container) break;

                    // 회사 카드 탐색: company URL을 포함한 링크
                    const companyLinks = container.querySelectorAll('a[href*="/company/"]');
                    const visibleLinks = Array.from(companyLinks).filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 20 && rect.height > 20;
                    });

                    if (visibleLinks.length >= 3 && visibleLinks.length <= 15) {
                        companyCards = visibleLinks;
                        foundSelector = 'a[href*="/company/"]';
                        break;
                    }

                    // li 요소 탐색
                    const liEls = container.querySelectorAll('li');
                    const visibleLi = Array.from(liEls).filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 50 && rect.height > 50;
                    });

                    if (visibleLi.length >= 3 && visibleLi.length <= 10) {
                        companyCards = visibleLi;
                        foundSelector = 'li';
                        break;
                    }
                }

                return {
                    sectionFound: true,
                    sectionVisible: sectionVisible,
                    sectionTag: sectionEl.tagName,
                    sectionCls: sectionEl.className.substring(0, 80),
                    sectionText: sectionEl.textContent.trim().substring(0, 80),
                    cardCount: companyCards.length,
                    foundSelector: foundSelector,
                    cardTexts: companyCards.slice(0, 7).map(el => el.textContent.trim().substring(0, 40)),
                    cardHrefs: companyCards.slice(0, 7).map(el => el.href || ''),
                };
            }""", TARGET_TEXT)

            print(f"[INFO] 섹션 탐색 결과: sectionFound={card_result.get('sectionFound')}, "
                  f"sectionVisible={card_result.get('sectionVisible')}, "
                  f"cardCount={card_result.get('cardCount')}")

            if card_result.get('cardCount', 0) > 0:
                print(f"[INFO] 카드 목록 ({card_result.get('foundSelector')}):")
                for i, txt in enumerate(card_result.get('cardTexts', [])):
                    print(f"  카드{i+1}: {txt}")

            await page.screenshot(path='screenshots/test_29_step3_cards.png')

            final_count = card_result.get('cardCount', 0)

            # ── 5단계: 대체 카드 탐색 (방법2: 전체 company 링크에서 섹션 근처 것들) ──
            if final_count < 3:
                print("[INFO] 방법2: 전체 회사 링크에서 섹션 근처 카드 탐색...")
                alt_result = await page.evaluate("""(targetText) => {
                    // 모든 company 링크 찾기
                    const allCompanyLinks = Array.from(document.querySelectorAll('a[href*="/company/"]'));
                    const visible = allCompanyLinks.filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 20 && rect.height > 20;
                    });

                    // 섹션 헤딩 위치 찾기
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    let sectionEl = null;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.trim().includes(targetText)) {
                            sectionEl = node.parentElement;
                            break;
                        }
                    }

                    if (!sectionEl) {
                        return { count: visible.length, bySection: false,
                                 hrefs: visible.slice(0, 7).map(el => el.href) };
                    }

                    const sectionRect = sectionEl.getBoundingClientRect();

                    // 섹션 헤딩과 가까운 링크들만 필터링
                    const nearLinks = visible.filter(el => {
                        const rect = el.getBoundingClientRect();
                        return Math.abs(rect.top - sectionRect.top) < 600;
                    });

                    return {
                        count: nearLinks.length,
                        bySection: true,
                        hrefs: nearLinks.slice(0, 7).map(el => el.href),
                    };
                }""", TARGET_TEXT)

                print(f"[INFO] 방법2 결과: {alt_result}")
                if alt_result.get('count', 0) >= 3:
                    final_count = alt_result['count']

            # ── 6단계: HTML 기반 분석 (최후 수단) ──
            if final_count < 3:
                print("[INFO] 방법3: HTML 기반 분석...")
                section_html = await page.evaluate("""(targetText) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.trim().includes(targetText)) {
                            let el = node.parentElement;
                            for (let i = 0; i < 8; i++) {
                                if (!el || !el.parentElement) break;
                                el = el.parentElement;
                            }
                            return el ? el.outerHTML.substring(0, 10000) : null;
                        }
                    }
                    return null;
                }""", TARGET_TEXT)

                if section_html:
                    li_matches = re.findall(r'<li[\s>]', section_html)
                    company_links = re.findall(r'href="[^"]*?/company/\d+[^"]*?"', section_html)
                    print(f"[INFO] HTML li: {len(li_matches)}, company links: {len(company_links)}")

                    if 3 <= len(company_links) <= 10:
                        final_count = len(company_links)
                    elif 3 <= len(li_matches) <= 10:
                        final_count = len(li_matches)

            print(f"\n[RESULT] '{TARGET_TEXT}' 회사 카드 수: {final_count}")
            await page.screenshot(path='screenshots/test_29_final.png')

            # ── 7단계: 검증 ──
            assert card_result.get('sectionFound'), (
                f"'{TARGET_TEXT}' 섹션이 탐색 페이지에서 발견되지 않았습니다."
            )
            assert card_result.get('sectionVisible', False), (
                f"'{TARGET_TEXT}' 섹션이 발견되었으나 visible하지 않습니다."
            )
            assert final_count == EXPECTED_CARD_COUNT, (
                f"회사 카드 수 불일치: 예상={EXPECTED_CARD_COUNT}, 실제={final_count}"
            )

            print(f"[PASS] 테스트 케이스 #29 통과: '{TARGET_TEXT}' 섹션에 회사 카드 {final_count}개 노출 확인")
            print("AUTOMATION_SUCCESS")
            return True

        except AssertionError as e:
            try:
                await page.screenshot(path='screenshots/test_29_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_29_error.png')
            except Exception:
                pass
            import traceback
            traceback.print_exc()
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
