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

            # 채용 홈 접속 후 로그인 버튼 클릭으로 로그인 페이지 진입
            print("[INFO] 채용 홈 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)
            print("[OK] 채용 홈 로드 완료")

            # GNB 회원가입/로그인 버튼 클릭
            print("[INFO] 회원가입/로그인 버튼 클릭...")
            clicked = await page.evaluate("""() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b =>
                    b.innerText.includes('회원가입') || b.innerText.includes('로그인')
                );
                if (btn) { btn.click(); return btn.innerText.trim(); }
                return null;
            }""")
            assert clicked is not None, "회원가입/로그인 버튼을 찾을 수 없습니다"
            print(f"[OK] 버튼 클릭됨: {clicked}")

            # 로그인 페이지 진입 대기
            await page.wait_for_url('**/login**', timeout=15000)
            await page.wait_for_timeout(2000)
            print(f"[OK] 로그인 페이지 진입: {page.url}")

            # 사전조건: 이메일로 로그인 페이지 진입 - '이메일로 계속하기' 클릭
            print("[INFO] '이메일로 계속하기' 버튼 클릭...")
            email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_btn.wait_for(timeout=10000)
            await email_continue_btn.click()
            await page.wait_for_timeout(2000)
            print("[OK] 이메일 로그인 폼 진입 완료")

            await page.screenshot(path='screenshots/test_3_step1.png')

            # 확인사항 1: 이메일 입력
            print("[INFO] 이메일 입력 중...")
            email_input = page.locator('input[type="email"]').first
            await email_input.wait_for(timeout=10000)
            await email_input.fill(TEST_EMAIL)
            print(f"[OK] 이메일 입력 완료: {TEST_EMAIL}")

            # 확인사항 1: 비밀번호 입력
            print("[INFO] 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]').first
            await password_input.wait_for(timeout=10000)
            await password_input.fill(TEST_PASSWORD)
            print("[OK] 비밀번호 입력 완료")

            await page.screenshot(path='screenshots/test_3_step2.png')

            # 확인사항 2: 로그인 버튼 선택
            print("[INFO] 로그인 버튼 클릭...")
            submit_btn = page.get_by_role('button', name='로그인')
            await submit_btn.wait_for(timeout=10000)
            await submit_btn.click()
            print("[OK] 로그인 버튼 클릭 완료")

            # 기대결과: 정상적으로 로그인되며 채용 홈으로 리다이렉트
            await page.wait_for_load_state('load', timeout=20000)
            await page.wait_for_timeout(3000)

            final_url = page.url
            print(f"[INFO] 로그인 후 URL: {final_url}")

            assert 'login' not in final_url, f"로그인 후에도 로그인 페이지에 머물러 있음: {final_url}"
            assert 'wanted.co.kr' in final_url, f"예상치 못한 URL로 이동: {final_url}"
            print(f"[OK] 채용 홈으로 리다이렉트 확인: {final_url}")

            # 로그인 세션 저장
            await context.storage_state(path='work/auth_state.json')
            print("[OK] 로그인 세션 저장 완료")

            await page.screenshot(path='screenshots/test_3_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_3_failed.png')
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
