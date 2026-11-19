import sys
from pathlib import Path
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups


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

            # 채용 홈 접속 (비로그인)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await dismiss_optional_popups(page)

            # GNB 콘텐츠 탭 선택
            content_link = page.get_by_role('link', name='콘텐츠', exact=True).first
            await content_link.wait_for(state='visible', timeout=15000)
            await content_link.click()

            await page.wait_for_url('**/events**', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            assert '/events' in page.url, f"콘텐츠 페이지 진입 실패: {page.url}"

            await page.screenshot(path='screenshots/test_GNB_007_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_GNB_007_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
