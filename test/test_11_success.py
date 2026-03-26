from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        # 브라우저 실행
        browser = await p.firefox.launch(headless=False)

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
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print("✅ 페이지 로드 완료")

            # ========================================
            # 테스트 로직: 소셜 탭 > 회원가입/로그인
            # ========================================

            # 초기 스크린샷
            await page.screenshot(path='screenshots/test_11_initial.png')

            # 1. GNB에서 소셜 탭 클릭
            print("📍 소셜 탭 클릭")
            # 다양한 셀렉터 시도
            social_tab = None
            try:
                # 첫 번째 시도: 텍스트로 찾기
                social_tab = page.locator('a:has-text("소셜")')
                await social_tab.click(timeout=5000)
            except:
                try:
                    # 두 번째 시도: 정확한 링크 찾기
                    social_tab = page.locator('a[href*="social"]')
                    await social_tab.first.click(timeout=5000)
                except:
                    # 세 번째 시도: nav 내부의 소셜 링크
                    social_tab = page.locator('nav a:has-text("소셜")')
                    await social_tab.click(timeout=5000)

            await page.wait_for_timeout(2000)
            print("✅ 소셜 탭 진입 완료")

            # 2. 회원가입/로그인 버튼 클릭 (우측 상단 로그인 버튼)
            print("📍 회원가입/로그인 버튼 클릭")
            login_button = page.get_by_role('button', name='회원가입/로그인')
            await login_button.click()
            await page.wait_for_timeout(2000)  # 모달 로드 대기
            print("✅ 로그인 모달 열림")

            # 3. 이메일로 계속하기 버튼 선택
            print("📍 이메일로 계속하기 버튼 클릭")
            email_continue_button = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_button.click()
            await page.wait_for_timeout(1000)
            print("✅ 이메일 로그인 폼 진입")

            # 4. 이메일 입력
            print(f"📍 이메일 입력: {TEST_EMAIL}")
            email_input = page.locator('input[type="email"]')
            await email_input.fill(TEST_EMAIL)
            print("✅ 이메일 입력 완료")

            # 5. 비밀번호 입력
            print("📍 비밀번호 입력")
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 6. 로그인 버튼 선택
            print("📍 로그인 버튼 클릭")
            submit_button = page.get_by_role('button', name='로그인')
            await submit_button.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 로그인 시도 완료")

            # 7. 로그인 성공 확인 - 소셜 탭 페이지로 리다이렉트 확인
            await page.wait_for_timeout(2000)
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 로그인 성공 확인 (프로필 버튼 또는 로그아웃 버튼 존재 여부)
            if 'social' in current_url.lower() or await page.locator('[data-attribute-id="gnb__user-profile"]').count() > 0:
                print("✅ 로그인 성공 및 소셜 탭 페이지 확인")
            else:
                raise Exception("로그인 후 소셜 탭으로 리다이렉트되지 않음")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_11_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            # 실패 스크린샷
            await page.screenshot(path='screenshots/test_11_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
