from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

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

            # 1단계: 교육•이벤트 페이지로 직접 이동 (사전조건)
            print("🌐 교육•이벤트 페이지 접속")
            await page.goto('https://www.wanted.co.kr/events', timeout=30000)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(1500)
            print(f"✅ 페이지 로드 완료 (URL: {page.url})")

            await page.screenshot(path='screenshots/test_14_step1.png')

            # 2단계: GNB 영역 확인
            print("🔍 GNB 영역 확인")
            gnb = page.locator('nav').first
            assert await gnb.is_visible(), "GNB 영역이 보이지 않습니다"
            print("✅ GNB 영역 확인 완료")

            # 3단계: 회원가입/로그인 버튼 찾기 및 클릭
            print("🔍 회원가입/로그인 버튼 찾기")

            login_btn = None
            selectors = [
                ('role:link', 'name=회원가입/로그인', lambda: page.get_by_role('link', name='회원가입/로그인')),
                ('role:button', 'name=회원가입/로그인', lambda: page.get_by_role('button', name='회원가입/로그인')),
                ('role:link', 'name=로그인', lambda: page.get_by_role('link', name='로그인')),
                ('role:button', 'name=로그인', lambda: page.get_by_role('button', name='로그인')),
                ('text', '회원가입/로그인', lambda: page.get_by_text('회원가입/로그인').first),
                ('text', '로그인', lambda: page.locator('a[href*="login"]').first),
            ]

            for desc_type, desc_name, locator_fn in selectors:
                try:
                    loc = locator_fn()
                    if await loc.is_visible(timeout=3000):
                        print(f"  ✅ 버튼 발견: {desc_type} {desc_name}")
                        login_btn = loc
                        break
                except Exception:
                    continue

            assert login_btn is not None, "회원가입/로그인 버튼을 찾을 수 없습니다"

            # 클릭 전 스크린샷
            await page.screenshot(path='screenshots/test_14_before_click.png')

            await login_btn.click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            print(f"✅ 버튼 클릭 완료 → 현재 URL: {page.url}")

            # 4단계: 회원가입/로그인 페이지 진입 확인
            current_url = page.url
            assert any(keyword in current_url for keyword in ['login', 'signup', 'register', 'auth', 'id.wanted']), \
                f"회원가입/로그인 페이지로 이동되지 않았습니다. 현재 URL: {current_url}"
            print(f"✅ 회원가입/로그인 페이지 정상 진입: {current_url}")

            await page.screenshot(path='screenshots/test_14_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_14_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
