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
            print("[INFO] wanted.co.kr 소셜 페이지 접속 중 (비로그인 상태)...")
            await page.goto('https://www.wanted.co.kr/community', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            current_url = page.url
            print(f"[OK] 소셜 페이지 로드 완료 - URL: {current_url}")
            await page.screenshot(path='screenshots/test_26_step1_social.png')

            # 2. LNB 영역에서 '로그인 해주세요' 버튼 탐색
            print("[INFO] LNB 영역 '로그인 해주세요' 버튼 탐색 중...")
            login_btn = None

            # 다양한 셀렉터로 시도
            selectors = [
                page.get_by_role('button', name='로그인 해주세요'),
                page.get_by_role('link', name='로그인 해주세요'),
                page.locator('button:has-text("로그인 해주세요")').first,
                page.locator('a:has-text("로그인 해주세요")').first,
                page.locator('[class*="login"]:has-text("로그인 해주세요")').first,
                page.locator('text=로그인 해주세요').first,
            ]

            for sel in selectors:
                try:
                    await sel.wait_for(timeout=3000, state='visible')
                    login_btn = sel
                    try:
                        label = await sel.inner_text()
                    except Exception:
                        label = '로그인 해주세요'
                    print(f"[OK] '로그인 해주세요' 버튼 발견: '{label}'")
                    break
                except Exception:
                    continue

            if login_btn is None:
                # 페이지 전체 텍스트 확인 후 디버그
                page_text = await page.inner_text('body')
                print(f"[DEBUG] 페이지 텍스트 일부: {page_text[:500]}")
                await page.screenshot(path='screenshots/test_26_debug.png')

                # URL 조정 시도 - 다른 소셜 관련 경로
                print("[INFO] community 페이지 재시도: /wdtalk 또는 /social 경로 시도...")
                for alt_url in [
                    'https://www.wanted.co.kr/wdtalk',
                    'https://www.wanted.co.kr/social',
                    'https://www.wanted.co.kr/community/list',
                ]:
                    try:
                        await page.goto(alt_url, timeout=30000)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(2000)
                        for sel in selectors:
                            try:
                                await sel.wait_for(timeout=2000, state='visible')
                                login_btn = sel
                                print(f"[OK] '{alt_url}' 에서 '로그인 해주세요' 버튼 발견")
                                break
                            except Exception:
                                continue
                        if login_btn is not None:
                            break
                    except Exception as e:
                        print(f"[WARN] {alt_url} 접속 실패: {e}")
                        continue

            assert login_btn is not None, "LNB 영역에서 '로그인 해주세요' 버튼을 찾을 수 없습니다"

            # 3. '로그인 해주세요' 버튼 클릭
            print("[INFO] '로그인 해주세요' 버튼 클릭 중...")
            await login_btn.click()
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            after_click_url = page.url
            print(f"[INFO] 클릭 후 URL: {after_click_url}")
            await page.screenshot(path='screenshots/test_26_step3_after_click.png')

            # 4. 회원가입/로그인 페이지 진입 확인
            is_login_page = (
                'login' in after_click_url or
                'signin' in after_click_url or
                'signup' in after_click_url or
                'register' in after_click_url or
                'auth' in after_click_url
            )

            if not is_login_page:
                # 모달로 열렸을 가능성 확인
                print("[INFO] URL 변경 없음. 로그인 모달 확인 중...")
                modal_selectors = [
                    page.locator('[class*="modal"]:has-text("이메일")'),
                    page.locator('[class*="login"]:has-text("이메일")'),
                    page.locator('input[type="email"]'),
                    page.locator('button:has-text("이메일로 계속하기")'),
                ]
                modal_found = False
                for modal_sel in modal_selectors:
                    try:
                        await modal_sel.wait_for(timeout=3000, state='visible')
                        modal_found = True
                        print("[OK] 로그인 모달/페이지 요소 발견")
                        break
                    except Exception:
                        continue

                if not modal_found:
                    # 새 탭으로 열렸는지 확인
                    pages = context.pages
                    for p_tab in pages:
                        tab_url = p_tab.url
                        if 'login' in tab_url or 'signin' in tab_url or 'auth' in tab_url:
                            page = p_tab
                            after_click_url = tab_url
                            is_login_page = True
                            print(f"[OK] 새 탭에서 로그인 페이지 발견: {tab_url}")
                            break

                if not modal_found and not is_login_page:
                    assert False, f"회원가입/로그인 페이지 또는 모달을 찾을 수 없습니다. URL: {after_click_url}"
            else:
                print(f"[OK] 회원가입/로그인 페이지 정상 진입 확인: {after_click_url}")

            # 5. 로그인 수행 (세션 저장을 위해)
            print("[INFO] 로그인 수행 중...")

            # '이메일로 계속하기' 버튼 탐색
            email_continue_btn = None
            continue_selectors = [
                page.get_by_role('button', name='이메일로 계속하기'),
                page.locator('button:has-text("이메일로 계속하기")').first,
                page.locator('button:has-text("이메일")').first,
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

            # 이메일 입력
            print("[INFO] 이메일 입력 중...")
            email_input = page.locator('#email, input[type="email"], input[name="email"]').first
            await email_input.wait_for(timeout=10000, state='visible')
            await email_input.fill(TEST_EMAIL)
            print(f"[OK] 이메일 입력 완료: {TEST_EMAIL}")

            # 비밀번호 입력
            print("[INFO] 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]').first
            await password_input.fill(TEST_PASSWORD)
            print("[OK] 비밀번호 입력 완료")

            # 로그인 버튼 클릭
            print("[INFO] 로그인 버튼 클릭 중...")
            submit_btn = page.get_by_role('button', name='로그인')
            await submit_btn.click()

            await page.wait_for_load_state('load', timeout=30000)
            await page.wait_for_timeout(3000)
            final_url = page.url
            print(f"[OK] 로그인 후 최종 URL: {final_url}")

            # 6. 세션 저장
            await context.storage_state(path='work/auth_state.json')
            print("[OK] 세션 저장 완료: work/auth_state.json")

            await page.screenshot(path='screenshots/test_26_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_26_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
