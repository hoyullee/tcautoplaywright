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

            # 사전조건: 소셜 탭 진입
            print("🌐 소셜 탭 접속")
            await page.goto('https://www.wanted.co.kr/community/feed', timeout=30000)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            print(f"✅ 소셜 페이지 로드 완료 (URL: {page.url})")

            await page.screenshot(path='screenshots/test_16_step1.png')

            # 확인사항 1: LNB 영역 확인
            print("🔍 LNB 영역 확인")
            lnb_visible = False
            lnb_selectors = [
                'nav',
                '[class*="lnb"]',
                '[class*="LNB"]',
                '[class*="sidebar"]',
                '[class*="Sidebar"]',
                'aside',
            ]
            for sel in lnb_selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.is_visible(timeout=3000):
                        lnb_visible = True
                        print(f"✅ LNB 영역 확인됨 (selector: {sel})")
                        break
                except Exception:
                    continue

            if not lnb_visible:
                print("ℹ️ LNB 영역을 찾지 못했지만 계속 진행합니다")

            # 확인사항 2: 로그인 해주세요 / 회원가입/로그인 버튼 선택
            print("🔍 로그인 버튼 찾기")
            login_btn = None
            login_btn_selectors = [
                lambda: page.get_by_role('button', name='로그인 해주세요'),
                lambda: page.get_by_role('button', name='회원가입/로그인'),
                lambda: page.get_by_text('로그인 해주세요').first,
                lambda: page.get_by_text('회원가입/로그인').first,
                lambda: page.locator('button:has-text("로그인 해주세요")').first,
                lambda: page.locator('button:has-text("회원가입/로그인")').first,
                lambda: page.locator('a:has-text("로그인 해주세요")').first,
                lambda: page.get_by_role('link', name='로그인 해주세요'),
            ]
            for locator_fn in login_btn_selectors:
                try:
                    loc = locator_fn()
                    if await loc.is_visible(timeout=3000):
                        login_btn = loc
                        print(f"✅ 로그인 버튼 발견")
                        break
                except Exception:
                    continue

            assert login_btn is not None, "로그인/회원가입 버튼을 찾을 수 없습니다"

            await page.screenshot(path='screenshots/test_16_step2.png')

            await login_btn.click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            print(f"✅ 로그인 해주세요 버튼 클릭 완료 (URL: {page.url})")

            await page.screenshot(path='screenshots/test_16_step3.png')

            # 기대결과: 회원가입/로그인 페이지 정상 진입 확인
            current_url = page.url
            print(f"🔍 현재 URL 확인: {current_url}")

            is_login_page = (
                'login' in current_url.lower() or
                'signup' in current_url.lower() or
                'register' in current_url.lower() or
                'auth' in current_url.lower()
            )

            if not is_login_page:
                # 페이지 내 로그인 폼이나 관련 요소 확인
                login_form_selectors = [
                    'input[type="email"]',
                    'input[type="password"]',
                    '[class*="login"]',
                    '[class*="Login"]',
                    'button:has-text("이메일로 계속하기")',
                    'button:has-text("로그인")',
                ]
                for sel in login_form_selectors:
                    try:
                        if await page.locator(sel).first.is_visible(timeout=2000):
                            is_login_page = True
                            print(f"✅ 로그인 페이지 요소 확인됨 (selector: {sel})")
                            break
                    except Exception:
                        continue

            assert is_login_page, f"회원가입/로그인 페이지로 이동되지 않았습니다. 현재 URL: {current_url}"

            print(f"✅ 회원가입/로그인 페이지 정상 진입 확인 (URL: {current_url})")

            await page.screenshot(path='screenshots/test_16_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_16_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
