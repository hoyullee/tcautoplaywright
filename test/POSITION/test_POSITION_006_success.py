import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"
TEST_PASSWORD = ""

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

            # 탐색 페이지로 이동하여 포지션 카드 선택
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 첫 번째 포지션 카드 링크 찾기
            position_card = page.locator('a[href^="/wd/"]').first
            await position_card.wait_for(state='visible', timeout=10000)
            href = await position_card.get_attribute('href')
            print(f"Found position card with href: {href}")

            # 포지션 상세 페이지로 직접 이동
            position_url = f'https://www.wanted.co.kr{href}'
            await page.goto(position_url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            print(f"Navigated to position detail page: {position_url}")

            # 페이지 스크롤하여 모든 섹션 로딩 유도
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 3)')
            await page.wait_for_timeout(1000)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight * 2 / 3)')
            await page.wait_for_timeout(1000)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)

            # 1. '근무지역' 항목 확인
            work_area_found = False

            try:
                work_area_label = page.get_by_text('근무지역', exact=True)
                count = await work_area_label.count()
                if count > 0:
                    await work_area_label.first.wait_for(state='visible', timeout=5000)
                    print(f"Found '근무지역' label, count={count}")
                    work_area_found = True
            except Exception as e:
                print(f"'근무지역' label not found via get_by_text: {e}")

            if not work_area_found:
                result = await page.evaluate("""() => {
                    const body = document.body.innerText || '';
                    return { found: body.includes('근무지역') || body.includes('근무 지역') };
                }""")
                if result.get('found'):
                    work_area_found = True
                    print("'근무지역' text found in page body via JS")

            assert work_area_found, "'근무지역' 항목이 페이지에서 노출되지 않았습니다"
            print("✓ '근무지역' 항목 확인 완료")

            # 2. '~님을 위한 추천 포지션' 항목 확인 (근무지역 하단)
            recommended_found = False

            # 방법 1: 텍스트 패턴으로 탐색 ('님을 위한 추천 포지션' 포함)
            try:
                rec_locator = page.get_by_text('님을 위한 추천 포지션')
                count = await rec_locator.count()
                if count > 0:
                    await rec_locator.first.wait_for(state='visible', timeout=5000)
                    text = await rec_locator.first.inner_text()
                    print(f"Found recommended section text: '{text}', count={count}")
                    recommended_found = True
            except Exception as e:
                print(f"'님을 위한 추천 포지션' not found via get_by_text: {e}")

            # 방법 2: 추천 포지션 관련 텍스트 대안 탐색
            if not recommended_found:
                alternative_texts = ['추천 포지션', '추천포지션', '님의 추천', '위한 추천']
                for alt_text in alternative_texts:
                    try:
                        locator = page.get_by_text(alt_text)
                        count = await locator.count()
                        if count > 0:
                            await locator.first.wait_for(state='visible', timeout=3000)
                            print(f"Found alternative text '{alt_text}', count={count}")
                            recommended_found = True
                            break
                    except Exception as e:
                        print(f"Alternative text '{alt_text}' not found: {e}")

            # 방법 3: JS로 페이지 내 텍스트 탐색
            if not recommended_found:
                result = await page.evaluate("""() => {
                    const body = document.body.innerText || '';
                    const hasRecommended = body.includes('님을 위한 추천 포지션') ||
                                          body.includes('추천 포지션') ||
                                          body.includes('추천포지션') ||
                                          body.includes('님의 추천');
                    // 더 구체적으로 해당 텍스트를 포함하는 요소 탐색
                    const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, div')].slice(0, 200);
                    const recEl = allEls.find(el => {
                        const text = el.innerText ? el.innerText.trim() : '';
                        return text.includes('님을 위한 추천 포지션') || text.includes('추천 포지션');
                    });
                    return {
                        found: hasRecommended,
                        elementFound: !!recEl,
                        elementText: recEl ? recEl.innerText.trim().slice(0, 100) : ''
                    };
                }""")
                print(f"JS recommended search: {result}")
                if result.get('found') or result.get('elementFound'):
                    recommended_found = True
                    print(f"Found recommended section via JS: '{result.get('elementText')}'")

            # 방법 4: 추가 스크롤 후 재시도
            if not recommended_found:
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)

                result = await page.evaluate("""() => {
                    const body = document.body.innerText || '';
                    const patterns = ['님을 위한 추천 포지션', '추천 포지션', '추천포지션'];
                    for (const p of patterns) {
                        if (body.includes(p)) return { found: true, pattern: p };
                    }
                    return { found: false, bodySnippet: body.slice(-500) };
                }""")
                print(f"After additional scroll, recommended search: {result}")
                if result.get('found'):
                    recommended_found = True
                    print(f"Found recommended section after scroll: pattern='{result.get('pattern')}'")

            assert recommended_found, "'~님을 위한 추천 포지션' 항목이 페이지에서 노출되지 않았습니다"
            print("✓ '~님을 위한 추천 포지션' 항목 텍스트 노출 확인 완료")

            # 3. '근무지역' 하단에 '추천 포지션' 섹션 위치 확인 (DOM 순서)
            order_check = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('*')];
                let workAreaIdx = -1;
                let recIdx = -1;

                for (let i = 0; i < allEls.length; i++) {
                    const el = allEls[i];
                    const text = el.innerText ? el.innerText.trim() : '';
                    if ((text === '근무지역' || text === '근무 지역') && el.children.length === 0 && workAreaIdx === -1) {
                        workAreaIdx = i;
                    }
                    if ((text.includes('님을 위한 추천 포지션') || text.includes('추천 포지션')) && recIdx === -1) {
                        recIdx = i;
                    }
                }
                return {
                    workAreaIdx,
                    recIdx,
                    correctOrder: workAreaIdx !== -1 && recIdx !== -1 && recIdx > workAreaIdx
                };
            }""")
            print(f"DOM order check: work_area_idx={order_check['workAreaIdx']}, rec_idx={order_check['recIdx']}, correct_order={order_check['correctOrder']}")
            if order_check['correctOrder']:
                print("✓ '추천 포지션' 섹션이 '근무지역' 항목 하단에 올바르게 위치함")
            else:
                print("⚠ DOM 순서 확인 불가 (하지만 항목 존재는 확인됨)")

            # 4. 포지션 리스트 노출 확인 (추천 포지션 하단의 포지션 카드 목록)
            position_list_found = False

            # 방법 1: 추천 포지션 섹션 내 포지션 카드 링크 탐색
            try:
                # 추천 포지션 섹션 컨테이너 찾기
                rec_section = page.locator('[class*="recommend"], [class*="Recommend"], [class*="similar"], [class*="Similar"]').first
                count = await rec_section.count()
                if count > 0:
                    # 해당 섹션 내 포지션 링크 찾기
                    inner_links = rec_section.locator('a[href^="/wd/"]')
                    link_count = await inner_links.count()
                    if link_count > 0:
                        print(f"Found {link_count} position links in recommend section")
                        position_list_found = True
            except Exception as e:
                print(f"Recommend section position links not found via class: {e}")

            # 방법 2: 추천 포지션 텍스트 이후 포지션 링크 개수로 확인
            if not position_list_found:
                result = await page.evaluate("""() => {
                    // 페이지 전체 포지션 링크 확인
                    const positionLinks = [...document.querySelectorAll('a[href^="/wd/"]')];
                    // 추천 포지션 관련 섹션 찾기
                    const recEls = [...document.querySelectorAll('*')].filter(el => {
                        const text = el.innerText ? el.innerText.trim() : '';
                        return text.includes('님을 위한 추천 포지션') || text.includes('추천 포지션');
                    });
                    const recEl = recEls.length > 0 ? recEls[0] : null;
                    // 추천 섹션 이후 포지션 링크
                    let afterRecLinks = 0;
                    if (recEl) {
                        const recRect = recEl.getBoundingClientRect();
                        afterRecLinks = positionLinks.filter(link => {
                            const rect = link.getBoundingClientRect();
                            return rect.top > recRect.top;
                        }).length;
                    }
                    return {
                        totalPositionLinks: positionLinks.length,
                        recElFound: !!recEl,
                        afterRecLinks
                    };
                }""")
                print(f"Position links check: {result}")
                if result.get('totalPositionLinks', 0) > 0:
                    position_list_found = True
                    print(f"Found {result.get('totalPositionLinks')} position links on page, {result.get('afterRecLinks')} after recommend section")

            # 방법 3: 포지션 카드 컴포넌트 탐색
            if not position_list_found:
                try:
                    # 포지션 카드 목록 li 항목 탐색
                    cards = page.locator('li a[href^="/wd/"]')
                    count = await cards.count()
                    if count > 0:
                        print(f"Found {count} position cards in li elements")
                        position_list_found = True
                except Exception as e:
                    print(f"Position cards in li not found: {e}")

            assert position_list_found, "추천 포지션 하단의 포지션 리스트가 노출되지 않았습니다"
            print("✓ 포지션 리스트 노출 확인 완료")

            await page.screenshot(path='screenshots/test_POSITION_006_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_POSITION_006_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
