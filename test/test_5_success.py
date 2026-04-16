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

            # 1. 채용 홈 접속
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 2. 회원가입/로그인 버튼 클릭
            login_selectors = [
                ('button', '회원가입/로그인'),
                ('link', '회원가입/로그인'),
                ('button', '로그인'),
                ('link', '로그인'),
            ]
            login_clicked = False
            for role, name in login_selectors:
                el = page.get_by_role(role, name=name)
                if await el.count() > 0:
                    await el.first.click()
                    login_clicked = True
                    print(f"✅ 로그인 버튼 클릭: role={role}, name={name}")
                    break
            if not login_clicked:
                # 텍스트로 시도
                el = page.get_by_text('회원가입/로그인')
                if await el.count() > 0:
                    await el.first.click()
                    login_clicked = True
                    print("✅ 텍스트로 로그인 버튼 클릭")
            if not login_clicked:
                raise Exception("회원가입/로그인 버튼을 찾을 수 없습니다")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(1000)
            print("✅ 회원가입/로그인 버튼 클릭 완료")

            # 3. 이메일로 계속하기 클릭
            await page.get_by_role('button', name='이메일로 계속하기').click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(1000)
            print("✅ 이메일 로그인 페이지 진입")

            # 4. 이메일 입력
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력: {TEST_EMAIL}")

            # 5. 비밀번호 입력
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 6. 로그인 버튼 클릭
            await page.get_by_role('button', name='로그인').click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)
            print("✅ 로그인 완료")
            await page.screenshot(path='screenshots/test_5_after_login.png')

            # 7. 프로필 페이지로 이동
            print("👤 프로필 페이지 이동")
            print(f"📍 로그인 후 현재 URL: {page.url}")
            # 프로필 페이지로 직접 이동 (networkidle 대신 load 사용)
            await page.goto('https://www.wanted.co.kr/profile', timeout=30000, wait_until='load')
            await page.wait_for_timeout(3000)
            await page.screenshot(path='screenshots/test_5_profile.png')
            print(f"✅ 프로필 페이지 URL: {page.url}")

            # 8. LNB 영역에서 로그아웃 버튼 탐색 및 클릭
            print("🔍 LNB 영역에서 로그아웃 버튼 탐색")

            logout_selectors = [
                'button:has-text("로그아웃")',
                'a:has-text("로그아웃")',
                '[href*="logout"]',
                'text=로그아웃',
            ]

            logout_clicked = False
            for selector in logout_selectors:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    print(f"✅ 로그아웃 버튼 발견: {selector} ({count}개)")
                    await elements.first.click()
                    logout_clicked = True
                    break

            if not logout_clicked:
                raise Exception("로그아웃 버튼을 찾을 수 없습니다")

            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            print("✅ 로그아웃 버튼 클릭 완료")

            # 9. 채용 홈으로 리다이렉트 확인
            current_url = page.url
            print(f"📍 로그아웃 후 URL: {current_url}")

            assert 'wanted.co.kr' in current_url, f"예상 도메인이 아닙니다: {current_url}"

            # 홈 또는 로그인 페이지로 이동 확인
            is_redirected = (
                current_url in ['https://www.wanted.co.kr/', 'https://www.wanted.co.kr'] or
                '/login' in current_url or
                current_url.rstrip('/') == 'https://www.wanted.co.kr'
            )
            assert is_redirected, f"리다이렉트 실패: {current_url}"
            print(f"✅ 로그아웃 후 채용 홈으로 리다이렉트 확인: {current_url}")

            await page.screenshot(path='screenshots/test_5_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_5_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
