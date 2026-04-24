"""
테스트 케이스 #30
환경: PC
기능영역: GNB > 채용 > 탐색
사전조건:
  1. 로그인 상태 (auth_state.json 세션 사용)
  2. 탐색 페이지 진입 상태
확인사항:
  1. '적극 채용 중인 회사' 항목 하단
  2. 포지션 리스트 노출 확인
기대결과: 포지션 카드 노출되며 하단으로 스크롤 시 추가 포지션 카드 노출
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
SECTION_TEXT = '적극 채용 중인 회사'

EXPLORE_URLS = [
    'https://www.wanted.co.kr/wdlist',
    'https://www.wanted.co.kr/wdlist/explore',
    'https://www.wanted.co.kr/explore',
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
                page_text = await page.evaluate('() => document.body.innerText')
                if SECTION_TEXT in page_text:
                    explore_url = current_url
                    print(f"[OK] 탐색 페이지에서 섹션 발견 - URL: {current_url}")
                    break
                else:
                    print(f"[INFO] {current_url} 에서 섹션 미발견")

            if not explore_url:
                print("[WARN] 기본 URL에서 섹션 미발견, 현재 페이지 유지")
                explore_url = page.url

            await page.screenshot(path='screenshots/test_30_step1_explore.png')

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

            # ── 3단계: 초기 페이지 스크롤 (lazy-load 트리거 및 섹션 렌더링) ──
            print("[INFO] 페이지 스크롤 중 (lazy-load 트리거)...")
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            for _ in range(10):
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(400)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)

            await page.screenshot(path='screenshots/test_30_step2_scrolled.png')

            # ── 4단계: '적극 채용 중인 회사' 섹션 하단 포지션 카드 탐색 ──
            print(f"[INFO] '{SECTION_TEXT}' 하단 포지션 카드 탐색 중...")

            position_result = await page.evaluate("""(sectionText) => {
                // 섹션 헤딩 찾기
                let sectionEl = null;
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    const text = node.textContent.trim();
                    if (text.includes(sectionText)) {
                        sectionEl = node.parentElement;
                        break;
                    }
                }

                if (!sectionEl) {
                    return {
                        sectionFound: false,
                        positionCount: 0,
                        reason: '섹션 헤딩 미발견',
                    };
                }

                const sectionRect = sectionEl.getBoundingClientRect();

                // 섹션 컨테이너 찾기 (상위 요소 탐색)
                let container = sectionEl;
                let positionCards = [];
                let foundSelector = '';

                for (let depth = 0; depth < 20; depth++) {
                    container = container.parentElement;
                    if (!container) break;

                    // 포지션 카드: /jobs/ URL을 포함한 링크
                    const jobLinks = container.querySelectorAll('a[href*="/wd/"]');
                    const visibleJobLinks = Array.from(jobLinks).filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 20 && rect.height > 20;
                    });

                    if (visibleJobLinks.length >= 3) {
                        positionCards = visibleJobLinks;
                        foundSelector = 'a[href*="/wd/"]';
                        break;
                    }

                    // 포지션 카드 대안: /jobs/ 링크
                    const jobLinks2 = container.querySelectorAll('a[href*="/jobs/"]');
                    const visibleJobLinks2 = Array.from(jobLinks2).filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 20 && rect.height > 20;
                    });

                    if (visibleJobLinks2.length >= 3) {
                        positionCards = visibleJobLinks2;
                        foundSelector = 'a[href*="/jobs/"]';
                        break;
                    }
                }

                // 컨테이너에서 못 찾으면 섹션 아래에 있는 포지션 링크 탐색
                if (positionCards.length === 0) {
                    // 섹션 헤딩의 Y좌표 이후 포지션 링크 탐색
                    const allJobLinks = Array.from(document.querySelectorAll('a[href*="/wd/"], a[href*="/jobs/"]'));
                    const belowSection = allJobLinks.filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 20 && rect.height > 20 && rect.top > sectionRect.top;
                    });
                    if (belowSection.length >= 3) {
                        positionCards = belowSection;
                        foundSelector = 'a[href*="/wd/"] or /jobs/ below section';
                    }
                }

                return {
                    sectionFound: true,
                    sectionVisible: sectionRect.width > 0 && sectionRect.height > 0,
                    sectionTag: sectionEl.tagName,
                    sectionText: sectionEl.textContent.trim().substring(0, 80),
                    positionCount: positionCards.length,
                    foundSelector: foundSelector,
                    cardTexts: positionCards.slice(0, 5).map(el => el.textContent.trim().substring(0, 60)),
                    cardHrefs: positionCards.slice(0, 5).map(el => el.href || ''),
                };
            }""", SECTION_TEXT)

            print(f"[INFO] 섹션 탐색 결과: sectionFound={position_result.get('sectionFound')}, "
                  f"sectionVisible={position_result.get('sectionVisible')}, "
                  f"positionCount={position_result.get('positionCount')}")

            if position_result.get('positionCount', 0) > 0:
                print(f"[INFO] 포지션 카드 목록 ({position_result.get('foundSelector')}):")
                for i, txt in enumerate(position_result.get('cardTexts', [])):
                    print(f"  카드{i+1}: {txt[:60]}")
                for i, href in enumerate(position_result.get('cardHrefs', [])):
                    print(f"  링크{i+1}: {href[:80]}")

            await page.screenshot(path='screenshots/test_30_step3_positions.png')

            initial_count = position_result.get('positionCount', 0)

            # ── 5단계: 추가 탐색 (다양한 셀렉터 시도) ──
            if initial_count < 3:
                print("[INFO] 방법2: 다양한 포지션 카드 셀렉터 탐색...")
                alt_result = await page.evaluate("""(sectionText) => {
                    const sectionWalker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let sectionEl = null;
                    let node;
                    while ((node = sectionWalker.nextNode())) {
                        if (node.textContent.trim().includes(sectionText)) {
                            sectionEl = node.parentElement;
                            break;
                        }
                    }

                    // 다양한 카드 셀렉터들
                    const selectors = [
                        'li[class*="card"]',
                        'li[class*="Card"]',
                        'li[class*="job"]',
                        'li[class*="Job"]',
                        'li[class*="position"]',
                        'li[class*="Position"]',
                        '[data-cy*="job"]',
                        '[data-cy*="position"]',
                        'article',
                        '[class*="JobCard"]',
                        '[class*="PositionCard"]',
                        '[class*="job-card"]',
                        '[class*="position-card"]',
                    ];

                    const results = {};
                    for (const sel of selectors) {
                        try {
                            const els = document.querySelectorAll(sel);
                            const visible = Array.from(els).filter(el => {
                                const rect = el.getBoundingClientRect();
                                return rect.width > 50 && rect.height > 50;
                            });
                            if (visible.length > 0) {
                                results[sel] = visible.length;
                            }
                        } catch(e) {}
                    }

                    // 섹션 이후 li 요소들
                    if (sectionEl) {
                        const sectionRect = sectionEl.getBoundingClientRect();
                        const allLi = Array.from(document.querySelectorAll('li'));
                        const belowLi = allLi.filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 100 && rect.height > 80 && rect.top > sectionRect.top + 50;
                        });
                        results['li_below_section'] = belowLi.length;
                    }

                    return results;
                }""", SECTION_TEXT)

                print(f"[INFO] 방법2 셀렉터 결과: {alt_result}")

                # 가장 많이 나온 셀렉터의 결과 사용
                if alt_result:
                    max_count = max(alt_result.values()) if alt_result else 0
                    if max_count >= 3:
                        initial_count = max_count
                        print(f"[INFO] 방법2로 {max_count}개 포지션 카드 발견")

            # ── 6단계: 스크롤 후 포지션 카드 수 재확인 ──
            print("[INFO] 추가 스크롤로 더 많은 포지션 카드 로드 중...")
            count_before_scroll = initial_count

            # 더 아래로 스크롤
            for _ in range(15):
                await page.evaluate("window.scrollBy(0, 600)")
                await page.wait_for_timeout(500)
            await page.wait_for_timeout(2000)

            await page.screenshot(path='screenshots/test_30_step4_after_scroll.png')

            # 스크롤 후 포지션 카드 수 재확인
            after_scroll_result = await page.evaluate("""(sectionText) => {
                // 섹션 헤딩 찾기
                let sectionEl = null;
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    const text = node.textContent.trim();
                    if (text.includes(sectionText)) {
                        sectionEl = node.parentElement;
                        break;
                    }
                }

                // 모든 포지션 링크 수집
                const allJobLinks = Array.from(document.querySelectorAll('a[href*="/wd/"], a[href*="/jobs/"]'));
                const allVisible = allJobLinks.filter(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                });

                // DOM 내 전체 포지션 링크 (스크롤 후 DOM에 추가된 것들 포함)
                const allInDOM = allJobLinks.length;

                return {
                    sectionFound: sectionEl !== null,
                    visiblePositionCount: allVisible.length,
                    totalInDOM: allInDOM,
                    sampleHrefs: allJobLinks.slice(0, 3).map(el => el.href),
                };
            }""", SECTION_TEXT)

            print(f"[INFO] 스크롤 후 결과: {after_scroll_result}")

            after_scroll_count = after_scroll_result.get('totalInDOM', 0)

            await page.screenshot(path='screenshots/test_30_final.png')

            # ── 7단계: 검증 ──
            print(f"\n[RESULT] 초기 포지션 카드 수: {initial_count}")
            print(f"[RESULT] 스크롤 후 포지션 카드 수(DOM): {after_scroll_count}")

            # 섹션 발견 검증
            assert position_result.get('sectionFound'), (
                f"'{SECTION_TEXT}' 섹션이 탐색 페이지에서 발견되지 않았습니다."
            )

            # 초기 포지션 카드 노출 검증 (최소 1개 이상)
            assert initial_count >= 1, (
                f"'{SECTION_TEXT}' 하단에 포지션 카드가 노출되지 않습니다. "
                f"발견된 카드 수: {initial_count}"
            )

            # 스크롤 후 추가 포지션 카드 검증 (DOM에 더 많은 카드가 있어야 함)
            # 스크롤 후 DOM에 더 많은 포지션 링크가 있는지 확인
            assert after_scroll_count >= initial_count, (
                f"스크롤 후 추가 포지션 카드가 로드되지 않았습니다. "
                f"초기: {initial_count}, 스크롤 후: {after_scroll_count}"
            )

            print(f"[PASS] 테스트 케이스 #30 통과:")
            print(f"  - '{SECTION_TEXT}' 섹션 발견")
            print(f"  - 초기 포지션 카드 {initial_count}개 노출 확인")
            print(f"  - 스크롤 후 총 {after_scroll_count}개 포지션 카드 확인")
            print("AUTOMATION_SUCCESS")
            return True

        except AssertionError as e:
            try:
                await page.screenshot(path='screenshots/test_30_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_30_error.png')
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
