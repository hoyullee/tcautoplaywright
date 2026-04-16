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
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 1. 상단 GNB 영역 확인
            print("🔍 상단 GNB 영역 확인 중...")
            gnb = page.locator('header').first
            await gnb.wait_for(timeout=10000)
            assert await gnb.is_visible(), "GNB 영역이 보이지 않습니다"
            print("✅ GNB 영역 확인 완료")

            # 2. 회원가입/로그인 버튼 선택
            print("🔍 회원가입/로그인 버튼 탐색 중...")
            login_btn = page.get_by_role('link', name='회원가입/로그인')
            if await login_btn.count() == 0:
                login_btn = page.get_by_text('회원가입/로그인')
            if await login_btn.count() == 0:
                login_btn = page.locator('a[href*="login"], a[href*="signup"], button').filter(has_text='로그인')

            await login_btn.first.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 회원가입/로그인 버튼 클릭 완료")

            # 기대결과: 회원가입/로그인 페이지 정상 진입 확인
            current_url = page.url
            print(f"현재 URL: {current_url}")
            assert 'login' in current_url or 'signup' in current_url or 'auth' in current_url, \
                f"회원가입/로그인 페이지 진입 실패. 현재 URL: {current_url}"
            print("✅ 회원가입/로그인 페이지 정상 진입 확인")

            await page.screenshot(path='screenshots/test_1_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_1_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
