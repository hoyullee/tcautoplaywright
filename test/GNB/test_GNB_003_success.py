import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        # 비로그인 상태 - 세션 로드 없이 새 컨텍스트 생성
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # GNB에서 "채용" 항목 클릭
            gnb_채용 = page.get_by_role('link', name='채용').first
            await gnb_채용.wait_for(state='visible', timeout=10000)
            await gnb_채용.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 탐색 페이지(https://www.wanted.co.kr/wdlist) 진입 확인
            current_url = page.url
            assert 'wdlist' in current_url, f"탐색 페이지 진입 실패. 현재 URL: {current_url}"

            await page.screenshot(path='screenshots/test_28_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_28_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
