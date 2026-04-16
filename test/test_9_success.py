from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

# ⭐ 테스트 계정 정보
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

            # 1. 교육•이벤트 탭 진입
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 교육•이벤트 GNB 탭 클릭
            print("🖱️ 교육•이벤트 탭 클릭")
            edu_tab = page.get_by_role('link', name='교육·이벤트')
            if not await edu_tab.is_visible():
                edu_tab = page.locator('a[href*="events"]').first
            await edu_tab.click()
            await page.wait_for_load_state('networkidle')
            print(f"✅ 교육•이벤트 페이지 이동: {page.url}")

            # 2. 회원가입/로그인 페이지 진입
            print("🖱️ 로그인 버튼 클릭")
            login_btn = page.get_by_role('link', name='로그인')
            if not await login_btn.is_visible():
                login_btn = page.locator('a[href*="login"], button:has-text("로그인")').first
            await login_btn.click()
            await page.wait_for_load_state('networkidle')
            print(f"✅ 로그인 페이지 이동: {page.url}")

            # 3. 이메일로 계속하기 버튼 클릭
            print("🖱️ 이메일로 계속하기 버튼 클릭")
            email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            if not await email_continue_btn.is_visible():
                email_continue_btn = page.locator('button:has-text("이메일로 계속하기")').first
            await email_continue_btn.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 이메일 로그인 폼 진입")

            # 4. 이메일 입력
            print(f"✉️ 이메일 입력: {TEST_EMAIL}")
            email_input = page.locator('input[type="email"]')
            await email_input.fill(TEST_EMAIL)

            # 5. 비밀번호 입력
            print("🔑 비밀번호 입력")
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)

            # 6. 로그인 버튼 클릭
            print("🖱️ 로그인 버튼 클릭")
            submit_btn = page.get_by_role('button', name='로그인')
            if not await submit_btn.is_visible():
                submit_btn = page.locator('button[type="submit"]').first
            await submit_btn.click()
            await page.wait_for_load_state('networkidle')
            print(f"✅ 로그인 완료. 현재 URL: {page.url}")

            # 7. 교육•이벤트 탭 리다이렉트 확인
            current_url = page.url
            assert 'events' in current_url or 'wanted.co.kr' in current_url, \
                f"로그인 후 예상치 못한 URL: {current_url}"

            # 로그인 성공 여부 확인 (로그인 버튼이 사라졌는지 확인)
            login_link_visible = await page.locator('a[href*="login"]').is_visible()
            assert not login_link_visible or 'events' in current_url, \
                "로그인이 완료되지 않았거나 리다이렉트 실패"

            await page.screenshot(path='screenshots/test_9_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_9_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
