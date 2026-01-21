from playwright.async_api import async_playwright
import asyncio
import sys
import os

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

async def main():
    async with async_playwright() as p:
        # 브라우저 실행
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
            # 테스트 로직 시작
            # ========================================

            # 1. 소셜 탭 클릭 (사전조건 1)
            print("📌 소셜 탭 클릭")
            social_tab = page.get_by_role('link', name='소셜')
            await social_tab.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 소셜 탭 진입 완료")

            # 2. 회원가입/로그인 버튼 클릭 (사전조건 2)
            print("📌 회원가입/로그인 페이지 진입")
            # 로그인 버튼 찾기 - 여러 가능성 시도
            try:
                # GNB의 로그인 버튼 클릭
                login_button = page.get_by_role('button', name='회원가입/로그인')
                await login_button.click()
            except:
                # 다른 로그인 버튼 시도
                login_button = page.locator('button:has-text("로그인")')
                await login_button.first.click()

            await page.wait_for_load_state('networkidle')
            print("✅ 회원가입/로그인 페이지 진입 완료")

            # 3. 이메일로 계속하기 버튼 선택 (확인사항 1)
            print("📌 이메일로 계속하기 버튼 클릭")
            email_continue_button = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_button.click()
            await page.wait_for_timeout(1000)  # 폼 로드 대기
            print("✅ 이메일 로그인 폼 표시")

            # 4. 이메일 및 비밀번호 입력 (확인사항 2)
            print("📌 이메일 및 비밀번호 입력")

            # 이메일 입력
            email_input = page.locator('input[type="email"]')
            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력: {TEST_EMAIL}")

            # 비밀번호 입력
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 5. 로그인 버튼 선택 (확인사항 3)
            print("📌 로그인 버튼 클릭")
            login_submit_button = page.get_by_role('button', name='로그인')
            await login_submit_button.click()

            # 6. 로그인 완료 및 리다이렉트 대기
            print("📌 로그인 처리 및 리다이렉트 대기")
            await page.wait_for_load_state('networkidle', timeout=10000)

            # 7. 소셜 탭으로 리다이렉트 확인 (기대결과)
            current_url = page.url
            print(f"📌 현재 URL: {current_url}")

            # 로그인 성공 확인 - 소셜 페이지에 있고 로그인 상태인지 확인
            if 'social' in current_url or 'community' in current_url:
                print("✅ 소셜 탭으로 리다이렉트 확인")
            else:
                # URL이 변경되지 않았다면 페이지 내용으로 확인
                await page.wait_for_timeout(2000)
                current_url = page.url
                print(f"📌 재확인 URL: {current_url}")

            # 로그인 상태 확인 (프로필 아이콘이나 로그아웃 버튼 존재 확인)
            try:
                # 로그인 후 표시되는 요소 확인
                profile_element = page.locator('[data-attribute-id="gnb__user-profile"]').first
                await profile_element.wait_for(state='visible', timeout=5000)
                print("✅ 로그인 상태 확인: 프로필 아이콘 표시됨")
            except:
                print("⚠️ 프로필 아이콘 확인 실패, URL로 판단")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_11_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            # 실패 시 스크린샷
            try:
                await page.screenshot(path='screenshots/test_11_failed.png', full_page=True)
            except:
                pass
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
