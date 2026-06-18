import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = ""
TEST_PASSWORD = ""

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        # 비로그인 상태 - 세션 파일 로드 없이 새 컨텍스트 생성
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 탐색 페이지로 이동하여 첫 번째 포지션 카드 링크 추출
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 첫 번째 포지션 카드 링크 찾기
            position_card = page.locator('a[href^="/wd/"]').first
            await position_card.wait_for(state='visible', timeout=10000)
            href = await position_card.get_attribute('href')
            print(f"첫 번째 포지션 링크: {href}")

            # 포지션 상세 페이지로 직접 이동
            position_url = f"https://www.wanted.co.kr{href}"
            await page.goto(position_url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            print(f"포지션 상세 페이지 URL: {page.url}")

            # 지원하기 버튼 클릭
            apply_btn = page.get_by_role('button', name='지원하기')
            apply_btn_count = await apply_btn.count()
            print(f"'지원하기' 버튼 수: {apply_btn_count}")

            if apply_btn_count == 0:
                # 다른 셀렉터로 시도
                apply_btn = page.locator('button:has-text("지원하기")')
                apply_btn_count = await apply_btn.count()
                print(f"'지원하기' button (has-text) 수: {apply_btn_count}")

            assert apply_btn_count > 0, "'지원하기' 버튼을 찾을 수 없습니다"
            await apply_btn.first.wait_for(state='visible', timeout=10000)

            # 클릭 후 페이지 이동 대기
            async with page.expect_navigation(timeout=15000, wait_until='domcontentloaded'):
                await apply_btn.first.click()

            current_url = page.url
            print(f"클릭 후 URL: {current_url}")

            # 로그인/회원가입 페이지 확인
            # 원티드 로그인/회원가입 URL 패턴: /signin, /login, /users/sign_in 등
            login_signup_urls = [
                'signin', 'login', 'sign_in', 'sign-in',
                'signup', 'register', 'join', 'auth'
            ]
            is_login_page = any(pattern in current_url.lower() for pattern in login_signup_urls)

            if not is_login_page:
                # URL 변경이 없는 경우 모달 또는 다이얼로그가 열렸는지 확인
                # 로그인 모달/다이얼로그 탐색
                login_modal = page.locator('[role="dialog"]')
                modal_count = await login_modal.count()
                print(f"다이얼로그 수: {modal_count}")

                if modal_count > 0:
                    modal_text = await login_modal.first.inner_text()
                    print(f"다이얼로그 텍스트 (첫 200자): {modal_text[:200]}")
                    login_keywords = ['로그인', '이메일', '비밀번호', '회원가입', 'sign', 'login']
                    is_login_page = any(kw.lower() in modal_text.lower() for kw in login_keywords)

            if not is_login_page:
                # 페이지 내용에서 로그인 키워드 확인
                page_text = await page.evaluate("() => document.body.innerText || ''")
                login_keywords = ['로그인', '이메일로 로그인', '소셜 로그인', '회원가입']
                matching = [kw for kw in login_keywords if kw in page_text]
                print(f"페이지 내 로그인 키워드: {matching}")
                is_login_page = len(matching) > 0

            assert is_login_page, f"로그인/회원가입 페이지로 이동하지 않았습니다. 현재 URL: {current_url}"
            print(f"✓ 로그인/회원가입 페이지 진입 확인 완료. URL: {current_url}")

            await page.screenshot(path='screenshots/test_50_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_50_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
