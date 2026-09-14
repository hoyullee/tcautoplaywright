import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json',
            viewport={'width': 1280, 'height': 900}
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # 인앱 메시지(브레이즈) 오버레이 제거 (클릭 가로채는 경우 방지)
            await page.evaluate("""() => {
                document.querySelectorAll('.ab-in-app-message, [class*="ab-in-app"]').forEach(el => el.remove());
            }""")

            # '~포지션 어때요?' 문구를 포함하는 섹션(article) 찾기
            section_info = await page.evaluate("""() => {
                const articles = document.querySelectorAll('article');
                for (const article of articles) {
                    if (article.textContent.includes('포지션 어때요?')) {
                        const rect = article.getBoundingClientRect();
                        const absoluteTop = window.scrollY + rect.top;
                        return { absoluteTop: Math.round(absoluteTop), text: article.textContent.slice(0, 50) };
                    }
                }
                return null;
            }""")

            assert section_info is not None, "'~포지션 어때요?' 섹션을 찾을 수 없음"
            print(f"찾은 섹션: {section_info['text']}")

            # 섹션이 뷰포트 중간에 오도록 스크롤
            target_scroll = max(0, section_info['absoluteTop'] - 200)
            await page.evaluate(f"window.scrollTo(0, {target_scroll})")
            await page.wait_for_timeout(1500)

            # '전체보기' 버튼(링크) href 확인 (예상 URL 패턴: /tags/{url})
            more_href = await page.evaluate("""() => {
                const articles = document.querySelectorAll('article');
                for (const article of articles) {
                    if (article.textContent.includes('포지션 어때요?')) {
                        const links = article.querySelectorAll('a');
                        for (const link of links) {
                            if (link.textContent.includes('전체보기') || link.textContent.includes('전체 보기')) {
                                return link.href;
                            }
                        }
                    }
                }
                return null;
            }""")

            assert more_href is not None, "'전체보기' 버튼을 찾을 수 없음"
            print(f"'전체보기' 버튼 href: {more_href}")

            before_url = page.url

            more_locator = page.locator(f'a[href="{more_href.replace("https://www.wanted.co.kr", "")}"]').first
            if await more_locator.count() == 0:
                more_locator = page.locator(f'a[href="{more_href}"]').first

            await more_locator.scroll_into_view_if_needed(timeout=5000)
            await more_locator.click(timeout=5000)
            await page.wait_for_load_state('domcontentloaded', timeout=15000)
            await page.wait_for_timeout(1500)

            current_url = page.url
            print(f"이동된 URL: {current_url}")

            assert current_url != before_url, "'전체보기' 클릭 후 페이지 URL이 변경되지 않음"
            assert '/tags/' in current_url, f"기대한 태그 페이지로 이동되지 않음. 현재 URL: {current_url}"
            print("✓ '전체보기' 버튼 클릭 시 태그 페이지로 이동 확인")

            await page.screenshot(path='screenshots/test_CAREERSHOME_020_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_020_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
