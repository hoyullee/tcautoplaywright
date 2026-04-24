import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)
            os.makedirs('work', exist_ok=True)

            # 1. 교육•이벤트 페이지 접속 (비로그인 상태)
            print("[INFO] 교육•이벤트 페이지 접속 중...")
            await page.goto('https://event.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)
            print(f"[OK] 교육•이벤트 페이지 로드 완료 - URL: {page.url}")

            # 2. GNB 영역의 회원가입/로그인 버튼 탐색
            print("[INFO] GNB 회원가입/로그인 버튼 탐색 중...")
            login_btn = None
            selectors = [
                page.get_by_role('link', name='회원가입/로그인'),
                page.get_by_role('button', name='회원가입/로그인'),
                page.get_by_role('link', name='로그인'),
                page.get_by_role('button', name='로그인'),
                page.locator('a[href*="login"]').first,
                page.locator('button:has-text("로그인")').first,
                page.locator('a:has-text("로그인")').first,
                page.locator('a:has-text("회원가입")').first,
            ]
            for sel in selectors:
                try:
                    await sel.wait_for(timeout=3000, state='visible')
                    login_btn = sel
                    label = await sel.inner_text()
                    print(f"[OK] 버튼 발견: '{label}'")
                    break
                except Exception:
                    continue

            assert login_btn is not None, "GNB에서 회원가입/로그인 버튼을 찾을 수 없습니다"

            # 3. 회원가입/로그인 버튼 클릭
            print("[INFO] 회원가입/로그인 버튼 클릭 중...")
            await login_btn.click()
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            current_url = page.url
            print(f"[INFO] 클릭 후 URL: {current_url}")

            # 4. 로그인/회원가입 페이지 진입 확인
            is_login_page = (
                'login' in current_url or
                'signin' in current_url or
                'signup' in current_url or
                'register' in current_url or
                'auth' in current_url
            )
            assert is_login_page, f"회원가입/로그인 페이지로 이동하지 않았습니다. 현재 URL: {current_url}"
            print(f"[OK] 회원가입/로그인 페이지 정상 진입 확인: {current_url}")

            # 5. '이메일로 계속하기' 버튼 클릭 (id.wanted.co.kr 로그인 페이지 구조)
            print("[INFO] '이메일로 계속하기' 버튼 탐색 중...")
            email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_btn.wait_for(timeout=10000, state='visible')
            await email_continue_btn.click()
            await page.wait_for_timeout(2000)
            print("[OK] '이메일로 계속하기' 클릭 완료")

            # 6. 이메일 입력
            print("[INFO] 이메일 입력 중...")
            email_input = page.locator('#email, input[type="email"], input[name="email"]').first
            await email_input.wait_for(timeout=10000, state='visible')
            await email_input.fill(TEST_EMAIL)
            print(f"[OK] 이메일 입력 완료: {TEST_EMAIL}")

            # 7. 비밀번호 입력
            print("[INFO] 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]').first
            await password_input.fill(TEST_PASSWORD)
            print("[OK] 비밀번호 입력 완료")

            # 8. 로그인 버튼 클릭
            print("[INFO] 로그인 버튼 클릭 중...")
            submit_btn = page.get_by_role('button', name='로그인')
            await submit_btn.click()
            await page.wait_for_load_state('load', timeout=30000)
            await page.wait_for_timeout(2000)
            final_url = page.url
            print(f"[OK] 로그인 후 URL: {final_url}")

            # 9. 세션 저장
            await context.storage_state(path='work/auth_state.json')
            print("[OK] 세션 저장 완료: work/auth_state.json")

            await page.screenshot(path='screenshots/test_24_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_24_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
