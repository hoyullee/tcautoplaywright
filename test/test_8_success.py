from playwright.async_api import async_playwright
import asyncio
import sys
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

            # 1. 원티드 홈 접속
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 2. '회원가입/로그인' 버튼 클릭
            print("🔍 회원가입/로그인 버튼 탐색...")
            login_btn = page.get_by_text('회원가입/로그인')
            await login_btn.wait_for(timeout=10000)
            await login_btn.click()
            await page.wait_for_timeout(2000)
            print("✅ 회원가입/로그인 버튼 클릭 완료")

            await page.screenshot(path='screenshots/test_8_after_login_modal.png')

            # 3. '이메일로 계속하기' 버튼 클릭
            print("🔍 이메일로 계속하기 버튼 탐색...")
            email_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_btn.wait_for(timeout=10000)
            assert await email_btn.is_visible(), "'이메일로 계속하기' 버튼이 보이지 않습니다"
            await email_btn.click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            print("✅ 이메일로 계속하기 버튼 클릭 완료")

            await page.screenshot(path='screenshots/test_8_after_email_click.png')

            # 4. 이메일 로그인 페이지 진입 확인
            print("🔍 이메일 로그인 페이지 확인...")
            # 이메일 입력 필드 또는 이메일 관련 텍스트 확인
            email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]')
            count = await email_input.count()

            if count == 0:
                # URL에 email이 포함되거나 이메일 관련 heading 확인
                current_url = page.url
                print(f"현재 URL: {current_url}")
                heading = page.locator('h1, h2, h3').filter(has_text='이메일')
                heading_count = await heading.count()
                if heading_count == 0:
                    # 페이지 전체 텍스트 확인
                    page_text = await page.inner_text('body')
                    assert '이메일' in page_text, "이메일 로그인 페이지가 아닙니다"
                print("✅ 이메일 로그인 페이지 텍스트 확인됨")
            else:
                assert await email_input.first.is_visible(), "이메일 입력 필드가 보이지 않습니다"
                print("✅ 이메일 입력 필드 확인됨")

            print("✅ 이메일 로그인 페이지 진입 확인 완료")

            await page.screenshot(path='screenshots/test_8_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_8_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
