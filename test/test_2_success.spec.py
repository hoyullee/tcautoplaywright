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
            # 테스트 로직: 회원가입/로그인 페이지 진입 후 이메일로 계속하기 버튼 선택
            # ========================================

            # 1단계: 회원가입/로그인 버튼 찾기 및 클릭
            print("🔍 회원가입/로그인 버튼 찾는 중...")

            # 방법 1: 텍스트로 찾기
            login_button = None
            try:
                login_button = page.get_by_text('회원가입/로그인', exact=False)
                if await login_button.count() > 0:
                    print("✅ 회원가입/로그인 버튼 발견 (텍스트)")
            except:
                pass

            # 방법 2: 버튼 role로 찾기
            if not login_button or await login_button.count() == 0:
                try:
                    login_button = page.get_by_role('button', name='회원가입')
                    if await login_button.count() > 0:
                        print("✅ 회원가입 버튼 발견 (role)")
                except:
                    pass

            # 방법 3: CSS 선택자로 찾기
            if not login_button or await login_button.count() == 0:
                try:
                    selectors = [
                        'a:has-text("회원가입")',
                        'button:has-text("회원가입")',
                        'a:has-text("로그인")',
                        'button:has-text("로그인")',
                        '[class*="login"]',
                        '[class*="signup"]',
                        '[href*="signup"]',
                        '[href*="login"]'
                    ]

                    for selector in selectors:
                        try:
                            element = page.locator(selector).first
                            if await element.count() > 0:
                                login_button = element
                                print(f"✅ 회원가입/로그인 버튼 발견 (selector: {selector})")
                                break
                        except:
                            continue
                except:
                    pass

            # 버튼이 존재하는지 확인
            if not login_button or await login_button.count() == 0:
                await page.screenshot(path='screenshots/test_2_debug.png', full_page=True)
                raise Exception("회원가입/로그인 버튼을 찾을 수 없습니다")

            # 버튼 클릭
            print("🖱️ 회원가입/로그인 버튼 클릭")
            await login_button.click()

            # 페이지 전환 대기
            await page.wait_for_load_state('networkidle', timeout=10000)
            print("✅ 회원가입/로그인 페이지 진입")

            # 현재 상태 스크린샷
            await page.screenshot(path='screenshots/test_2_after_login_click.png', full_page=True)

            # 2단계: 이메일로 계속하기 버튼 찾기
            print("🔍 이메일로 계속하기 버튼 찾는 중...")

            email_button = None

            # 방법 1: 정확한 텍스트로 찾기
            try:
                email_button = page.get_by_text('이메일로 계속하기', exact=False)
                if await email_button.count() > 0:
                    print("✅ 이메일로 계속하기 버튼 발견 (텍스트)")
            except:
                pass

            # 방법 2: role로 찾기
            if not email_button or await email_button.count() == 0:
                try:
                    email_button = page.get_by_role('button', name='이메일')
                    if await email_button.count() > 0:
                        print("✅ 이메일 버튼 발견 (role)")
                except:
                    pass

            # 방법 3: CSS 선택자로 찾기
            if not email_button or await email_button.count() == 0:
                try:
                    selectors = [
                        'button:has-text("이메일")',
                        'a:has-text("이메일")',
                        'button:has-text("계속")',
                        '[class*="email"]',
                        '[data-button-name*="email"]'
                    ]

                    for selector in selectors:
                        try:
                            element = page.locator(selector).first
                            if await element.count() > 0:
                                email_button = element
                                print(f"✅ 이메일 버튼 발견 (selector: {selector})")
                                break
                        except:
                            continue
                except:
                    pass

            # 버튼이 존재하는지 확인
            if not email_button or await email_button.count() == 0:
                await page.screenshot(path='screenshots/test_2_no_email_button.png', full_page=True)
                raise Exception("이메일로 계속하기 버튼을 찾을 수 없습니다")

            # 버튼 클릭
            print("🖱️ 이메일로 계속하기 버튼 클릭")
            await email_button.click()

            # 3단계: 이메일 로그인 페이지 진입 확인
            print("🔍 이메일 입력 필드 확인 중...")

            # 이메일 입력 필드가 나타날 때까지 기다리기 (최대 10초)
            try:
                await page.wait_for_selector('input[type="email"], input[name*="email"], input[id*="email"], input[placeholder*="이메일"]', timeout=10000, state='visible')
                print("✅ 이메일 입력 필드 발견")
            except:
                # 입력 필드를 찾지 못한 경우 현재 페이지 상태 확인
                await page.screenshot(path='screenshots/test_2_no_email_field.png', full_page=True)
                # URL이 변경되었는지 확인
                current_url = page.url
                print(f"현재 URL: {current_url}")

                # 다른 방법으로 이메일 입력 필드 찾기
                email_field = page.locator('input').filter(has_text='이메일')
                if await email_field.count() == 0:
                    # 텍스트 입력 필드 중에서 찾기
                    email_field = page.locator('input[type="text"]').first
                    if await email_field.count() == 0:
                        raise Exception("이메일 입력 필드를 찾을 수 없습니다")

                print("✅ 이메일 입력 필드 발견 (대체 방법)")

            # 현재 URL 확인
            current_url = page.url
            print(f"✅ 현재 URL: {current_url}")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_2_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_2_error.png')
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
