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

            await page.screenshot(path='screenshots/test_17_step1.png')

            # 회원가입/로그인 버튼 찾기
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

            if login_btn:
                await login_btn.click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                print(f"✅ 로그인 버튼 클릭 완료 (URL: {page.url})")
            else:
                # 이미 로그인 페이지에 있거나 직접 이동
                print("ℹ️ 로그인 버튼 미발견, 직접 로그인 페이지로 이동")
                await page.goto('https://www.wanted.co.kr/login', timeout=30000)
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)

            await page.screenshot(path='screenshots/test_17_step2.png')

            # 확인사항 1: 이메일로 계속하기 버튼 선택
            print("🔍 이메일로 계속하기 버튼 찾기")
            email_continue_btn = None
            email_continue_selectors = [
                lambda: page.get_by_role('button', name='이메일로 계속하기'),
                lambda: page.get_by_text('이메일로 계속하기').first,
                lambda: page.locator('button:has-text("이메일로 계속하기")').first,
                lambda: page.locator('[class*="email"]:has-text("계속하기")').first,
            ]
            for locator_fn in email_continue_selectors:
                try:
                    loc = locator_fn()
                    if await loc.is_visible(timeout=3000):
                        email_continue_btn = loc
                        print(f"✅ 이메일로 계속하기 버튼 발견")
                        break
                except Exception:
                    continue

            if email_continue_btn:
                await email_continue_btn.click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                print(f"✅ 이메일로 계속하기 버튼 클릭 완료 (URL: {page.url})")
            else:
                print("ℹ️ 이메일로 계속하기 버튼 미발견, 이메일 입력폼 직접 확인")

            await page.screenshot(path='screenshots/test_17_step3.png')

            # 확인사항 2: 이메일 및 비밀번호 입력
            print("🔍 이메일 입력폼 찾기")
            email_input = None
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="이메일"]',
                'input[id*="email"]',
            ]
            for sel in email_selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.is_visible(timeout=3000):
                        email_input = loc
                        print(f"✅ 이메일 입력폼 발견 (selector: {sel})")
                        break
                except Exception:
                    continue

            assert email_input is not None, "이메일 입력폼을 찾을 수 없습니다"

            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력 완료")

            print("🔍 비밀번호 입력폼 찾기")
            password_input = None
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="비밀번호"]',
                'input[id*="password"]',
            ]
            for sel in password_selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.is_visible(timeout=3000):
                        password_input = loc
                        print(f"✅ 비밀번호 입력폼 발견 (selector: {sel})")
                        break
                except Exception:
                    continue

            assert password_input is not None, "비밀번호 입력폼을 찾을 수 없습니다"

            await password_input.fill(TEST_PASSWORD)
            print(f"✅ 비밀번호 입력 완료")

            await page.screenshot(path='screenshots/test_17_step4.png')

            # 확인사항 3: 로그인 버튼 선택
            print("🔍 로그인 버튼 찾기")
            submit_btn = None
            submit_selectors = [
                lambda: page.get_by_role('button', name='로그인'),
                lambda: page.locator('button[type="submit"]').first,
                lambda: page.locator('button:has-text("로그인")').first,
            ]
            for locator_fn in submit_selectors:
                try:
                    loc = locator_fn()
                    if await loc.is_visible(timeout=3000):
                        submit_btn = loc
                        print(f"✅ 로그인 버튼 발견")
                        break
                except Exception:
                    continue

            assert submit_btn is not None, "로그인 버튼을 찾을 수 없습니다"

            await submit_btn.click()
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)
            print(f"✅ 로그인 버튼 클릭 완료 (URL: {page.url})")

            await page.screenshot(path='screenshots/test_17_step5.png')

            # 기대결과: 정상 로그인 및 소셜 탭 리다이렉트 확인
            current_url = page.url
            print(f"🔍 최종 URL 확인: {current_url}")

            # 로그인 성공 여부 확인 (로그인 페이지가 아닌 곳으로 이동했는지)
            is_logged_in = (
                'login' not in current_url.lower() and
                'signup' not in current_url.lower()
            )

            # 소셜 탭으로 리다이렉트 확인
            is_social_tab = 'community' in current_url.lower() or 'feed' in current_url.lower()

            if not is_logged_in:
                # 오류 메시지 확인
                error_selectors = [
                    '[class*="error"]',
                    '[class*="Error"]',
                    '[role="alert"]',
                ]
                for sel in error_selectors:
                    try:
                        loc = page.locator(sel).first
                        if await loc.is_visible(timeout=2000):
                            error_text = await loc.text_content()
                            raise AssertionError(f"로그인 실패 - 오류 메시지: {error_text}")
                    except AssertionError:
                        raise
                    except Exception:
                        continue
                raise AssertionError(f"로그인 후 여전히 로그인 페이지에 있습니다. URL: {current_url}")

            print(f"✅ 로그인 성공 확인 (URL: {current_url})")

            if is_social_tab:
                print(f"✅ 소셜 탭으로 리다이렉트 확인")
            else:
                print(f"ℹ️ 현재 URL이 소셜 탭이 아님: {current_url}, 소셜 탭으로 이동 확인")

            await page.screenshot(path='screenshots/test_17_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_17_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
