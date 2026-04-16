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

            # 1. 원티드 메인 접속 후 교육•이벤트 탭 진입
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 2. GNB 영역에서 교육•이벤트 탭 클릭
            print("🔍 교육•이벤트 탭 클릭")
            edu_tab = page.get_by_role('link', name='교육·이벤트')
            if not await edu_tab.is_visible():
                edu_tab = page.locator('a[href*="education"], a[href*="event"]').first
            await edu_tab.click()
            await page.wait_for_load_state('networkidle')
            print(f"✅ 교육•이벤트 탭 클릭 완료, URL: {page.url}")

            # 3. GNB 영역 확인
            print("🔍 GNB 영역 확인")
            gnb = page.locator('header, nav, [class*="gnb"], [class*="GNB"], [class*="header"]').first
            assert await gnb.is_visible(), "GNB 영역이 보이지 않습니다"
            print("✅ GNB 영역 확인 완료")

            # 4. 회원가입/로그인 버튼 클릭
            print("🔍 회원가입/로그인 버튼 찾기")
            login_btn = None
            for selector in [
                page.get_by_role('button', name='회원가입/로그인'),
                page.get_by_role('link', name='회원가입/로그인'),
                page.get_by_text('회원가입/로그인'),
                page.locator('[class*="login"], [class*="Login"]').first,
            ]:
                try:
                    if await selector.is_visible(timeout=3000):
                        login_btn = selector
                        break
                except Exception:
                    continue

            assert login_btn is not None, "회원가입/로그인 버튼을 찾을 수 없습니다"
            await login_btn.click()
            await page.wait_for_load_state('networkidle')
            print(f"✅ 회원가입/로그인 버튼 클릭 완료, URL: {page.url}")

            # 5. 회원가입/로그인 페이지 진입 확인
            current_url = page.url
            assert any(keyword in current_url for keyword in ['login', 'signup', 'register', 'auth']), \
                f"회원가입/로그인 페이지로 이동하지 않았습니다. 현재 URL: {current_url}"
            print(f"✅ 회원가입/로그인 페이지 진입 확인: {current_url}")

            await page.screenshot(path='screenshots/test_8_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_8_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
