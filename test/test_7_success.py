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
        browser = await p.chromium.launch(headless=True, channel='chrome')

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
            # 확인사항: 1. 상단 GNB 영역 확인
            # ========================================
            print("🔍 상단 GNB 영역 확인 중...")

            # GNB 영역 확인 (header 또는 nav)
            gnb = page.locator('header').first
            await gnb.wait_for(state='visible', timeout=10000)
            print("✅ 상단 GNB 영역 확인 완료")

            # ========================================
            # 확인사항: 2. 회원가입/로그인 버튼 선택
            # ========================================
            print("🔍 회원가입/로그인 버튼 찾는 중...")

            # 회원가입/로그인 버튼 클릭 시도 (다양한 선택자 시도)
            login_btn = None

            # 방법 1: 텍스트로 찾기
            try:
                login_btn = page.get_by_role('link', name='회원가입/로그인')
                await login_btn.wait_for(state='visible', timeout=5000)
                print("✅ '회원가입/로그인' 링크 발견 (role=link)")
            except Exception:
                pass

            if not login_btn or not await login_btn.is_visible():
                try:
                    login_btn = page.get_by_text('회원가입/로그인', exact=True)
                    await login_btn.wait_for(state='visible', timeout=5000)
                    print("✅ '회원가입/로그인' 텍스트 발견")
                except Exception:
                    pass

            if not login_btn or not await login_btn.is_visible():
                try:
                    login_btn = page.locator('a[href*="login"], a[href*="signup"], button').filter(has_text='로그인').first
                    await login_btn.wait_for(state='visible', timeout=5000)
                    print("✅ 로그인 관련 버튼/링크 발견")
                except Exception:
                    pass

            # 버튼 클릭
            await login_btn.click()
            print("✅ 회원가입/로그인 버튼 클릭 완료")

            # 페이지 이동 대기
            await page.wait_for_load_state('networkidle', timeout=15000)

            # 현재 URL 확인
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 회원가입/로그인 페이지 진입 확인
            assert (
                'login' in current_url or
                'signup' in current_url or
                'auth' in current_url or
                'register' in current_url
            ), f"회원가입/로그인 페이지로 이동하지 않음. 현재 URL: {current_url}"

            print("✅ 회원가입/로그인 페이지 정상 진입 확인")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_7_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            # 실패 스크린샷
            await page.screenshot(path='screenshots/test_7_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
