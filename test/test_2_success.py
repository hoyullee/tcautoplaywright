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
        # 브라우저 실행 (Chromium 크래시 시 Firefox 사용)
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
            # 테스트 로직: 이메일로 계속하기 버튼 선택
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

            # 2. 이메일로 계속하기 버튼 찾아서 클릭
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

            # 방법 2: 이메일 포함 버튼 찾기
            if not email_clicked:
                try:
                    email_elements = await page.locator('button:has-text("이메일")').count()
                    if email_elements > 0:
                        await page.locator('button:has-text("이메일")').first.click()
                        print("✅ 이메일 버튼 클릭 완료")
                        email_clicked = True
                except Exception as e:
                    print(f"방법 2 실패: {e}")

            if not email_clicked:
                raise Exception("이메일로 계속하기 버튼을 찾을 수 없습니다")

            # 이메일 로그인 페이지 로드 대기
            await page.wait_for_timeout(3000)

            # 3. 이메일 입력 필드 존재 확인으로 페이지 진입 검증
            print("🔍 이메일 로그인 페이지 진입 확인 중...")

            # 이메일 입력 필드 확인
            email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]').first
            is_visible = await email_input.is_visible()

            if is_visible:
                print("✅ 이메일 로그인 페이지 진입 확인 완료")
            else:
                raise Exception("이메일 입력 필드를 찾을 수 없습니다")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_2_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            # 실패 스크린샷
            await page.screenshot(path='screenshots/test_2_failed.png', full_page=True)
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
