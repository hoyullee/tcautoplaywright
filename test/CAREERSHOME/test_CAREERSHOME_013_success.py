import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups
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
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await dismiss_optional_popups(page)
            await page.wait_for_timeout(1500)

            if await page.locator('iframe.ab-in-app-message').count() > 0:
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(500)

            header = page.get_by_text('한 번쯤 가보고 싶은 회사', exact=False).first
            await header.wait_for(state='attached', timeout=20000)
            await header.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            link = page.locator('a[href*="/tags/"]').filter(has_text='전체보기')
            if await link.count() == 0:
                section = page.locator('section').filter(has_text='한 번쯤 가보고 싶은 회사')
                link = section.get_by_text('전체보기', exact=True)
            target = link.first
            await target.scroll_into_view_if_needed()
            await target.click(timeout=10000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1500)

            url = page.url
            assert '/tags/' in url, f"Unexpected URL: {url}"
            await page.screenshot(path='screenshots/test_CAREERSHOME_013_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_013_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
