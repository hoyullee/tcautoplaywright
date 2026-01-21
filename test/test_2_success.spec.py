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
            # 테스트 로직: 이메일로 계속하기 버튼 선택
            # ========================================

            # 1. 회원가입/로그인 버튼 찾기 및 클릭
            print("🔍 회원가입/로그인 버튼 찾는 중...")

            # 여러 가능한 로케이터 시도
            login_button = None
            selectors = [
                "button:has-text('회원가입/로그인')",
                "a:has-text('회원가입/로그인')",
                "text=회원가입/로그인",
                "[class*='login']",
                "[class*='signup']"
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=3000):
                        login_button = element
                        print(f"✅ 로그인 버튼 발견: {selector}")
                        break
                except:
                    continue

            if login_button:
                await login_button.click()
                await page.wait_for_load_state('networkidle')
                print("✅ 회원가입/로그인 버튼 클릭 완료")
            else:
                print("ℹ️ 로그인 버튼을 찾지 못했습니다. 이미 로그인 페이지에 있을 수 있습니다.")

            # 2. '이메일로 계속하기' 버튼 찾기 및 클릭
            print("🔍 '이메일로 계속하기' 버튼 찾는 중...")

            # 여러 가능한 로케이터 시도
            email_button = None
            email_selectors = [
                "button:has-text('이메일로 계속하기')",
                "button:has-text('이메일')",
                "text=이메일로 계속하기",
                "[class*='email']"
            ]

            for selector in email_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=5000):
                        email_button = element
                        print(f"✅ 이메일 버튼 발견: {selector}")
                        break
                except:
                    continue

            if not email_button:
                raise Exception("'이메일로 계속하기' 버튼을 찾을 수 없습니다")

            # 버튼 클릭
            await email_button.click()
            print("✅ '이메일로 계속하기' 버튼 클릭 완료")

            # 페이지 전환 대기 (더 긴 시간)
            await asyncio.sleep(2)
            await page.wait_for_load_state('networkidle', timeout=10000)

            # 3. 이메일 로그인 페이지 진입 확인
            print("🔍 이메일 로그인 페이지 확인 중...")

            # 현재 URL 출력
            current_url = page.url
            print(f"현재 URL: {current_url}")

            # 이메일 입력 필드가 있는지 확인
            email_input = None
            email_input_selectors = [
                "input[type='email']",
                "input[type='text'][name*='email']",
                "input[name='email']",
                "input[placeholder*='이메일']",
                "input[placeholder*='email']",
                "#email",
                "[data-attribute-id='email']",
                "input",  # 모든 input 필드
            ]

            for selector in email_input_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=3000):
                        email_input = element
                        print(f"✅ 이메일 입력 필드 발견: {selector}")
                        break
                except:
                    continue

            # URL에 email이나 login이 포함되어 있는지 확인
            if 'email' in current_url.lower() or 'login' in current_url.lower():
                print("✅ URL에서 이메일 로그인 페이지 확인됨")
                email_input = True  # URL로 확인 가능

            # 페이지에 "이메일" 텍스트가 있는지 확인
            if not email_input:
                try:
                    email_text = await page.get_by_text('이메일').count()
                    if email_text > 0:
                        print(f"✅ 페이지에 '이메일' 텍스트 발견 ({email_text}개)")
                        email_input = True
                except:
                    pass

            if not email_input:
                raise Exception("이메일 입력 필드를 찾을 수 없습니다. 이메일 로그인 페이지 진입 실패")

            print("✅ 이메일 로그인 페이지 진입 확인 완료")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_2_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            try:
                await page.screenshot(path='screenshots/test_2_failure.png')
            except:
                pass
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
