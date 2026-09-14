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

            # GNB에서 '소셜' 링크 확인 (href 속성으로 탐색)
            social_link = page.locator('a[href*="social.wanted.co.kr"]').first

            # 링크가 없으면 텍스트로 시도
            if await social_link.count() == 0:
                social_link = page.get_by_role('link', name='소셜')

            # href 속성 확인하여 새 탭 여부 판단
            href = await social_link.get_attribute('href')
            target = await social_link.get_attribute('target')
            print(f"소셜 링크 href: {href}, target: {target}")

            # 링크를 직접 클릭하는 대신 href로 이동 (크로스 도메인 링크 click() timeout 방지)
            if href:
                await page.goto(href, timeout=30000)
            else:
                await social_link.click(force=True)
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            current_url = page.url
            screenshot_page = page

            print(f"현재 URL: {current_url}")
            assert 'social.wanted.co.kr' in current_url, \
                f"소셜 페이지 URL이 아닙니다. 현재 URL: {current_url}"

            await screenshot_page.screenshot(path='screenshots/test_GNB_008_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_GNB_008_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
