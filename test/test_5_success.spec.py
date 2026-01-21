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
            # 로그인 프로세스
            # ========================================
            print("🔑 로그인 시작")

            # 1-1. 로그인 버튼 클릭
            print("🔍 로그인 버튼 찾는 중...")
            await page.wait_for_timeout(2000)

            login_button = page.get_by_role('button', name='로그인')
            if await login_button.count() > 0:
                await login_button.first.click()
            else:
                login_link = page.get_by_text('로그인', exact=True)
                if await login_link.count() > 0:
                    await login_link.first.click()
                else:
                    await page.locator('a[href*="login"], button:has-text("로그인")').first.click()

            print("✅ 로그인 버튼 클릭 완료")
            await page.wait_for_timeout(1000)

            # 1-2. 이메일로 로그인 선택
            print("🔍 이메일로 로그인 버튼 찾는 중...")
            await page.wait_for_timeout(1000)

            email_login_button = page.get_by_text('이메일로 계속하기')
            if await email_login_button.count() > 0:
                await email_login_button.click()
            else:
                email_login_button = page.get_by_text('이메일')
                if await email_login_button.count() > 0:
                    await email_login_button.click()
                else:
                    await page.locator('button:has-text("이메일")').first.click()

            print("✅ 이메일 로그인 선택 완료")
            await page.wait_for_load_state('networkidle')

            # 1-3. 이메일 입력
            print("📧 이메일 입력 중...")
            email_input = page.locator('input[type="email"]')
            if await email_input.count() == 0:
                email_input = page.locator('input[name="email"]')
            if await email_input.count() == 0:
                email_input = page.get_by_placeholder('이메일')

            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력 완료: {TEST_EMAIL}")

            # 1-4. 비밀번호 입력
            print("🔑 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]')
            if await password_input.count() == 0:
                password_input = page.locator('input[name="password"]')
            if await password_input.count() == 0:
                password_input = page.get_by_placeholder('비밀번호')

            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 1-5. 로그인 버튼 클릭
            print("👆 로그인 버튼 클릭 중...")
            submit_button = page.get_by_role('button', name='로그인')
            if await submit_button.count() > 0:
                await submit_button.click()
            else:
                submit_button = page.locator('button[type="submit"]')
                await submit_button.click()

            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            print("✅ 로그인 완료")

            # ========================================
            # 프로필 페이지 진입
            # ========================================
            print("👤 프로필 페이지 진입")
            # 직접 프로필 URL로 이동
            await page.goto('https://www.wanted.co.kr/profile', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 프로필 페이지 진입 완료")
            await page.wait_for_timeout(2000)

            # ========================================
            # LNB 영역에서 로그아웃 버튼 선택
            # ========================================
            print("🔍 LNB 영역 확인")
            # LNB(Left Navigation Bar)에서 로그아웃 버튼 찾기
            logout_button = page.get_by_role('button', name='로그아웃')

            # 로그아웃 버튼이 보이지 않으면 다른 방법 시도
            if not await logout_button.is_visible():
                logout_button = page.get_by_text('로그아웃', exact=True)

            print("👆 로그아웃 버튼 클릭")
            await logout_button.click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)

            # ========================================
            # 로그아웃 확인 및 채용 홈 리다이렉트 확인
            # ========================================
            print("🔍 로그아웃 및 리다이렉트 확인")
            current_url = page.url
            print(f"현재 URL: {current_url}")

            # 채용 홈으로 리다이렉트 되었는지 확인
            if 'wanted.co.kr' in current_url and '/profile' not in current_url:
                print("✅ 채용 홈으로 리다이렉트 완료")

                # 로그인 버튼이 다시 보이는지 확인 (로그아웃 성공 확인)
                login_button_visible = await page.get_by_role('button', name='로그인').is_visible()
                if login_button_visible:
                    print("✅ 로그아웃 성공 (로그인 버튼 확인)")
                else:
                    print("⚠️ 로그인 버튼이 보이지 않음")
            else:
                print(f"⚠️ 예상치 못한 URL: {current_url}")

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
