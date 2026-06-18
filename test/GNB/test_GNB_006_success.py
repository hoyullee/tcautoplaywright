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

            # GNB에서 교육•이벤트 링크 찾기 (href에 event.wanted.co.kr 포함)
            edu_link = page.locator('a[href*="event.wanted.co.kr"]').first

            # 새 탭 오픈 대비해서 expect_page 사용
            try:
                async with context.expect_page(timeout=15000) as new_page_info:
                    await edu_link.click(timeout=15000)
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded', timeout=30000)
                target_page = new_page
            except Exception:
                # 새 탭이 아닌 현재 탭에서 이동한 경우
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                target_page = page

            # 교육•이벤트 페이지 진입 확인 (event.wanted.co.kr)
            current_url = target_page.url
            assert 'event.wanted.co.kr' in current_url, f"Expected event.wanted.co.kr but got: {current_url}"

            await target_page.screenshot(path='screenshots/test_31_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_31_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
