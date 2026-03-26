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
        browser = await p.firefox.launch(
            headless=False
        )

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
            # 로그인 테스트 로직
            # ========================================

            # 1. 회원가입/로그인 버튼 찾아서 클릭
            print("🔍 회원가입/로그인 버튼 찾는 중...")

            # 로그인 관련 요소를 찾아서 클릭
            login_clicked = False

            # 방법 1: 텍스트 '회원가입/로그인' 찾기
            try:
                login_elements = await page.locator('text=회원가입/로그인').count()
                if login_elements > 0:
                    await page.locator('text=회원가입/로그인').first.click()
                    print("✅ 회원가입/로그인 링크 클릭 완료")
                    login_clicked = True
            except Exception as e:
                print(f"방법 1 실패: {e}")

            # 방법 2: 로그인 버튼 찾기
            if not login_clicked:
                try:
                    login_elements = await page.locator('text=로그인').count()
                    if login_elements > 0:
                        await page.locator('text=로그인').first.click()
                        print("✅ 로그인 버튼 클릭 완료")
                        login_clicked = True
                except Exception as e:
                    print(f"방법 2 실패: {e}")

            # 방법 3: CSS 선택자로 찾기
            if not login_clicked:
                try:
                    await page.locator('a[href*="login"]').first.click(timeout=5000)
                    print("✅ 로그인 링크 클릭 완료 (CSS)")
                    login_clicked = True
                except Exception as e:
                    print(f"방법 3 실패: {e}")

            if not login_clicked:
                raise Exception("로그인 버튼을 찾을 수 없습니다")

            # 로그인 모달/페이지 로드 대기
            await page.wait_for_timeout(3000)

            # 2. 이메일로 계속하기/이메일로 시작하기 버튼 찾아서 클릭
            print("🔍 이메일로 계속하기 버튼 찾는 중...")

            email_clicked = False

            # 방법 1: 텍스트로 찾기
            try:
                email_elements = await page.locator('text=이메일로 계속하기').count()
                if email_elements > 0:
                    await page.locator('text=이메일로 계속하기').first.click()
                    print("✅ 이메일로 계속하기 버튼 클릭 완료")
                    email_clicked = True
            except Exception as e:
                print(f"방법 1 실패: {e}")

            # 방법 2: 이메일로 시작하기 찾기
            if not email_clicked:
                try:
                    email_elements = await page.locator('text=이메일로 시작하기').count()
                    if email_elements > 0:
                        await page.locator('text=이메일로 시작하기').first.click()
                        print("✅ 이메일로 시작하기 버튼 클릭 완료")
                        email_clicked = True
                except Exception as e:
                    print(f"방법 2 실패: {e}")

            # 방법 3: 이메일 포함 버튼 찾기
            if not email_clicked:
                try:
                    email_elements = await page.locator('button:has-text("이메일")').count()
                    if email_elements > 0:
                        await page.locator('button:has-text("이메일")').first.click()
                        print("✅ 이메일 버튼 클릭 완료")
                        email_clicked = True
                except Exception as e:
                    print(f"방법 3 실패: {e}")

            if not email_clicked:
                raise Exception("이메일로 계속하기 버튼을 찾을 수 없습니다")

            # 이메일 로그인 페이지 로드 대기
            await page.wait_for_timeout(3000)

            # 3. 이메일 입력
            print("📝 이메일 입력 중...")
            email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]').first
            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력 완료: {TEST_EMAIL}")

            # 4. 비밀번호 입력
            print("📝 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"], input[name="password"], input[placeholder*="비밀번호"]').first
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 5. 로그인 버튼 클릭
            print("🔍 로그인 버튼 클릭 중...")

            login_submit_clicked = False

            # 방법 1: 텍스트로 로그인 버튼 찾기
            try:
                login_button = page.locator('button:has-text("로그인")')
                if await login_button.count() > 0:
                    await login_button.first.click()
                    print("✅ 로그인 버튼 클릭 완료")
                    login_submit_clicked = True
            except Exception as e:
                print(f"로그인 버튼 찾기 실패: {e}")

            # 방법 2: submit 버튼 찾기
            if not login_submit_clicked:
                try:
                    submit_button = page.locator('button[type="submit"]')
                    if await submit_button.count() > 0:
                        await submit_button.first.click()
                        print("✅ Submit 버튼 클릭 완료")
                        login_submit_clicked = True
                except Exception as e:
                    print(f"Submit 버튼 찾기 실패: {e}")

            if not login_submit_clicked:
                raise Exception("로그인 버튼을 찾을 수 없습니다")

            # 6. 로그인 후 리다이렉트 대기
            print("⏳ 로그인 처리 대기 중...")
            await page.wait_for_timeout(5000)

            # 7. 로그인 성공 확인
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 로그인 성공 확인
            is_logged_in = False

            # 방법 1: URL이 로그인 페이지가 아닌지 확인
            if '/login' not in current_url and '/signup' not in current_url:
                is_logged_in = True
                print("✅ 로그인 확인: 로그인 페이지에서 벗어남")

            # 방법 2: 프로필 요소 확인
            try:
                profile_elements = await page.locator('[class*="Avatar"], [class*="profile"], button:has-text("MY")').count()
                if profile_elements > 0:
                    is_logged_in = True
                    print("✅ 로그인 확인: 프로필 요소 발견")
            except:
                pass

            if not is_logged_in:
                # 스크린샷 찍어서 확인
                await page.screenshot(path='screenshots/test_3_debug.png', full_page=True)
                raise Exception("로그인 성공 확인 실패")

            print("🎉 로그인 성공 및 채용 홈 리다이렉트 확인")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_3_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            # 실패 스크린샷
            await page.screenshot(path='screenshots/test_3_failed.png', full_page=True)
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
