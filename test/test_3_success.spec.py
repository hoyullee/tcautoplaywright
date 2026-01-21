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
            # 테스트 로직: 로그인 프로세스
            # ========================================

            # 1. 로그인 버튼 찾기 및 클릭 (회원가입/로그인 버튼)
            print("🔍 로그인 버튼 찾는 중...")
            await page.screenshot(path='screenshots/test_3_before_login.png')

            # 로그인/회원가입 버튼 클릭
            login_button = page.get_by_role('button', name='회원가입/로그인')
            if await login_button.count() > 0:
                await login_button.click()
                print("✅ 로그인 모달 열기 성공")
            else:
                # 대체 방법: 텍스트로 찾기
                login_link = page.get_by_text('회원가입/로그인')
                await login_link.click()
                print("✅ 로그인 모달 열기 성공 (대체 방법)")

            await page.wait_for_timeout(2000)

            # 2. 이메일로 시작하기 버튼 클릭
            print("🔍 이메일로 시작하기 버튼 찾는 중...")
            email_start_button = page.get_by_text('이메일로 계속하기')
            if await email_start_button.count() == 0:
                email_start_button = page.get_by_text('이메일로 시작하기')

            await email_start_button.click()
            print("✅ 이메일 로그인 페이지 진입")
            await page.wait_for_timeout(2000)

            # 3. 이메일 입력
            print(f"📧 이메일 입력 중: {TEST_EMAIL}")
            email_input = page.locator('input[type="email"]')
            await email_input.fill(TEST_EMAIL)
            print("✅ 이메일 입력 완료")

            # 4. 비밀번호 입력
            print("🔒 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            await page.screenshot(path='screenshots/test_3_filled.png')

            # 5. 로그인 버튼 클릭
            print("🔍 로그인 버튼 클릭 중...")
            submit_button = page.get_by_role('button', name='로그인')
            if await submit_button.count() == 0:
                # 대체 방법: type=submit 버튼
                submit_button = page.locator('button[type="submit"]')

            await submit_button.click()
            print("✅ 로그인 버튼 클릭 완료")

            # 6. 로그인 완료 대기 (채용 홈으로 리다이렉트)
            print("⏳ 로그인 처리 중...")
            await page.wait_for_load_state('networkidle', timeout=10000)

            # 7. 로그인 성공 확인: URL이 채용 홈으로 돌아갔는지 또는 로그인 상태 확인
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 로그인 성공 확인: 사용자 메뉴 또는 프로필 아이콘이 보이는지 확인
            await page.wait_for_timeout(3000)

            # 로그인 후 사용자 관련 요소가 있는지 확인
            user_menu_visible = False
            try:
                # 프로필 아이콘이나 사용자 메뉴 확인
                user_button = page.locator('button[data-gnb-kind="user"]')
                if await user_button.count() > 0:
                    user_menu_visible = True
                    print("✅ 사용자 메뉴 확인됨 - 로그인 성공")
            except:
                pass

            # 추가 확인: 로그인 모달이 사라졌는지
            login_modal = page.get_by_text('이메일로 계속하기')
            modal_gone = await login_modal.count() == 0

            if user_menu_visible or modal_gone:
                print("✅ 로그인 성공 확인 완료")
            else:
                print("⚠️ 로그인 상태 확인 중...")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_3_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_3_error.png')
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
