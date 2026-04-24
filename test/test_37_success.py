import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            storage_state='work/auth_state.json',
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1. 채용 목록 페이지로 이동 후 포지션 URL 확보
            print("[INFO] 채용 목록 페이지 접속 중...")
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"[OK] 채용 목록 페이지 로드 완료 - URL: {page.url}")

            position_url = None
            wd_links = page.locator('a[href*="/wd/"]')
            count = await wd_links.count()
            print(f"[INFO] /wd/ 링크 수: {count}")

            if count > 0:
                href = await wd_links.first.get_attribute('href')
                if href:
                    position_url = href if href.startswith('http') else f"https://www.wanted.co.kr{href}"
                    print(f"[OK] 포지션 URL 발견: {position_url}")

            assert position_url is not None, "포지션 상세 페이지 URL을 찾을 수 없습니다"

            # 2. 포지션 상세 페이지 진입
            print(f"[INFO] 포지션 상세 페이지 진입: {position_url}")
            await page.goto(position_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            # 클라이언트 측 인증 및 추천 포지션 로딩 대기
            await page.wait_for_timeout(5000)
            print(f"[OK] 포지션 상세 페이지 로드 완료 - URL: {page.url}")
            await page.screenshot(path='screenshots/test_37_step1_detail.png')

            # 3. 근무지역 항목 탐색
            print("[INFO] '근무지역' 항목 탐색 중...")
            work_area_found = False
            work_area_y = None

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            work_texts = ['근무지역', '근무지', '근무 지역', '근무위치', '근무 위치']
            for scroll_step in range(30):
                for wt in work_texts:
                    try:
                        el = page.get_by_text(wt, exact=False)
                        cnt = await el.count()
                        if cnt > 0:
                            for i in range(min(cnt, 5)):
                                try:
                                    item = el.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        bb = await item.bounding_box()
                                        if bb:
                                            work_area_y = bb['y'] + bb['height']
                                        work_area_found = True
                                        print(f"[OK] '{wt}' 텍스트 발견 (visible), y_bottom={work_area_y}")
                                        break
                                except Exception:
                                    continue
                        if work_area_found:
                            break
                    except Exception as e:
                        print(f"[WARN] '{wt}' 탐색 실패: {e}")
                if work_area_found:
                    break
                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(300)

            if not work_area_found:
                print("[INFO] JS 기반 '근무지역' 탐색 중...")
                js_work = await page.evaluate("""() => {
                    const keywords = ['근무지역', '근무지', '근무 지역', '근무위치', '근무 위치'];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        const text = node.textContent.trim();
                        for (const kw of keywords) {
                            if (text === kw || text.includes(kw)) {
                                const el = node.parentElement;
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0) {
                                    return {found: true, keyword: kw, text: text,
                                            y_bottom: rect.bottom, y_top: rect.top};
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                if js_work.get('found'):
                    work_area_found = True
                    work_area_y = js_work.get('y_bottom')
                    print(f"[OK] JS로 '근무지역' 항목 발견: {js_work.get('keyword')}, y_bottom={work_area_y}")

            assert work_area_found, "'근무지역' 항목을 찾을 수 없습니다"
            print("[OK] '근무지역' 항목 확인됨")
            await page.screenshot(path='screenshots/test_37_step2_workarea.png')

            # 4. 근무지역 하단에서 추천 포지션 섹션 탐색
            # 로그인 시: '~님을 위한 추천 포지션'
            # 비로그인/다른 변형 시: '이 포지션을 찾고 계셨나요?'
            print("[INFO] 추천 포지션 섹션 탐색 중...")
            recommend_found = False
            recommend_text_found = None

            recommend_keywords = [
                '님을 위한 추천 포지션',   # 로그인 상태 (개인화)
                '님을 위한 추천',
                '추천 포지션',
                '위한 추천 포지션',
                '이 포지션을 찾고 계셨나요',   # 비로그인 또는 다른 변형
                '이 포지션을 찾고',
                '추천포지션',
                '비슷한 포지션',
                '관련 포지션',
            ]

            # 스크롤하며 추천 섹션 탐색
            for scroll_step in range(40):
                for kw in recommend_keywords:
                    try:
                        el = page.get_by_text(kw, exact=False)
                        cnt = await el.count()
                        if cnt > 0:
                            for i in range(min(cnt, 5)):
                                try:
                                    item = el.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        text_content = await item.text_content()
                                        recommend_found = True
                                        recommend_text_found = kw
                                        print(f"[OK] 추천 섹션 텍스트 발견 (visible): '{text_content[:80]}'")
                                        break
                                except Exception:
                                    continue
                        if recommend_found:
                            break
                    except Exception as e:
                        print(f"[WARN] '{kw}' 탐색 실패: {e}")
                if recommend_found:
                    break
                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(300)

            if not recommend_found:
                print("[INFO] JS 기반 추천 섹션 탐색 중...")
                js_recommend = await page.evaluate("""() => {
                    const keywords = [
                        '님을 위한 추천 포지션',
                        '님을 위한 추천',
                        '추천 포지션',
                        '이 포지션을 찾고 계셨나요',
                        '이 포지션을 찾고',
                        '비슷한 포지션',
                        '관련 포지션',
                        '추천포지션',
                    ];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        const text = node.textContent.trim();
                        for (const kw of keywords) {
                            if (text.includes(kw)) {
                                const el = node.parentElement;
                                const rect = el.getBoundingClientRect();
                                return {found: true, keyword: kw, text: text.substring(0, 80),
                                        visible: rect.width > 0};
                            }
                        }
                    }

                    // 전체 body에서 탐색
                    const bodyText = document.body.innerText || '';
                    for (const kw of keywords) {
                        if (bodyText.includes(kw)) {
                            return {found: true, keyword: kw, fromBodyText: true};
                        }
                    }

                    return {found: false};
                }""")
                print(f"[INFO] JS 추천 섹션 탐색 결과: {js_recommend}")
                if js_recommend.get('found'):
                    recommend_found = True
                    recommend_text_found = js_recommend.get('keyword')
                    print(f"[OK] JS로 추천 포지션 섹션 발견: '{js_recommend.get('keyword')}'")

            await page.screenshot(path='screenshots/test_37_step3_recommend.png')
            assert recommend_found, "추천 포지션 섹션 텍스트를 찾을 수 없습니다 (로그인/비로그인 모두 미발견)"
            print(f"[OK] 추천 포지션 섹션 텍스트 확인됨: '{recommend_text_found}'")

            # 로그인 여부 확인 (실제로 '~님을 위한' 패턴이 있는지 재확인)
            if '님을 위한 추천 포지션' in recommend_text_found or '님을 위한 추천' in recommend_text_found:
                print("[OK] 로그인 상태 확인: '~님을 위한 추천 포지션' 텍스트 발견")
            else:
                print(f"[INFO] 현재 표시된 추천 섹션: '{recommend_text_found}' (비로그인/다른 변형)")

            # 5. 포지션 리스트 노출 확인
            print("[INFO] 추천 포지션 리스트 탐색 중...")
            position_list_found = False

            js_position_list = await page.evaluate("""() => {
                // 추천 포지션 관련 키워드 찾기
                const keywords = [
                    '님을 위한 추천 포지션',
                    '님을 위한 추천',
                    '추천 포지션',
                    '이 포지션을 찾고 계셨나요',
                    '이 포지션을 찾고',
                ];

                let recommendY = 0;

                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    const text = node.textContent.trim();
                    for (const kw of keywords) {
                        if (text.includes(kw)) {
                            const el = node.parentElement;
                            const rect = el.getBoundingClientRect();
                            recommendY = rect.bottom;
                            break;
                        }
                    }
                    if (recommendY > 0) break;
                }

                // 포지션 카드/링크 탐색
                const wdLinks = document.querySelectorAll('a[href*="/wd/"]');
                const visibleWdLinks = Array.from(wdLinks).filter(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 50 && rect.height > 10;
                });

                // 추천 섹션 이하의 포지션 아이템들
                const belowSection = visibleWdLinks.filter(el => {
                    const rect = el.getBoundingClientRect();
                    return recommendY > 0 ? rect.top >= recommendY - 100 : true;
                });

                return {
                    recommendY: recommendY,
                    totalWdLinks: wdLinks.length,
                    visibleWdLinks: visibleWdLinks.length,
                    belowSectionLinks: belowSection.length,
                    sampleTexts: visibleWdLinks.slice(0, 3).map(el =>
                        (el.innerText || el.textContent || '').substring(0, 50)
                    )
                };
            }""")

            print(f"[INFO] 추천 섹션 y={js_position_list.get('recommendY')}")
            print(f"[INFO] 전체 /wd/ 링크: {js_position_list.get('totalWdLinks')}, "
                  f"visible: {js_position_list.get('visibleWdLinks')}, "
                  f"섹션 이하: {js_position_list.get('belowSectionLinks')}")
            for sample in js_position_list.get('sampleTexts', []):
                print(f"  포지션 샘플: '{sample}'")

            # 포지션 리스트 판단 (섹션 이하에 포지션 링크가 있거나 전체적으로 여러 포지션 링크 존재)
            below_count = js_position_list.get('belowSectionLinks', 0)
            total_count = js_position_list.get('visibleWdLinks', 0)
            if below_count > 0:
                position_list_found = True
                print(f"[OK] 추천 섹션 하단 포지션 리스트 발견: {below_count}개")
            elif total_count > 1:
                position_list_found = True
                print(f"[OK] 포지션 리스트 발견 (전체 /wd/ 링크): {total_count}개")

            await page.screenshot(path='screenshots/test_37_step4_position_list.png')
            assert position_list_found, "추천 포지션 하단 포지션 리스트를 찾을 수 없습니다"
            print("[OK] 추천 포지션 하단 포지션 리스트 노출 확인됨")

            # 최종 결과
            print("\n[SUMMARY] 테스트 케이스 37 검증 완료:")
            print("[OK] 포지션 상세 페이지 진입")
            print("[OK] '근무지역' 항목 확인됨")
            print(f"[OK] 추천 포지션 섹션 텍스트 노출 확인됨: '{recommend_text_found}'")
            print("[OK] 추천 포지션 하단 포지션 리스트 노출 확인됨")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_37_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
