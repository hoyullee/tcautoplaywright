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
            headless=True
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
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            print("✅ 페이지 로드 완료")

            # ========================================
            # 테스트 로직: 회원가입/로그인 버튼 클릭
            # ========================================

            # 1. 상단 GNB 영역 확인
            print("🔍 상단 GNB 영역 확인 중...")
            await page.wait_for_selector('header', state='visible', timeout=10000)
            print("✅ GNB 영역 확인 완료")

            # 2. 회원가입/로그인 버튼 찾기 및 클릭
            print("🔍 회원가입/로그인 버튼 찾는 중...")

            # 여러 가능한 선택자 시도
            login_button = None
            selectors = [
                "button:has-text('회원가입/로그인')",
                "a:has-text('회원가입/로그인')",
                "button:has-text('회원가입')",
                "a:has-text('회원가입')",
                "button:has-text('로그인')",
                "a:has-text('로그인')",
                "[data-button-name*='login']",
                "[data-button-name*='signup']"
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        login_button = element
                        print(f"✅ 버튼 발견: {selector}")
                        break
                except:
                    continue

            if login_button is None:
                # 스크린샷 찍어서 확인
                await page.screenshot(path='screenshots/test_1_debug.png', full_page=True)
                raise Exception("회원가입/로그인 버튼을 찾을 수 없습니다")

            # 버튼 클릭
            print("🖱️  회원가입/로그인 버튼 클릭 중...")
            await login_button.click()

            # 페이지 전환 대기
            await page.wait_for_load_state('networkidle', timeout=10000)
            print("✅ 페이지 전환 완료")

            # 3. 회원가입/로그인 페이지 진입 확인
            print("🔍 로그인 페이지 진입 확인 중...")
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # URL 또는 페이지 요소로 로그인 페이지 확인
            is_login_page = False

            # URL 체크
            if 'login' in current_url.lower() or 'signup' in current_url.lower() or 'user' in current_url.lower():
                is_login_page = True
                print("✅ URL 기반 로그인 페이지 확인")

            # 로그인 폼 요소 체크
            login_form_selectors = [
                "input[type='email']",
                "input[type='password']",
                "input[placeholder*='이메일']",
                "input[placeholder*='비밀번호']",
                "form"
            ]

            for selector in login_form_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        is_login_page = True
                        print(f"✅ 로그인 폼 요소 확인: {selector}")
                        break
                except:
                    continue

            if not is_login_page:
                await page.screenshot(path='screenshots/test_1_failed.png', full_page=True)
                raise Exception(f"로그인 페이지로 이동하지 않았습니다. 현재 URL: {current_url}")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_1_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            # 실패 스크린샷
            await page.screenshot(path='screenshots/test_1_failed.png', full_page=True)
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
