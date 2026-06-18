import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest
import re

SEARCH_TERM = "카카오"

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

            # 5. 회사 탭 찾기 및 클릭
            # 검색 결과 페이지에서 회사 탭 확인
            company_tab = None

            # 방법1: href에 tab=company 포함된 링크
            company_tab_link = page.locator('a[href*="tab=company"]').first
            if await company_tab_link.count() > 0:
                await company_tab_link.wait_for(state='visible', timeout=5000)
                await company_tab_link.click()
                await page.wait_for_load_state('load')
                await page.wait_for_timeout(3000)
                print("회사 탭(tab=company) 클릭 완료")
            else:
                # 방법2: "회사" 텍스트가 있는 탭 찾기
                tab_links = await page.evaluate("""() => {
                    const allLinks = [...document.querySelectorAll('a')];
                    return allLinks
                        .filter(a => a.innerText.trim() === '회사' || a.innerText.includes('회사'))
                        .slice(0, 5)
                        .map(a => ({
                            href: a.getAttribute('href'),
                            text: a.innerText.trim().substring(0, 30)
                        }));
                }""")
                print(f"회사 관련 탭 링크들: {tab_links}")

                if tab_links:
                    company_tab_href = tab_links[0]['href']
                    company_tab_el = page.locator(f'a[href="{company_tab_href}"]').first
                    await company_tab_el.click()
                    await page.wait_for_load_state('load')
                    await page.wait_for_timeout(3000)
                    print(f"회사 탭 클릭 완료: {company_tab_href}")
                else:
                    print("회사 탭을 찾지 못함 - 현재 페이지에서 회사 항목 탐색")

            print(f"회사 탭 클릭 후 URL: {page.url}")

            # 6. 회사 항목 확인 - /company/{id} 링크 탐색
            company_links = await page.evaluate("""() => {
                const allLinks = [...document.querySelectorAll('a[href]')];
                const companyLinks = allLinks.filter(a => /\\/company\\/\\d+/.test(a.getAttribute('href') || ''));
                return companyLinks.slice(0, 10).map(a => ({
                    href: a.getAttribute('href'),
                    text: a.innerText.trim().substring(0, 50),
                    visible: a.offsetParent !== null
                }));
            }""")

            print(f"발견된 /company/ 링크: {company_links}")

            if len(company_links) == 0:
                # 대안: 페이지의 모든 visible a 태그 확인 (디버깅용)
                debug_links = await page.evaluate("""() => {
                    const allLinks = [...document.querySelectorAll('a[href]')].slice(0, 100);
                    return allLinks
                        .filter(a => a.offsetParent !== null)
                        .map(a => a.getAttribute('href'))
                        .filter(h => h && (h.startsWith('/') || h.startsWith('http')))
                        .slice(0, 40);
                }""")
                print(f"visible 링크들: {debug_links}")

            assert len(company_links) > 0, "회사 /company/ 링크가 검색 결과에 없음"
            print(f"회사 항목 수: {len(company_links)}")

            # 7. 첫 번째 회사 선택 (visible한 항목 우선)
            visible_links = [l for l in company_links if l.get('visible', False)]
            target_link = visible_links[0] if visible_links else company_links[0]
            target_href = target_link['href']
            print(f"선택할 회사 href: {target_href}, 텍스트: {target_link['text']}")

            # 8. 회사 클릭 후 URL 변경 대기
            navigation_promise = page.wait_for_url(lambda url: '/company/' in url, timeout=15000)
            await page.evaluate("""(href) => {
                const el = document.querySelector('a[href="' + href + '"]');
                if (el) { el.click(); }
            }""", target_href)

            await navigation_promise
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(1000)
            final_url = page.url
            print(f"이동된 URL: {final_url}")

            # 9. 회사 상세 페이지 URL 확인 (/company/{id} 패턴)
            assert re.search(r'/company/\d+', final_url), f"회사 상세 페이지로 이동되지 않음. URL: {final_url}"
            print(f"✅ 회사 상세 페이지 이동 확인: {final_url}")

            await page.screenshot(path='screenshots/test_56_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_56_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
