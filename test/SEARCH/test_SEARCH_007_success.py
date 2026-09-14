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

            # 5. 프로필 탭 찾기 및 클릭
            profile_tab_clicked = False

            # 방법1: href에 tab=profile 포함된 링크
            for tab_param in ['tab=profile', 'tab=프로필']:
                profile_tab_link = page.locator(f'a[href*="{tab_param}"]').first
                if await profile_tab_link.count() > 0:
                    await profile_tab_link.wait_for(state='visible', timeout=5000)
                    await profile_tab_link.click()
                    await page.wait_for_load_state('load')
                    await page.wait_for_timeout(3000)
                    print(f"프로필 탭({tab_param}) 클릭 완료")
                    profile_tab_clicked = True
                    break

            if not profile_tab_clicked:
                # 방법2: "프로필" 텍스트가 있는 탭 찾기
                tab_links = await page.evaluate("""() => {
                    const allLinks = [...document.querySelectorAll('a')];
                    return allLinks
                        .filter(a => a.innerText.trim() === '프로필' || a.innerText.includes('프로필'))
                        .slice(0, 5)
                        .map(a => ({
                            href: a.getAttribute('href'),
                            text: a.innerText.trim().substring(0, 30)
                        }));
                }""")
                print(f"프로필 관련 탭 링크들: {tab_links}")

                if tab_links:
                    profile_tab_href = tab_links[0]['href']
                    profile_tab_el = page.locator(f'a[href="{profile_tab_href}"]').first
                    await profile_tab_el.click()
                    await page.wait_for_load_state('load')
                    await page.wait_for_timeout(3000)
                    print(f"프로필 탭 클릭 완료: {profile_tab_href}")
                    profile_tab_clicked = True
                else:
                    # 방법3: role=tab 으로 탭 찾기
                    tabs = page.locator('[role="tab"]')
                    tab_count = await tabs.count()
                    for i in range(tab_count):
                        tab = tabs.nth(i)
                        tab_text = await tab.inner_text()
                        if '프로필' in tab_text:
                            await tab.click()
                            await page.wait_for_load_state('load')
                            await page.wait_for_timeout(3000)
                            print(f"프로필 탭(role=tab) 클릭 완료: {tab_text}")
                            profile_tab_clicked = True
                            break

            print(f"프로필 탭 클릭 후 URL: {page.url}")

            # 6. 프로필 항목 확인 - social.wanted.co.kr/community/profile 링크 탐색
            profile_links = await page.evaluate("""() => {
                const allLinks = [...document.querySelectorAll('a[href]')];
                const profileLinks = allLinks.filter(a => {
                    const href = a.getAttribute('href') || '';
                    return /social\\.wanted\\.co\\.kr\\/community\\/profile\\//.test(href)
                        || href.includes('/community/profile/');
                });
                return profileLinks.slice(0, 10).map(a => ({
                    href: a.getAttribute('href'),
                    text: a.innerText.trim().substring(0, 50),
                    visible: a.offsetParent !== null
                }));
            }""")

            print(f"발견된 프로필 링크: {profile_links}")

            if len(profile_links) == 0:
                # 디버깅: 페이지의 visible a 태그 확인
                debug_links = await page.evaluate("""() => {
                    const allLinks = [...document.querySelectorAll('a[href]')].slice(0, 100);
                    return allLinks
                        .filter(a => a.offsetParent !== null)
                        .map(a => a.getAttribute('href'))
                        .filter(h => h && (h.includes('social') || h.includes('profile') || h.includes('community')))
                        .slice(0, 30);
                }""")
                print(f"social/profile/community 관련 링크들: {debug_links}")

                # 모든 visible 링크 확인
                all_visible_links = await page.evaluate("""() => {
                    const allLinks = [...document.querySelectorAll('a[href]')].slice(0, 150);
                    return allLinks
                        .filter(a => a.offsetParent !== null)
                        .map(a => a.getAttribute('href'))
                        .filter(h => h && (h.startsWith('/') || h.startsWith('http')))
                        .slice(0, 50);
                }""")
                print(f"모든 visible 링크들: {all_visible_links}")

                # 페이지 텍스트 확인
                page_text = await page.evaluate("() => document.body.innerText.substring(0, 2000)")
                print(f"페이지 텍스트: {page_text}")

            assert len(profile_links) > 0, "프로필 링크가 검색 결과에 없음"
            print(f"프로필 항목 수: {len(profile_links)}")

            # 7. 첫 번째 프로필 항목 선택 (visible한 항목 우선)
            visible_links = [l for l in profile_links if l.get('visible', False)]
            target_link = visible_links[0] if visible_links else profile_links[0]
            target_href = target_link['href']
            print(f"선택할 프로필 항목 href: {target_href}, 텍스트: {target_link['text']}")

            # 8. 프로필 항목 클릭 후 새 페이지 또는 URL 변경 대기
            # social.wanted.co.kr는 별도 도메인이므로 새 탭이 열릴 수 있음
            new_page_promise = context.wait_for_event('page', timeout=10000)

            await page.evaluate("""(href) => {
                const el = document.querySelector('a[href="' + href + '"]');
                if (el) { el.click(); }
            }""", target_href)

            try:
                new_page = await new_page_promise
                await new_page.wait_for_load_state('load', timeout=15000)
                await new_page.wait_for_timeout(1000)
                final_url = new_page.url
                print(f"새 탭에서 이동된 URL: {final_url}")
                active_page = new_page
            except Exception:
                # 새 탭이 열리지 않은 경우 현재 페이지 URL 확인
                await page.wait_for_load_state('load', timeout=10000)
                await page.wait_for_timeout(1000)
                final_url = page.url
                print(f"현재 탭에서 이동된 URL: {final_url}")
                active_page = page

            # 9. 프로필 상세 페이지 URL 확인
            # 기대: social.wanted.co.kr/community/profile/{id}
            is_valid_url = bool(re.search(
                r'social\.wanted\.co\.kr/community/profile/\w+',
                final_url
            ))
            assert is_valid_url, (
                f"프로필 상세 페이지로 이동되지 않음. URL: {final_url}\n"
                f"기대 패턴: social.wanted.co.kr/community/profile/{{id}}"
            )
            print(f"✅ 프로필 상세 페이지 이동 확인: {final_url}")

            await active_page.screenshot(path='screenshots/test_SEARCH_007_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_SEARCH_007_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
