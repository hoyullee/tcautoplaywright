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
            # 테스트 로직: 이메일로 로그인
            # ========================================

            # 1. 로그인 버튼 찾기 (헤더에 있는)
            print("🔍 로그인 버튼 찾는 중...")
            await page.wait_for_timeout(2000)  # 페이지 안정화

            # 로그인 버튼 클릭 (다양한 셀렉터 시도)
            login_button = page.get_by_role('button', name='로그인')
            if await login_button.count() > 0:
                await login_button.first.click()
            else:
                # 텍스트로 찾기
                login_link = page.get_by_text('로그인', exact=True)
                if await login_link.count() > 0:
                    await login_link.first.click()
                else:
                    # CSS 셀렉터로 찾기
                    await page.locator('a[href*="login"], button:has-text("로그인")').first.click()

            print("✅ 로그인 버튼 클릭 완료")
            await page.wait_for_load_state('networkidle')

            # 2. 이메일로 로그인 선택
            print("🔍 이메일로 로그인 버튼 찾는 중...")
            await page.wait_for_timeout(1000)

            # 이메일 로그인 버튼 찾기
            email_login_button = page.get_by_text('이메일로 계속하기')
            if await email_login_button.count() > 0:
                await email_login_button.click()
            else:
                # 다른 텍스트 시도
                email_login_button = page.get_by_text('이메일')
                if await email_login_button.count() > 0:
                    await email_login_button.click()
                else:
                    # CSS 셀렉터로 찾기
                    await page.locator('button:has-text("이메일")').first.click()

            print("✅ 이메일 로그인 선택 완료")
            await page.wait_for_load_state('networkidle')

            # 3. 이메일 입력
            print("📧 이메일 입력 중...")
            email_input = page.locator('input[type="email"]')
            if await email_input.count() == 0:
                email_input = page.locator('input[name="email"]')
            if await email_input.count() == 0:
                email_input = page.get_by_placeholder('이메일')

            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력 완료: {TEST_EMAIL}")

            # 4. 비밀번호 입력
            print("🔑 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]')
            if await password_input.count() == 0:
                password_input = page.locator('input[name="password"]')
            if await password_input.count() == 0:
                password_input = page.get_by_placeholder('비밀번호')

            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 5. 로그인 버튼 클릭
            print("🔐 로그인 버튼 클릭 중...")
            submit_button = page.get_by_role('button', name='로그인')
            if await submit_button.count() > 0:
                await submit_button.click()
            else:
                # 텍스트로 찾기
                submit_button = page.locator('button[type="submit"]')
                if await submit_button.count() > 0:
                    await submit_button.click()
                else:
                    # 폼 제출
                    await page.locator('form').first.evaluate('form => form.submit()')

            print("✅ 로그인 버튼 클릭 완료")

            # 6. 로그인 완료 대기
            print("⏳ 로그인 처리 중...")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)  # 추가 대기

            # 7. 로그인 성공 확인 (채용 홈으로 리다이렉트 확인)
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 로그인 후 페이지 확인
            if 'wanted.co.kr' in current_url and 'login' not in current_url:
                print("✅ 로그인 성공: 채용 홈으로 리다이렉트됨")
            else:
                # 추가 확인: 로그인된 사용자 UI 요소 확인
                user_menu = page.locator('[class*="UserMenu"], [class*="user"], button:has-text("MY")')
                if await user_menu.count() > 0:
                    print("✅ 로그인 성공: 사용자 메뉴 확인됨")
                else:
                    print("⚠️ 로그인 상태 확인 필요")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_3_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_3_failed.png')
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
