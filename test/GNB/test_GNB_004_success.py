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

            # GNB에서 이력서 항목 클릭
            resume_link = page.get_by_role('link', name='이력서')
            await resume_link.first.click()
            await page.wait_for_load_state('domcontentloaded')

            # 이력서 페이지 진입 확인 (비로그인: /cv/intro, 로그인: /cv/list)
            current_url = page.url
            assert 'cv/intro' in current_url or 'cv/list' in current_url, \
                f"이력서 페이지 진입 실패: {current_url}"

            await page.screenshot(path='screenshots/test_29_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_29_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
