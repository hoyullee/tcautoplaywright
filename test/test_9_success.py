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

            # 이메일 로그인 페이지 직접 접속
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            print("✅ 페이지 로드 완료")

            # 회원가입/로그인 버튼 클릭
            print("🔍 회원가입/로그인 버튼 클릭 중...")
            await page.get_by_text('회원가입/로그인', exact=True).click()
            await page.wait_for_timeout(2000)
            print("✅ 로그인 페이지 이동 완료")

            # 이메일로 계속하기 클릭 (이메일 로그인 페이지 진입)
            print("🔍 이메일로 계속하기 버튼 클릭 중...")
            email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_btn.wait_for(state='visible', timeout=10000)
            await email_continue_btn.click()
            await page.wait_for_timeout(1000)
            print("✅ 이메일 로그인 페이지 진입 완료")

            # 이메일 입력
            print("✍️ 이메일 입력 중...")
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)
            print("✅ 이메일 입력 완료")

            # 비밀번호 입력
            print("✍️ 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]')
            await password_input.wait_for(state='visible', timeout=10000)
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 로그인 버튼 클릭
            print("🔍 로그인 버튼 클릭 중...")
            login_button = page.get_by_role('button', name='로그인')
            await login_button.click()
            print("✅ 로그인 버튼 클릭 완료")

            # 로그인 후 www.wanted.co.kr으로 리다이렉트 대기
            print("⏳ 로그인 후 리다이렉트 대기 중...")
            await page.wait_for_url(
                lambda url: url.startswith('https://www.wanted.co.kr'),
                timeout=15000
            )

            # 채용 홈으로 리다이렉트 확인
            current_url = page.url
            print(f"🔗 현재 URL: {current_url}")
            assert current_url.startswith('https://www.wanted.co.kr'), f"예상치 못한 URL: {current_url}"
            print("✅ 로그인 성공 및 채용 홈 리다이렉트 확인")

            await page.screenshot(path='screenshots/test_9_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_9_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
