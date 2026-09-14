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

            # GNB에서 '프리랜서' 링크 탐색 (href 속성으로 우선 탐색)
            freelancer_link = page.locator('a[href*="gigs/experts"]').first

            # href로 못 찾으면 텍스트로 시도
            if await freelancer_link.count() == 0:
                freelancer_link = page.get_by_role('link', name='프리랜서')

            # href 속성 및 target 확인
            href = await freelancer_link.get_attribute('href')
            target = await freelancer_link.get_attribute('target')
            print(f"프리랜서 링크 href: {href}, target: {target}")

            if target == '_blank':
                # 새 탭으로 열리는 경우
                async with context.expect_page() as new_page_info:
                    await freelancer_link.click(timeout=15000)
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded', timeout=30000)
                await new_page.wait_for_timeout(2000)
                current_url = new_page.url
                screenshot_page = new_page
            else:
                # 현재 탭에서 이동하는 경우
                await freelancer_link.click(timeout=15000)
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)
                current_url = page.url
                screenshot_page = page

            print(f"현재 URL: {current_url}")
            assert 'gigs/experts' in current_url, \
                f"프리랜서 페이지 URL이 아닙니다. 현재 URL: {current_url}"

            await screenshot_page.screenshot(path='screenshots/test_GNB_009_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_GNB_009_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
