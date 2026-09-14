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
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 탐색 페이지 진입
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 희망 근무지 설정 팝업 노출 확인
            dialog = page.locator('[role="dialog"]', has_text="근무지")
            await dialog.wait_for(state='visible', timeout=15000)

            # "나중에 하기" 버튼 클릭
            later_button = dialog.get_by_role('button', name='나중에 하기')
            await later_button.click()

            # 팝업이 닫히는지 확인
            await dialog.wait_for(state='hidden', timeout=10000)
            assert await dialog.count() == 0 or not await dialog.is_visible(), "희망 근무지 설정 팝업이 닫히지 않았습니다."

            await page.screenshot(path='screenshots/test_CAREERS_006_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERS_006_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
