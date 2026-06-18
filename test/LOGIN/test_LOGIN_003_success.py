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

            # 사전조건: 이메일로 로그인 페이지 진입
            # 채용 홈 → GNB 로그인 버튼 → 이메일로 시작하기 순으로 진입
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # GNB에서 회원가입/로그인 버튼 클릭
            login_btn = page.get_by_role('link', name='회원가입/로그인')
            if not await login_btn.is_visible():
                login_btn = page.get_by_text('회원가입/로그인')
            await login_btn.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1000)

            # "이메일로 시작하기" 버튼 클릭하여 이메일 로그인 페이지 진입
            email_start_btn = page.get_by_role('button', name='이메일로 시작하기')
            await email_start_btn.wait_for(state='visible', timeout=10000)
            await email_start_btn.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1000)

            # 이메일 입력 필드 대기 (이메일 로그인 페이지 진입 확인)
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)

            # 확인사항 1: 이메일 입력
            await email_input.fill(TEST_EMAIL)

            # 다음 버튼이 있으면 클릭 (이메일 → 비밀번호 단계 분리된 경우)
            try:
                next_btn = page.get_by_role('button', name='다음')
                await next_btn.wait_for(state='visible', timeout=3000)
                await next_btn.click()
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            # 확인사항 1: 비밀번호 입력
            password_input = page.locator('input[type="password"]')
            await password_input.wait_for(state='visible', timeout=10000)
            await password_input.fill(TEST_PASSWORD)

            # 확인사항 2: 로그인 버튼 선택 후 네비게이션 대기
            async with page.expect_navigation(timeout=30000):
                submit_btn = page.get_by_role('button', name='로그인')
                await submit_btn.click()

            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 기대결과: 정상 로그인 및 채용 홈으로 리다이렉트 확인
            final_url = page.url
            assert 'wanted.co.kr' in final_url and 'id.wanted.co.kr/login' not in final_url, \
                f"로그인 후 채용 홈 리다이렉트 실패, 현재 URL: {final_url}"

            # 채용 홈(https://www.wanted.co.kr/) 또는 그와 동등한 페이지인지 확인
            assert 'www.wanted.co.kr' in final_url, \
                f"채용 홈으로 리다이렉트되지 않음, 현재 URL: {final_url}"

            # 세션 저장
            await context.storage_state(path='work/auth_state.json')

            await page.screenshot(path='screenshots/test_03_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_03_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
