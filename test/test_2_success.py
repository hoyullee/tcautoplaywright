import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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

            # [사전조건] 회원가입/로그인 페이지 진입
            print("[INFO] 채용 홈 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)
            print("[OK] 페이지 로드 완료")

            # GNB 로그인 버튼 클릭하여 로그인 페이지 진입
            print("[INFO] 회원가입/로그인 버튼 클릭...")
            clicked = await page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const loginBtn = buttons.find(b =>
                    b.innerText.includes('회원가입') ||
                    b.innerText.includes('로그인')
                );
                if (loginBtn) {
                    loginBtn.click();
                    return loginBtn.innerText.trim();
                }
                return null;
            }""")
            assert clicked is not None, "회원가입/로그인 버튼을 찾을 수 없습니다"
            print(f"[OK] 버튼 클릭됨: {clicked}")

            await page.wait_for_url('**/login**', timeout=15000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(2000)
            print(f"[OK] 로그인 페이지 진입: {page.url}")
            await page.screenshot(path='screenshots/test_2_step1_login_page.png')

            # [확인사항] 이메일로 계속하기 버튼 선택
            print("[INFO] '이메일로 계속하기' 버튼 클릭...")
            email_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_btn.wait_for(timeout=10000)
            await email_btn.click()
            await page.wait_for_timeout(2000)
            print("[OK] '이메일로 계속하기' 버튼 클릭 완료")

            # [기대결과] 이메일로 로그인 페이지 진입 확인
            print("[INFO] 이메일 로그인 폼 확인 중...")
            await page.screenshot(path='screenshots/test_2_step2_email_form.png')

            email_input = page.locator('#email, input[type="email"], input[name="email"]').first
            await email_input.wait_for(timeout=10000)
            assert await email_input.is_visible(), "이메일 입력 필드가 보이지 않습니다"
            print("[OK] 이메일 입력 필드 확인 완료 - 이메일 로그인 페이지 진입 확인")

            # 로그인 완료 후 세션 저장
            print("[INFO] 이메일/비밀번호 입력 및 로그인...")
            await email_input.fill(TEST_EMAIL)

            password_input = page.locator('input[type="password"]').first
            await password_input.fill(TEST_PASSWORD)
            print("[OK] 계정 정보 입력 완료")

            submit_btn = page.get_by_role('button', name='로그인')
            await submit_btn.click()
            print("[OK] 로그인 제출")

            await page.wait_for_load_state('load', timeout=20000)
            await page.wait_for_timeout(2000)
            print(f"[OK] 로그인 후 URL: {page.url}")

            await context.storage_state(path='work/auth_state.json')
            print("[OK] 로그인 세션 저장 완료")

            await page.screenshot(path='screenshots/test_2_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_2_failed.png')
            except Exception:
                pass
            print(f"[FAIL] 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
