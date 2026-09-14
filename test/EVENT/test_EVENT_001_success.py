import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"


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

            # 1. 교육•이벤트 탭 진입 (비로그인 상태)
            await page.goto('https://event.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 2. GNB에서 회원가입/로그인 버튼 찾기
            login_btn = page.get_by_role('link', name='회원가입/로그인')
            if not await login_btn.is_visible():
                login_btn = page.get_by_text('회원가입/로그인')
            if not await login_btn.is_visible():
                login_btn = page.locator('a[href*="login"], a[href*="signup"]').first

            await login_btn.wait_for(state='visible', timeout=10000)

            # 3. 회원가입/로그인 버튼 클릭
            await login_btn.click()
            await page.wait_for_load_state('domcontentloaded')

            # 4. 회원가입/로그인 페이지 진입 확인
            current_url = page.url
            assert (
                'login' in current_url or
                'signup' in current_url or
                'register' in current_url or
                'auth' in current_url
            ), f"회원가입/로그인 페이지 진입 실패. 현재 URL: {current_url}"

            await page.screenshot(path='screenshots/test_EVENT_001_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_EVENT_001_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
