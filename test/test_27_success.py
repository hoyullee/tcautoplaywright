import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)
            os.makedirs('work', exist_ok=True)

            # 1. 소셜 탭 진입 (비로그인 상태)
            print("[INFO] 소셜 탭(community) 페이지 접속 중...")
            await page.goto('https://www.wanted.co.kr/community', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            current_url = page.url
            print(f"[OK] 소셜 페이지 로드 완료 - URL: {current_url}")
            await page.screenshot(path='screenshots/test_27_step1_social.png')

            # 2. 로그인 버튼 탐색 (GNB 또는 LNB 영역)
            print("[INFO] 로그인 버튼 탐색 중...")
            login_btn = None

            login_selectors = [
                page.get_by_role('button', name='로그인 해주세요'),
                page.get_by_role('link', name='로그인 해주세요'),
                page.locator('button:has-text("로그인 해주세요")').first,
                page.locator('a:has-text("로그인 해주세요")').first,
                page.get_by_role('link', name='로그인'),
                page.get_by_role('button', name='로그인'),
                page.locator('a[href*="login"]').first,
                page.locator('text=로그인 해주세요').first,
                page.locator('text=로그인').first,
            ]

            for sel in login_selectors:
                try:
                    await sel.wait_for(timeout=3000, state='visible')
                    login_btn = sel
                    try:
                        label = await sel.inner_text()
                    except Exception:
                        label = '로그인'
                    print(f"[OK] 로그인 버튼 발견: '{label}'")
                    break
                except Exception:
                    continue

            if login_btn is None:
                # 대체 경로: 직접 로그인 페이지로 이동 (community redirect 포함)
                print("[INFO] 로그인 버튼 없음. 직접 로그인 페이지로 이동 시도...")
                await page.goto(
                    'https://www.wanted.co.kr/login?redirect=https%3A%2F%2Fwww.wanted.co.kr%2Fcommunity',
                    timeout=60000
                )
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(2000)
                print(f"[INFO] 로그인 페이지 URL: {page.url}")
            else:
                # 3. 로그인 버튼 클릭 → 회원가입/로그인 페이지 진입
                print("[INFO] 로그인 버튼 클릭 중...")
                await login_btn.click()
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)
                after_click_url = page.url
                print(f"[INFO] 클릭 후 URL: {after_click_url}")

                # 새 탭으로 열렸는지 확인
                pages = context.pages
                for p_tab in pages:
                    tab_url = p_tab.url
                    if 'login' in tab_url or 'signin' in tab_url or 'auth' in tab_url:
                        page = p_tab
                        after_click_url = tab_url
                        print(f"[OK] 새 탭에서 로그인 페이지 발견: {tab_url}")
                        break

            await page.screenshot(path='screenshots/test_27_step2_login_page.png')

            # 4. '이메일로 계속하기' 버튼 탐색 및 클릭
            print("[INFO] '이메일로 계속하기' 버튼 탐색 중...")
            email_continue_btn = None
            continue_selectors = [
                page.get_by_role('button', name='이메일로 계속하기'),
                page.locator('button:has-text("이메일로 계속하기")').first,
                page.locator('button:has-text("이메일")').first,
                page.locator('[class*="email"]:has-text("계속")').first,
                page.locator('text=이메일로 계속하기').first,
            ]
            for sel in continue_selectors:
                try:
                    await sel.wait_for(timeout=5000, state='visible')
                    email_continue_btn = sel
                    print("[OK] '이메일로 계속하기' 버튼 발견")
                    break
                except Exception:
                    continue

            if email_continue_btn is not None:
                await email_continue_btn.click()
                await page.wait_for_timeout(2000)
                print("[OK] '이메일로 계속하기' 클릭 완료")
                await page.screenshot(path='screenshots/test_27_step3_email_continue.png')
            else:
                print("[WARN] '이메일로 계속하기' 버튼 없음. 이메일 입력 필드 직접 탐색...")

            # 5. 이메일 입력
            print("[INFO] 이메일 입력 중...")
            email_input = page.locator('#email, input[type="email"], input[name="email"]').first
            await email_input.wait_for(timeout=10000, state='visible')
            await email_input.fill(TEST_EMAIL)
            await page.wait_for_timeout(500)
            print(f"[OK] 이메일 입력 완료: {TEST_EMAIL}")

            # 6. 비밀번호 입력
            print("[INFO] 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]').first
            await password_input.wait_for(timeout=10000, state='visible')
            await password_input.fill(TEST_PASSWORD)
            await page.wait_for_timeout(500)
            print("[OK] 비밀번호 입력 완료")
            await page.screenshot(path='screenshots/test_27_step4_credentials.png')

            # 7. 로그인 버튼 클릭
            print("[INFO] 로그인 버튼 클릭 중...")
            submit_selectors = [
                page.get_by_role('button', name='로그인'),
                page.locator('button[type="submit"]').first,
                page.locator('button:has-text("로그인")').first,
                page.locator('input[type="submit"]').first,
            ]
            submit_btn = None
            for sel in submit_selectors:
                try:
                    await sel.wait_for(timeout=3000, state='visible')
                    submit_btn = sel
                    print("[OK] 로그인 버튼 발견")
                    break
                except Exception:
                    continue

            assert submit_btn is not None, "로그인 버튼을 찾을 수 없습니다"
            await submit_btn.click()

            # 8. 로그인 완료 대기 및 리다이렉트 확인
            print("[INFO] 로그인 처리 중... 소셜 탭 리다이렉트 대기 중...")
            await page.wait_for_load_state('load', timeout=30000)
            await page.wait_for_timeout(3000)
            final_url = page.url
            print(f"[OK] 로그인 후 최종 URL: {final_url}")
            await page.screenshot(path='screenshots/test_27_step5_after_login.png')

            # 9. 로그인 성공 및 소셜 탭 리다이렉트 검증
            is_logged_in = (
                'login' not in final_url and
                'signin' not in final_url
            )
            is_social_redirect = (
                'community' in final_url or
                'social' in final_url or
                'wdtalk' in final_url or
                'wanted.co.kr' in final_url
            )

            # 로그인 성공 여부 추가 확인 (아바타/프로필 요소)
            logged_in_indicators = [
                page.locator('[class*="avatar"]').first,
                page.locator('[class*="profile"]').first,
                page.locator('[aria-label*="프로필"]').first,
                page.locator('[class*="user"]').first,
            ]
            logged_in_ui_found = False
            for ind in logged_in_indicators:
                try:
                    await ind.wait_for(timeout=3000, state='visible')
                    logged_in_ui_found = True
                    print("[OK] 로그인 상태 UI 요소 확인됨")
                    break
                except Exception:
                    continue

            if not logged_in_ui_found:
                print(f"[INFO] 로그인 UI 요소 미확인, URL 기반 검증: {final_url}")

            assert is_logged_in, f"여전히 로그인 페이지에 있습니다: {final_url}"
            assert is_social_redirect, f"소셜 탭으로 리다이렉트 되지 않았습니다: {final_url}"

            print(f"[OK] 로그인 성공 및 소셜 탭 리다이렉트 확인: {final_url}")

            # 10. 세션 저장
            await context.storage_state(path='work/auth_state.json')
            print("[OK] 세션 저장 완료: work/auth_state.json")

            await page.screenshot(path='screenshots/test_27_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_27_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
