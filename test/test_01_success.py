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

            # 1. 채용 홈 진입
            print("[INFO] 채용 홈 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)
            print("[OK] 채용 홈 로드 완료")

            title = await page.title()
            print(f"[INFO] 페이지 타이틀: {title}")
            assert 'ERROR' not in title.upper(), f"페이지 로드 실패: {title}"

            # 2. GNB 영역 확인
            print("[INFO] GNB 영역 확인 중...")
            gnb_visible = False
            for sel in [
                'header',
                'nav',
                'a[href="https://www.wanted.co.kr/wdlist"]',
                'a:has-text("채용")',
            ]:
                count = await page.locator(sel).count()
                if count > 0:
                    print(f"[OK] GNB 확인됨 (셀렉터: {sel})")
                    gnb_visible = True
                    break
            assert gnb_visible, "GNB 영역을 찾을 수 없습니다"

            # 3. 회원가입/로그인 버튼 클릭
            print("[INFO] 회원가입/로그인 버튼 클릭 중...")
            login_btn = page.get_by_role('button', name='회원가입/로그인')
            btn_count = await login_btn.count()

            if btn_count == 0:
                # fallback: 텍스트로 탐색
                login_btn = page.get_by_text('회원가입/로그인').first
                btn_count = await login_btn.count()

            if btn_count == 0:
                # fallback: JS로 클릭
                clicked = await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const btn = buttons.find(b =>
                        b.innerText.includes('회원가입') ||
                        b.innerText.includes('로그인')
                    );
                    if (btn) { btn.click(); return btn.innerText.trim(); }
                    return null;
                }""")
                assert clicked is not None, "회원가입/로그인 버튼을 찾을 수 없습니다"
                print(f"[OK] JS 클릭으로 버튼 클릭됨: {clicked}")
            else:
                await login_btn.click()
                print("[OK] 회원가입/로그인 버튼 클릭 완료")

            # 4. 로그인 페이지 진입 확인
            await page.wait_for_url('**/login**', timeout=15000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(2000)
            current_url = page.url
            print(f"[OK] 현재 URL: {current_url}")
            assert 'login' in current_url, f"로그인 페이지로 이동하지 않음: {current_url}"
            print("[OK] 회원가입/로그인 페이지 정상 진입 확인")

            # 5. 이메일로 시작하기 (또는 이메일로 계속하기)
            print("[INFO] '이메일로 시작하기' 버튼 클릭...")
            email_continue_btn = page.get_by_role('button', name='이메일로 시작하기')
            btn_cnt = await email_continue_btn.count()
            if btn_cnt == 0:
                email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_btn.wait_for(timeout=10000)
            await email_continue_btn.click()
            await page.wait_for_timeout(2000)
            print("[OK] 이메일 로그인 폼 진입 완료")

            # 6. 이메일 입력
            print("[INFO] 이메일 입력 중...")
            email_input = page.locator('#email, input[type="email"], input[name="email"]').first
            await email_input.wait_for(timeout=10000)
            await email_input.fill(TEST_EMAIL)
            print("[OK] 이메일 입력 완료")

            # 7. 비밀번호 입력
            password_input = page.locator('input[type="password"]').first
            await password_input.fill(TEST_PASSWORD)
            print("[OK] 비밀번호 입력 완료")

            # 8. 로그인 버튼 클릭
            submit_btn = page.get_by_role('button', name='로그인')
            await submit_btn.click()
            print("[OK] 로그인 제출 완료")

            # 9. 로그인 후 리다이렉트 확인
            await page.wait_for_load_state('load', timeout=20000)
            await page.wait_for_timeout(3000)
            final_url = page.url
            print(f"[OK] 로그인 후 URL: {final_url}")
            assert 'login' not in final_url, f"로그인 실패, 여전히 로그인 페이지: {final_url}"

            # 10. 세션 저장
            await context.storage_state(path='work/auth_state.json')
            print("[OK] 로그인 세션 저장 완료: work/auth_state.json")

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
