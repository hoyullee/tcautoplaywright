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

            # 탐색 페이지 진입 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # '적극 채용 중인 회사' 항목 비노출 확인
            # 텍스트로 해당 섹션이 존재하는지 확인
            actively_hiring_text = page.get_by_text('적극 채용 중인 회사', exact=False)
            count = await actively_hiring_text.count()

            assert count == 0, f"'적극 채용 중인 회사' 항목이 노출됨 (비로그인 상태에서는 비노출이어야 함). count={count}"

            await page.screenshot(path='screenshots/test_CAREERS_001_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERS_001_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
