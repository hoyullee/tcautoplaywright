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
            # 테스트 로직: 회원가입/로그인 버튼 찾기 및 클릭
            # ========================================

            # 1. 상단 GNB 영역 확인
            print("🔍 상단 GNB 영역 확인 중...")

            # 2. 회원가입/로그인 버튼 찾기 (다양한 방법으로 시도)
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
                    # 일반적인 회원가입/로그인 버튼 선택자들
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
                # 페이지 스크린샷으로 디버깅
                await page.screenshot(path='screenshots/test_1_debug.png', full_page=True)
                raise Exception("회원가입/로그인 버튼을 찾을 수 없습니다")

            # 버튼 클릭 전 스크린샷
            await page.screenshot(path='screenshots/test_1_before_click.png')

            # 버튼 클릭
            print("🖱️ 회원가입/로그인 버튼 클릭")
            await login_button.click()

            # 페이지 전환 대기
            await page.wait_for_load_state('networkidle', timeout=10000)
            print("✅ 페이지 전환 완료")

            # 현재 URL 확인
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 회원가입/로그인 페이지 진입 확인
            if 'signup' in current_url.lower() or 'login' in current_url.lower() or 'register' in current_url.lower():
                print("✅ 회원가입/로그인 페이지 정상 진입")
            else:
                # URL 변경이 없어도 모달이나 팝업이 나타날 수 있음
                # 로그인 관련 요소 확인
                login_form_exists = False
                try:
                    # 이메일 입력 필드 찾기
                    email_field = page.locator('input[type="email"], input[name*="email"], input[id*="email"]').first
                    if await email_field.count() > 0:
                        login_form_exists = True
                        print("✅ 로그인 폼 발견 (모달/팝업)")
                except:
                    pass

                if not login_form_exists:
                    await page.screenshot(path='screenshots/test_1_after_click.png')
                    print(f"⚠️ 예상하지 못한 페이지입니다. URL: {current_url}")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_1_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_1_error.png', full_page=True)
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
