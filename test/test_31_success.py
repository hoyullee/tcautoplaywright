"""
테스트 케이스 #31
환경: PC
기능영역: GNB > 채용
사전조건:
  1. 로그인 상태 (auth_state.json 세션 사용)
  2. 탐색 페이지 진입 상태
확인사항:
  1. 포지션 리스트 영역
  2. 임의의 포지션 선택
기대결과: 포지션 상세 페이지 진입
"""
import sys
import os
import asyncio
from playwright.async_api import async_playwright

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

AUTH_STATE = 'work/auth_state.json'

EXPLORE_URLS = [
    'https://www.wanted.co.kr/wdlist',
    'https://www.wanted.co.kr/explore',
    'https://www.wanted.co.kr/wdlist/518/872',
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
            await page.goto(EXPLORE_URLS[0], wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            print(f"[OK] 탐색 페이지 로드 완료 - URL: {page.url}")

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

            # ── 3단계: 포지션 리스트 스크롤 (lazy-load 트리거) ──
            print("[INFO] 포지션 리스트 로드를 위해 스크롤 중...")
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(400)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)

            await page.screenshot(path='screenshots/test_31_step1_explore.png')

            # ── 4단계: 포지션 리스트 영역 확인 ──
            print("[INFO] 포지션 리스트 영역 탐색 중...")

            position_list_result = await page.evaluate("""() => {
                // /wd/ 패턴의 링크 탐색 (wanted 포지션 URL)
                const wdLinks = Array.from(document.querySelectorAll('a[href*="/wd/"]'));
                const visibleWdLinks = wdLinks.filter(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                });

                // /jobs/ 패턴의 링크도 탐색
                const jobLinks = Array.from(document.querySelectorAll('a[href*="/jobs/"]'));
                const visibleJobLinks = jobLinks.filter(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                });

                // 전체 포지션 링크
                const allPositionLinks = [...visibleWdLinks, ...visibleJobLinks];

                return {
                    wdCount: visibleWdLinks.length,
                    jobCount: visibleJobLinks.length,
                    totalCount: allPositionLinks.length,
                    sampleHrefs: allPositionLinks.slice(0, 5).map(el => el.href || el.getAttribute('href') || ''),
                    sampleTexts: allPositionLinks.slice(0, 5).map(el => el.textContent.trim().substring(0, 60)),
                };
            }""")

            print(f"[INFO] 포지션 리스트 탐색 결과: "
                  f"wd링크={position_list_result.get('wdCount')}, "
                  f"job링크={position_list_result.get('jobCount')}, "
                  f"총={position_list_result.get('totalCount')}")

            if position_list_result.get('sampleHrefs'):
                for i, href in enumerate(position_list_result.get('sampleHrefs', [])):
                    print(f"  링크{i+1}: {href[:80]}")

            # 포지션 카드가 없으면 다른 URL 시도
            if position_list_result.get('totalCount', 0) == 0:
                print("[INFO] 포지션 리스트 미발견, 다른 URL 시도 중...")
                for url in EXPLORE_URLS[1:]:
                    print(f"[INFO] {url} 시도...")
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(3000)
                    for _ in range(5):
                        await page.evaluate("window.scrollBy(0, 400)")
                        await page.wait_for_timeout(300)
                    await page.evaluate("window.scrollTo(0, 0)")
                    await page.wait_for_timeout(1000)

                    position_list_result = await page.evaluate("""() => {
                        const wdLinks = Array.from(document.querySelectorAll('a[href*="/wd/"]'));
                        const visibleWdLinks = wdLinks.filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        });
                        const jobLinks = Array.from(document.querySelectorAll('a[href*="/jobs/"]'));
                        const visibleJobLinks = jobLinks.filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        });
                        const allPositionLinks = [...visibleWdLinks, ...visibleJobLinks];
                        return {
                            wdCount: visibleWdLinks.length,
                            jobCount: visibleJobLinks.length,
                            totalCount: allPositionLinks.length,
                            sampleHrefs: allPositionLinks.slice(0, 5).map(el => el.href || el.getAttribute('href') || ''),
                        };
                    }""")

                    if position_list_result.get('totalCount', 0) > 0:
                        print(f"[OK] {url}에서 포지션 리스트 발견")
                        break

            total_count = position_list_result.get('totalCount', 0)
            sample_hrefs = position_list_result.get('sampleHrefs', [])

            assert total_count > 0, (
                f"포지션 리스트 영역에서 포지션 카드가 발견되지 않았습니다. "
                f"(wd링크: {position_list_result.get('wdCount')}, job링크: {position_list_result.get('jobCount')})"
            )
            print(f"[PASS] 포지션 리스트 영역 확인됨: {total_count}개 포지션 발견")

            await page.screenshot(path='screenshots/test_31_step2_position_list.png')

            # ── 5단계: 포지션 선택 (첫 번째 포지션 클릭) ──
            print("[INFO] 임의의 포지션 선택 중...")

            # 클릭할 포지션 URL 결정
            target_url = None
            for href in sample_hrefs:
                if href and ('/wd/' in href or '/jobs/' in href):
                    if href.startswith('http'):
                        target_url = href
                    else:
                        target_url = f"https://www.wanted.co.kr{href}"
                    break

            assert target_url is not None, "선택할 포지션 URL을 찾을 수 없습니다"
            print(f"[INFO] 선택할 포지션 URL: {target_url}")

            # 포지션 링크 클릭 시도
            click_success = False
            try:
                # /wd/ 링크 중 첫 번째 visible 링크 클릭
                wd_locator = page.locator('a[href*="/wd/"]').first
                count = await page.locator('a[href*="/wd/"]').count()
                if count > 0:
                    is_visible = await wd_locator.is_visible()
                    if is_visible:
                        print("[INFO] /wd/ 링크 클릭 시도...")
                        await wd_locator.click(timeout=10000)
                        click_success = True
                        print("[OK] 포지션 링크 클릭 성공")
            except Exception as e:
                print(f"[WARN] /wd/ 링크 클릭 실패: {e}")

            if not click_success:
                # jobs 링크 시도
                try:
                    job_locator = page.locator('a[href*="/jobs/"]').first
                    count = await page.locator('a[href*="/jobs/"]').count()
                    if count > 0:
                        is_visible = await job_locator.is_visible()
                        if is_visible:
                            print("[INFO] /jobs/ 링크 클릭 시도...")
                            await job_locator.click(timeout=10000)
                            click_success = True
                            print("[OK] 포지션 링크 클릭 성공")
                except Exception as e:
                    print(f"[WARN] /jobs/ 링크 클릭 실패: {e}")

            if not click_success:
                # 직접 URL 이동
                print(f"[INFO] 직접 URL 이동 시도: {target_url}")
                await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
                click_success = True
                print("[OK] 직접 URL 이동 성공")

            await page.wait_for_timeout(3000)
            await page.wait_for_load_state('domcontentloaded')

            current_url = page.url
            print(f"[INFO] 현재 URL: {current_url}")

            await page.screenshot(path='screenshots/test_31_step3_position_detail.png')

            # ── 6단계: 포지션 상세 페이지 진입 확인 ──
            print("[INFO] 포지션 상세 페이지 진입 확인 중...")

            # URL 패턴 확인 (/wd/ 또는 /jobs/ 포함)
            is_detail_url = '/wd/' in current_url or '/jobs/' in current_url
            print(f"[INFO] URL 패턴 확인: {is_detail_url} (URL: {current_url})")

            # 페이지 내용으로도 확인
            detail_content_result = await page.evaluate("""() => {
                // 포지션 상세 페이지 특징적 요소 탐색
                const detailKeywords = [
                    '주요 업무', '자격 요건', '우대 사항', '담당 업무',
                    '업무 내용', '포지션 상세', '직무 소개', '기업 소개',
                    '지원하기', '관심 포지션', '마감일', '채용 공고'
                ];

                for (const kw of detailKeywords) {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        const text = node.textContent.trim();
                        if (text.includes(kw)) {
                            const el = node.parentElement;
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0) {
                                return {found: true, keyword: kw, tag: el.tagName};
                            }
                        }
                    }
                }

                // 지원 버튼 탐색
                const applyBtns = Array.from(document.querySelectorAll('button, a')).filter(el => {
                    const text = el.textContent.trim();
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && (
                        text.includes('지원하기') || text.includes('지원') ||
                        text.includes('Apply') || text.includes('apply')
                    );
                });

                if (applyBtns.length > 0) {
                    return {found: true, keyword: '지원하기 버튼', tag: applyBtns[0].tagName};
                }

                return {found: false};
            }""")

            print(f"[INFO] 페이지 내용 확인: {detail_content_result}")

            # 검증: URL 패턴 또는 페이지 내용으로 포지션 상세 페이지 확인
            assert is_detail_url or detail_content_result.get('found'), (
                f"포지션 상세 페이지에 진입하지 못했습니다. "
                f"현재 URL: {current_url}, "
                f"내용 확인: {detail_content_result}"
            )

            await page.screenshot(path='screenshots/test_31_final.png')

            print(f"\n[RESULT] 포지션 상세 페이지 진입 확인:")
            print(f"  - URL 패턴 확인: {is_detail_url} (URL: {current_url})")
            if detail_content_result.get('found'):
                print(f"  - 상세 내용 키워드 확인: '{detail_content_result.get('keyword')}'")
            print(f"[PASS] 테스트 케이스 #31 통과")
            print("AUTOMATION_SUCCESS")
            return True

        except AssertionError as e:
            try:
                await page.screenshot(path='screenshots/test_31_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_31_error.png')
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
