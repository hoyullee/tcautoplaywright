import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest
import re

SEARCH_TERM = "마케팅"

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

            # 5. 콘텐츠 탭 찾기 및 클릭
            content_tab_clicked = False

            # 방법1: href에 tab=content 또는 tab=event 포함된 링크
            for tab_param in ['tab=content', 'tab=event', 'tab=콘텐츠']:
                content_tab_link = page.locator(f'a[href*="{tab_param}"]').first
                if await content_tab_link.count() > 0:
                    await content_tab_link.wait_for(state='visible', timeout=5000)
                    await content_tab_link.click()
                    await page.wait_for_load_state('load')
                    await page.wait_for_timeout(3000)
                    print(f"콘텐츠 탭({tab_param}) 클릭 완료")
                    content_tab_clicked = True
                    break

            if not content_tab_clicked:
                # 방법2: "콘텐츠" 텍스트가 있는 탭 찾기
                tab_links = await page.evaluate("""() => {
                    const allLinks = [...document.querySelectorAll('a')];
                    return allLinks
                        .filter(a => a.innerText.trim() === '콘텐츠' || a.innerText.includes('콘텐츠'))
                        .slice(0, 5)
                        .map(a => ({
                            href: a.getAttribute('href'),
                            text: a.innerText.trim().substring(0, 30)
                        }));
                }""")
                print(f"콘텐츠 관련 탭 링크들: {tab_links}")

                if tab_links:
                    content_tab_href = tab_links[0]['href']
                    content_tab_el = page.locator(f'a[href="{content_tab_href}"]').first
                    await content_tab_el.click()
                    await page.wait_for_load_state('load')
                    await page.wait_for_timeout(3000)
                    print(f"콘텐츠 탭 클릭 완료: {content_tab_href}")
                    content_tab_clicked = True
                else:
                    # 방법3: role=tab 으로 탭 찾기
                    tabs = page.locator('[role="tab"]')
                    tab_count = await tabs.count()
                    for i in range(tab_count):
                        tab = tabs.nth(i)
                        tab_text = await tab.inner_text()
                        if '콘텐츠' in tab_text:
                            await tab.click()
                            await page.wait_for_load_state('load')
                            await page.wait_for_timeout(3000)
                            print(f"콘텐츠 탭(role=tab) 클릭 완료: {tab_text}")
                            content_tab_clicked = True
                            break

            print(f"콘텐츠 탭 클릭 후 URL: {page.url}")

            # 6. 콘텐츠 항목 확인 - /events/{id} 링크 탐색
            event_links = await page.evaluate("""() => {
                const allLinks = [...document.querySelectorAll('a[href]')];
                const eventLinks = allLinks.filter(a => /\\/events\\/\\d+/.test(a.getAttribute('href') || ''));
                return eventLinks.slice(0, 10).map(a => ({
                    href: a.getAttribute('href'),
                    text: a.innerText.trim().substring(0, 50),
                    visible: a.offsetParent !== null
                }));
            }""")

            print(f"발견된 /events/ 링크: {event_links}")

            if len(event_links) == 0:
                # 디버깅: 페이지의 모든 visible a 태그 확인
                debug_links = await page.evaluate("""() => {
                    const allLinks = [...document.querySelectorAll('a[href]')].slice(0, 100);
                    return allLinks
                        .filter(a => a.offsetParent !== null)
                        .map(a => a.getAttribute('href'))
                        .filter(h => h && (h.startsWith('/') || h.startsWith('http')))
                        .slice(0, 50);
                }""")
                print(f"visible 링크들: {debug_links}")

                # 페이지 텍스트에서 콘텐츠 관련 항목 확인
                page_text = await page.evaluate("() => document.body.innerText.substring(0, 2000)")
                print(f"페이지 텍스트: {page_text}")

            assert len(event_links) > 0, "콘텐츠 /events/ 링크가 검색 결과에 없음"
            print(f"콘텐츠 항목 수: {len(event_links)}")

            # 7. 첫 번째 콘텐츠 선택 (visible한 항목 우선)
            visible_links = [l for l in event_links if l.get('visible', False)]
            target_link = visible_links[0] if visible_links else event_links[0]
            target_href = target_link['href']
            print(f"선택할 콘텐츠 href: {target_href}, 텍스트: {target_link['text']}")

            # 8. 콘텐츠 클릭 후 URL 변경 대기
            navigation_promise = page.wait_for_url(lambda url: '/events/' in url, timeout=15000)
            await page.evaluate("""(href) => {
                const el = document.querySelector('a[href="' + href + '"]');
                if (el) { el.click(); }
            }""", target_href)

            await navigation_promise
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(1000)
            final_url = page.url
            print(f"이동된 URL: {final_url}")

            # 9. 콘텐츠 상세 페이지 URL 확인 (/events/{id} 패턴)
            assert re.search(r'/events/\d+', final_url), f"콘텐츠 상세 페이지로 이동되지 않음. URL: {final_url}"
            print(f"✅ 콘텐츠 상세 페이지 이동 확인: {final_url}")

            await page.screenshot(path='screenshots/test_SEARCH_005_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_SEARCH_005_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
