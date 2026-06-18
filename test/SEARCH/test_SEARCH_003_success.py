import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest
import re

SEARCH_TERM = "개발자"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1. 채용 홈 진입 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(2000)

            # 2. GNB 검색 버튼 클릭
            search_btn = page.get_by_role('button', name='검색')
            await search_btn.wait_for(state='visible', timeout=10000)
            await search_btn.click()
            await page.wait_for_timeout(1000)

            # 3. 검색어 입력 후 검색 실행
            search_input = page.locator('input[type="search"]')
            await search_input.wait_for(state='visible', timeout=10000)
            await search_input.fill(SEARCH_TERM)
            await page.wait_for_timeout(500)
            await page.keyboard.press('Enter')
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)

            # 4. 검색 결과 페이지 확인
            current_url = page.url
            assert 'search' in current_url.lower(), f"검색 결과 페이지 이동 실패: {current_url}"
            print(f"검색 결과 페이지: {current_url}")

            # 5. 포지션 탭 클릭
            position_tab = page.locator('a[href*="tab=position"]').first
            await position_tab.wait_for(state='visible', timeout=10000)
            await position_tab.click()
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)

            print(f"포지션 탭 클릭 후 URL: {page.url}")

            # 6. 포지션 항목 확인 - DOM에서 /wd/ 링크 찾기
            position_links = await page.evaluate("""() => {
                const allLinks = [...document.querySelectorAll('a[href]')];
                const wdLinks = allLinks.filter(a => /\\/wd\\/\\d+/.test(a.getAttribute('href') || ''));
                return wdLinks.slice(0, 5).map(a => ({
                    href: a.getAttribute('href'),
                    text: a.innerText.trim().substring(0, 50),
                    visible: a.offsetParent !== null
                }));
            }""")

            print(f"발견된 /wd/ 링크: {position_links}")

            if len(position_links) == 0:
                # 대안: 페이지의 모든 visible a 태그 확인
                debug_links = await page.evaluate("""() => {
                    const allLinks = [...document.querySelectorAll('a[href]')].slice(0, 80);
                    return allLinks
                        .filter(a => a.offsetParent !== null)
                        .map(a => a.getAttribute('href'))
                        .filter(h => h && h.startsWith('/') || h.startsWith('http'))
                        .slice(0, 30);
                }""")
                print(f"visible 링크들: {debug_links}")

                # 포지션 카드 요소 구조 파악
                dom_structure = await page.evaluate("""() => {
                    const items = [...document.querySelectorAll('li, article, [role="listitem"]')].slice(0, 20);
                    return items.map(el => ({
                        tag: el.tagName,
                        classes: el.className.substring(0, 60),
                        hasLink: el.querySelector('a') ? el.querySelector('a').getAttribute('href') : null
                    })).filter(el => el.hasLink);
                }""")
                print(f"링크를 포함한 목록 요소들: {dom_structure[:10]}")

            assert len(position_links) > 0, "포지션 /wd/ 링크가 검색 결과에 없음"
            print(f"포지션 항목 수: {len(position_links)}")

            # 7. 첫 번째 포지션 클릭
            first_href = position_links[0]['href']
            print(f"선택할 포지션 href: {first_href}")

            # 포지션 카드가 보이지 않는 경우 (virtual scroll 등) JS로 클릭
            first_position = page.locator(f'a[href="{first_href}"]').first

            # JS로 직접 클릭 후 URL 변경 감지
            navigation_promise = page.wait_for_url(lambda url: '/wd/' in url, timeout=15000)
            await page.evaluate("""(href) => {
                const el = document.querySelector('a[href="' + href + '"]');
                if (el) { el.click(); }
            }""", first_href)

            await navigation_promise
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(1000)
            final_url = page.url
            print(f"이동된 URL: {final_url}")

            # 8. 포지션 상세 페이지 URL 확인 (/wd/{id} 패턴)
            assert re.search(r'/wd/\d+', final_url), f"포지션 상세 페이지로 이동되지 않음. URL: {final_url}"
            print(f"✅ 포지션 상세 페이지 이동 확인: {final_url}")

            await page.screenshot(path='screenshots/test_55_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_55_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
