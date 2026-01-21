from playwright.async_api import async_playwright
import asyncio
import sys
import os

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

async def main():
    async with async_playwright() as p:
        # 브라우저 실행 (Firefox 사용)
        browser = await p.firefox.launch(headless=True)

        # 한국어 설정
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            # screenshots 폴더 생성
            os.makedirs('screenshots', exist_ok=True)

            # 페이지 접속
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # ========================================
            # 테스트 로직: 로그인 후 로그아웃
            # ========================================

            # 1. 로그인 버튼 클릭
            print("🔐 로그인 시작")
            login_button = page.get_by_role('button', name='회원가입/로그인')
            await login_button.click()
            await page.wait_for_timeout(2000)
            print("✅ 로그인 페이지로 이동")

            # 2. "이메일로 계속하기" 버튼 클릭
            email_continue_button = page.get_by_text('이메일로 계속하기')
            await email_continue_button.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path='screenshots/test_5_email_form.png')
            print("✅ 이메일 로그인 폼으로 이동")

            # 3. 이메일 입력
            email_input = page.locator('input[type="email"]').first
            await email_input.wait_for(state='visible', timeout=5000)
            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력: {TEST_EMAIL}")

            # 4. 비밀번호 입력
            password_input = page.locator('input[type="password"]').first
            await password_input.wait_for(state='visible', timeout=5000)
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력")

            # 5. 로그인 버튼 클릭 (제출)
            submit_button = page.get_by_role('button', name='로그인')
            await submit_button.click()
            await page.wait_for_timeout(3000)  # 로그인 완료 대기
            await page.screenshot(path='screenshots/test_5_after_login.png')
            print("✅ 로그인 완료")

            # 6. 프로필 페이지로 직접 이동
            print("👤 프로필 페이지로 이동")
            await page.goto('https://www.wanted.co.kr/profile', timeout=30000)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshots/test_5_profile_page.png')
            print("✅ 프로필 페이지 진입")

            # 7. LNB 영역에서 로그아웃 버튼 찾기
            print("🔍 LNB 영역에서 로그아웃 버튼 찾기")

            # 로그아웃 버튼 선택 (여러 가능성 시도)
            logout_button = None
            try:
                # 시도 1: 정확한 텍스트로 버튼 찾기
                logout_button = page.get_by_role('button', name='로그아웃')
                await logout_button.wait_for(state='visible', timeout=5000)
            except:
                try:
                    # 시도 2: 부분 텍스트로 찾기
                    logout_button = page.get_by_text('로그아웃').first
                    await logout_button.wait_for(state='visible', timeout=5000)
                except:
                    try:
                        # 시도 3: 링크로 찾기
                        logout_button = page.locator('a:has-text("로그아웃")').first
                        await logout_button.wait_for(state='visible', timeout=5000)
                    except:
                        # 시도 4: nav 또는 aside 영역 내에서 찾기
                        logout_button = page.locator('nav button:has-text("로그아웃"), aside button:has-text("로그아웃")').first
                        await logout_button.wait_for(state='visible', timeout=5000)

            print("✅ 로그아웃 버튼 발견")

            # 9. 로그아웃 실행
            await logout_button.click()
            await page.wait_for_timeout(3000)
            print("✅ 로그아웃 클릭 완료")

            # 10. 채용 홈으로 리다이렉트 확인
            current_url = page.url
            print(f"🌐 현재 URL: {current_url}")

            if 'wanted.co.kr' in current_url and '/profile' not in current_url:
                print("✅ 채용 홈으로 리다이렉트 확인")
            else:
                raise Exception(f"리다이렉트 실패: {current_url}")

            # 11. 로그아웃 상태 확인 (로그인 버튼 존재)
            login_check = page.get_by_role('button', name='회원가입/로그인')
            await login_check.wait_for(state='visible', timeout=5000)
            print("✅ 로그아웃 상태 확인 (로그인 버튼 표시)")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_5_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_5_error.png')
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
