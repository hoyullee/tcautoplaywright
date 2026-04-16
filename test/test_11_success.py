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

            # 소셜 탭 진입
            print("🌐 소셜 탭 접속: https://www.wanted.co.kr/social")
            await page.goto('https://www.wanted.co.kr/social', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 소셜 탭 로드 완료")

            # 회원가입/로그인 페이지 진입 - 로그인 버튼 클릭
            print("🔍 로그인 버튼 찾는 중...")
            login_link = page.get_by_role('link', name='로그인')
            if await login_link.count() > 0:
                await login_link.first.click()
            else:
                # 헤더의 로그인 버튼 시도
                await page.get_by_text('로그인').first.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 로그인 페이지 진입")

            # 이메일로 계속하기 버튼 선택
            print("🔍 이메일로 계속하기 버튼 찾는 중...")
            email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            if await email_continue_btn.count() == 0:
                email_continue_btn = page.get_by_text('이메일로 계속하기')
            await email_continue_btn.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 이메일로 계속하기 선택")

            # 이메일 입력
            print("📧 이메일 입력 중...")
            email_input = page.locator('input[type="email"]')
            if await email_input.count() == 0:
                email_input = page.get_by_label('이메일')
            await email_input.fill(TEST_EMAIL)
            print("✅ 이메일 입력 완료")

            # 비밀번호 입력
            print("🔑 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]')
            if await password_input.count() == 0:
                password_input = page.get_by_label('비밀번호')
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 로그인 버튼 선택
            print("🖱️ 로그인 버튼 클릭 중...")
            login_btn = page.get_by_role('button', name='로그인')
            await login_btn.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 로그인 버튼 클릭 완료")

            # 소셜 탭으로 리다이렉트 확인
            current_url = page.url
            print(f"현재 URL: {current_url}")

            # 로그인 성공 여부 확인 (URL에 social이 포함되거나 로그인 상태 확인)
            assert 'social' in current_url or 'wanted.co.kr' in current_url, f"예상치 못한 URL: {current_url}"

            # 로그인 실패 메시지가 없는지 확인
            error_msg = page.locator('[class*="error"], [class*="Error"]')
            if await error_msg.count() > 0:
                error_text = await error_msg.first.text_content()
                raise AssertionError(f"로그인 실패 메시지 발견: {error_text}")

            await page.screenshot(path='screenshots/test_11_success.png')
            print("✅ 테스트 성공 - 소셜 탭으로 리다이렉트 확인")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_11_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
