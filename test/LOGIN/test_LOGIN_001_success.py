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
            os.makedirs('work', exist_ok=True)

            # 1. 채용 홈 진입
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 2. GNB 영역에서 회원가입/로그인 버튼 클릭
            login_btn = page.get_by_role('link', name='회원가입/로그인')
            if not await login_btn.is_visible():
                login_btn = page.get_by_text('회원가입/로그인')
            await login_btn.click()
            await page.wait_for_load_state('domcontentloaded')

            # 3. 회원가입/로그인 페이지 진입 확인 (wanted 통합 로그인 페이지 포함)
            await page.wait_for_timeout(1000)
            current_url = page.url
            # wanted 로그인 페이지는 id.wanted.co.kr 또는 login 관련 URL로 이동
            assert ('login' in current_url or 'signup' in current_url
                    or 'join' in current_url or 'id.wanted' in current_url
                    or 'account' in current_url), \
                f"Expected login/signup page, but got: {current_url}"

            # 4. 이메일로 시작하기 버튼 클릭 (소셜 로그인 선택 화면)
            try:
                email_start_btn = page.get_by_role('button', name='이메일로 시작하기')
                await email_start_btn.wait_for(state='visible', timeout=5000)
                await email_start_btn.click()
                await page.wait_for_load_state('domcontentloaded')
            except Exception:
                pass

            # 이메일 입력
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)

            # 다음 버튼 클릭 (이메일 입력 후 다음 단계)
            try:
                next_btn = page.get_by_role('button', name='다음')
                await next_btn.wait_for(state='visible', timeout=3000)
                await next_btn.click()
                await page.wait_for_load_state('domcontentloaded')
            except Exception:
                pass

            # 비밀번호 입력
            password_input = page.locator('input[type="password"]')
            await password_input.wait_for(state='visible', timeout=10000)
            await password_input.fill(TEST_PASSWORD)

            # 로그인 버튼 클릭
            submit_btn = page.get_by_role('button', name='로그인')
            await submit_btn.click()
            await page.wait_for_load_state('domcontentloaded')

            # 5. 로그인 성공 확인 (채용 홈 또는 이전 페이지로 리다이렉트)
            await page.wait_for_timeout(2000)
            final_url = page.url
            # 로그인 성공 시 wanted.co.kr 메인 혹은 다른 페이지로 이동
            assert 'wanted.co.kr' in final_url and 'login' not in final_url, \
                f"Login may have failed, current URL: {final_url}"

            # 6. 세션 저장
            await context.storage_state(path='work/auth_state.json')

            await page.screenshot(path='screenshots/test_01_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_01_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
