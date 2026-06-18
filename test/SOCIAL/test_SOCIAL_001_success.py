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

            # 1. 소셜 탭 진입 (비로그인 상태)
            await page.goto('https://social.wanted.co.kr/community', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 2. LNB 영역 확인 및 "로그인 해주세요" 버튼 찾기
            login_btn = page.get_by_role('button', name='로그인 해주세요')
            await login_btn.wait_for(state='visible', timeout=10000)
            print("LNB 영역에서 '로그인 해주세요' 버튼 확인 완료")

            # 3. "로그인 해주세요" 버튼 클릭
            await login_btn.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 4. 회원가입/로그인 페이지 진입 확인
            current_url = page.url
            print(f"이동된 URL: {current_url}")

            # 로그인 페이지 확인
            login_page_indicators = [
                'login' in current_url.lower(),
                'signup' in current_url.lower(),
                'register' in current_url.lower(),
                'auth' in current_url.lower(),
                'sign-in' in current_url.lower(),
            ]

            if not any(login_page_indicators):
                # URL로 확인 안될 경우 로그인 폼 존재 여부 확인
                login_form = page.locator('input[type="email"], input[type="text"][name*="email"], input[placeholder*="이메일"]')
                try:
                    await login_form.first.wait_for(state='visible', timeout=5000)
                    print("로그인 폼 확인 완료 (이메일 입력 필드 존재)")
                except Exception:
                    raise AssertionError(f"회원가입/로그인 페이지로 이동하지 않음. 현재 URL: {current_url}")
            else:
                print(f"로그인/회원가입 페이지 URL 확인 완료: {current_url}")

            # 5. 로그인 수행 및 세션 저장
            # "이메일로 시작하기" 버튼이 있으면 클릭
            try:
                email_start_btn = page.get_by_role('button', name='이메일로 시작하기')
                await email_start_btn.wait_for(state='visible', timeout=5000)
                await email_start_btn.click()
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            # 이메일 입력
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)

            # "다음" 버튼이 있으면 클릭
            try:
                next_btn = page.get_by_role('button', name='다음')
                await next_btn.wait_for(state='visible', timeout=3000)
                await next_btn.click()
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(1000)
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
            await page.wait_for_timeout(3000)

            # 로그인 성공 확인
            final_url = page.url
            assert 'wanted.co.kr' in final_url and 'login' not in final_url, \
                f"로그인 실패. 현재 URL: {final_url}"

            # 세션 저장
            os.makedirs('work', exist_ok=True)
            await context.storage_state(path='work/auth_state.json')
            print("세션 저장 완료: work/auth_state.json")

            await page.screenshot(path='screenshots/test_37_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_37_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
