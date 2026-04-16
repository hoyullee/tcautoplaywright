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
            # 1단계: 소셜 탭 진입
            # ========================================
            print("🔍 소셜 탭 클릭 시도...")
            await page.screenshot(path='screenshots/test_10_before_social.png')

            # 소셜 탭 선택자 시도
            social_selectors = [
                'a[href*="social"]',
                'a[href*="/social"]',
                'text=소셜',
                '[class*="gnb"] a:has-text("소셜")',
                'nav a:has-text("소셜")',
                'a:has-text("소셜")',
            ]
            social_clicked = False
            for selector in social_selectors:
                try:
                    elem = page.locator(selector).first
                    count = await elem.count()
                    if count > 0:
                        await elem.click(timeout=5000)
                        social_clicked = True
                        print(f"✅ 소셜 탭 클릭 성공: {selector}")
                        break
                except Exception:
                    continue

            if not social_clicked:
                raise Exception("소셜 탭을 찾을 수 없습니다")

            await page.wait_for_load_state('networkidle')
            print(f"✅ 소셜 탭 진입 완료, URL: {page.url}")

            # ========================================
            # 2단계: LNB 영역 확인
            # ========================================
            print("🔍 LNB 영역 확인...")
            # LNB(Left Navigation Bar) 영역이 존재하는지 확인
            lnb = page.locator('aside, nav, [class*="lnb"], [class*="LNB"], [class*="sidebar"], [class*="Sidebar"]').first
            await lnb.wait_for(timeout=10000)
            lnb_visible = await lnb.is_visible()
            print(f"✅ LNB 영역 확인: {'표시됨' if lnb_visible else '숨겨짐'}")
            assert lnb_visible, "LNB 영역이 표시되지 않습니다"

            await page.screenshot(path='screenshots/test_10_lnb.png')

            # ========================================
            # 3단계: 로그인 해주세요 버튼 클릭
            # ========================================
            print("🔍 '로그인 해주세요' 버튼 찾기...")
            login_btn = page.get_by_text('로그인 해주세요')
            await login_btn.wait_for(timeout=10000)
            login_btn_visible = await login_btn.is_visible()
            print(f"✅ '로그인 해주세요' 버튼 확인: {'표시됨' if login_btn_visible else '숨겨짐'}")
            assert login_btn_visible, "'로그인 해주세요' 버튼이 표시되지 않습니다"

            await login_btn.click()
            await page.wait_for_load_state('networkidle')
            print("✅ '로그인 해주세요' 버튼 클릭 완료")

            # ========================================
            # 4단계: 회원가입/로그인 페이지 진입 확인
            # ========================================
            print("🔍 회원가입/로그인 페이지 진입 확인...")
            current_url = page.url
            print(f"현재 URL: {current_url}")

            # URL이 로그인 관련 페이지인지 확인
            is_login_page = (
                'login' in current_url or
                'signup' in current_url or
                'register' in current_url or
                'join' in current_url
            )

            # 페이지 내 로그인 폼 요소 확인 (URL 기반 확인이 실패할 경우 대비)
            if not is_login_page:
                email_input = page.locator('input[type="email"], input[name="email"]')
                is_login_page = await email_input.count() > 0

            assert is_login_page, f"회원가입/로그인 페이지로 이동하지 않았습니다. 현재 URL: {current_url}"
            print(f"✅ 회원가입/로그인 페이지 정상 진입 확인: {current_url}")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_10_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            # 실패 스크린샷
            await page.screenshot(path='screenshots/test_10_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
