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
            await page.goto('https://www.wanted.co.kr/', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # GNB에서 '콘텐츠' 항목 클릭 (href에 /events 포함된 링크)
            contents_link = page.locator('a[href*="/events"]').first
            await contents_link.click(timeout=15000)
            await page.wait_for_load_state('domcontentloaded', timeout=30000)

            # 콘텐츠 페이지 URL 확인
            current_url = page.url
            assert 'wanted.co.kr/events' in current_url, \
                f"콘텐츠 페이지 URL이 아닙니다. 현재 URL: {current_url}"

            await page.screenshot(path='screenshots/test_32_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_32_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
