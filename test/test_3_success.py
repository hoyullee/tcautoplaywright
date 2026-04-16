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

            # 채용 홈 접속
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 회원가입/로그인 버튼 클릭
            await page.get_by_role('button', name='회원가입/로그인').click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(1000)
            print("✅ 회원가입/로그인 버튼 클릭")

            # 이메일로 계속하기 클릭 (이메일 로그인 페이지 진입)
            await page.get_by_role('button', name='이메일로 계속하기').click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(1000)
            print("✅ 이메일 로그인 페이지 진입")

            # 이메일 입력
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력: {TEST_EMAIL}")

            # 비밀번호 입력
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 로그인 버튼 클릭
            login_button = page.get_by_role('button', name='로그인')
            await login_button.click()
            print("✅ 로그인 버튼 클릭")

            # 채용 홈으로 리다이렉트 확인
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)

            current_url = page.url
            print(f"✅ 현재 URL: {current_url}")

            # 로그인 성공 확인: id.wanted.co.kr/login 이 아닌 페이지로 이동
            assert 'id.wanted.co.kr/login' not in current_url, \
                f"로그인 실패 - 여전히 로그인 페이지: {current_url}"
            print("✅ 채용 홈으로 리다이렉트 확인")

            await page.screenshot(path='screenshots/test_3_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_3_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
