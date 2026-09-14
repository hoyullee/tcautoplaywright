import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

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

            # 채용 홈 접속 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 1. '한 번쯤 가보고 싶은 회사' 섹션 찾기
            section_title = page.get_by_text('한 번쯤 가보고 싶은 회사', exact=True)
            await section_title.wait_for(state='visible', timeout=15000)
            assert await section_title.is_visible(), "'한 번쯤 가보고 싶은 회사' 텍스트가 보이지 않습니다"
            print("[OK] '한 번쯤 가보고 싶은 회사' 섹션 확인")

            # 섹션으로 스크롤
            await section_title.scroll_into_view_if_needed()
            await page.wait_for_timeout(800)

            # 2. evaluate를 사용하여 섹션 내 '전체보기' 링크의 href 찾기
            section_info = await page.evaluate("""() => {
                const headings = document.querySelectorAll('h2, h3, h4, strong, span, p, a');
                for (const heading of headings) {
                    if (heading.textContent && heading.textContent.trim() === '한 번쯤 가보고 싶은 회사') {
                        let parent = heading.parentElement;
                        for (let i = 0; i < 10; i++) {
                            if (!parent) break;
                            const links = parent.querySelectorAll('a');
                            for (const link of links) {
                                if (link.textContent && link.textContent.trim() === '전체보기') {
                                    return {
                                        found: true,
                                        href: link.getAttribute('href'),
                                        text: link.textContent.trim()
                                    };
                                }
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return { found: false };
            }""")
            print(f"Section info: {section_info}")

            view_all_btn = None

            if section_info.get('found') and section_info.get('href'):
                href = section_info['href']
                view_all_btn = page.locator(f'a[href="{href}"]').first
                print(f"[OK] '전체보기' 버튼 발견 (href: {href})")
            else:
                # 방법 2: 섹션 컨테이너 내에서 탐색
                section_container = page.locator('section, div').filter(
                    has=page.get_by_text('한 번쯤 가보고 싶은 회사', exact=True)
                ).first

                view_all_candidate = section_container.get_by_role('link', name='전체보기')
                if await view_all_candidate.count() > 0:
                    view_all_btn = view_all_candidate.first
                    print("[OK] '전체보기' 버튼 발견 (섹션 컨테이너 내)")
                else:
                    # 방법 3: 페이지 전체에서 tag 관련 '전체보기' 링크 찾기
                    all_view_links = page.get_by_role('link', name='전체보기')
                    count = await all_view_links.count()
                    print(f"Found {count} '전체보기' links total")

                    for i in range(count):
                        link = all_view_links.nth(i)
                        href = await link.get_attribute('href')
                        print(f"  Link {i}: {href}")
                        if href and ('tag' in href or '10675' in href):
                            view_all_btn = link
                            print(f"[OK] '전체보기' 버튼 발견 (tag URL: {href})")
                            break

            assert view_all_btn is not None, "'전체보기' 버튼을 찾을 수 없습니다"

            # 3. '전체보기' 버튼 클릭
            await view_all_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            current_url = page.url
            await view_all_btn.click()
            await page.wait_for_url('**/tags/**', timeout=15000)

            # 4. 페이지 이동 확인
            new_url = page.url
            print(f"Navigated to: {new_url}")

            # 기대 결과: '한 번쯤 가보고 싶은 회사' 페이지로 이동
            # 참고 URL: https://www.wanted.co.kr/tags/14?view=company&tag_id=10675
            assert new_url != current_url, f"페이지가 이동되지 않았습니다. URL: {new_url}"
            assert 'wanted.co.kr' in new_url, f"원티드 페이지가 아닙니다. URL: {new_url}"

            is_valid_url = (
                'tag' in new_url or
                '10675' in new_url or
                'company' in new_url
            )
            assert is_valid_url, f"예상한 '한 번쯤 가보고 싶은 회사' 페이지로 이동되지 않았습니다. URL: {new_url}"
            print(f"[OK] '한 번쯤 가보고 싶은 회사' 페이지로 이동 확인")

            page_title = await page.title()
            print(f"Page title: {page_title}")

            await page.screenshot(path='screenshots/test_CAREERSHOME_010_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_010_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
