from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

# ⭐ 테스트 계정 정보
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

            # 1. 메인 페이지에서 회원가입/로그인 버튼 클릭하여 로그인 페이지 진입
            print("🌐 메인 페이지 접속")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 메인 페이지 로드 완료")

            login_link = page.get_by_role('link', name='회원가입/로그인')
            if await login_link.count() == 0:
                login_link = page.get_by_text('회원가입/로그인')
            await login_link.first.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 로그인 페이지 진입")

            # 2. 이메일로 계속하기 버튼 클릭
            print("🔍 '이메일로 계속하기' 버튼 탐색")
            email_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_btn.wait_for(timeout=10000)
            await email_btn.click()
            print("✅ '이메일로 계속하기' 버튼 클릭")

            await page.wait_for_load_state('networkidle')

            # 3. 이메일 입력 필드가 나타났는지 확인 (이메일 로그인 페이지 진입 확인)
            print("🔍 이메일 입력 필드 확인")
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(timeout=10000)
            assert await email_input.is_visible(), "이메일 입력 필드가 보이지 않습니다"
            print("✅ 이메일 로그인 페이지 진입 확인")

            await page.screenshot(path='screenshots/test_2_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_2_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
