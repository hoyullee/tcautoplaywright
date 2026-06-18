import sys
from playwright.async_api import async_playwright
import asyncio
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
            os.makedirs('work', exist_ok=True)

            # 사전조건 1: 교육•이벤트 탭 진입
            await page.goto('https://event.wanted.co.kr/', timeout=30000)
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            print(f"교육이벤트 페이지 진입: {page.url}")

            # 사전조건 2: 회원가입/로그인 페이지 진입 - 로그인 버튼 찾기
            login_btn = None

            # 방법 1: 회원가입/로그인 버튼 텍스트로 찾기
            for btn_text in ['회원가입/로그인', '로그인', '회원가입']:
                try:
                    el = page.get_by_role('button', name=btn_text)
                    if await el.first.is_visible(timeout=3000):
                        login_btn = el.first
                        print(f"로그인 버튼 발견 (get_by_role): {btn_text}")
                        break
                except Exception:
                    pass

            # 방법 2: 링크로 찾기
            if not login_btn:
                for link_text in ['회원가입/로그인', '로그인', '회원가입']:
                    try:
                        el = page.get_by_role('link', name=link_text)
                        if await el.first.is_visible(timeout=3000):
                            login_btn = el.first
                            print(f"로그인 링크 발견 (get_by_role link): {link_text}")
                            break
                    except Exception:
                        pass

            # 방법 3: 텍스트로 찾기
            if not login_btn:
                for text in ['회원가입/로그인', '로그인']:
                    try:
                        el = page.get_by_text(text, exact=True)
                        if await el.first.is_visible(timeout=3000):
                            login_btn = el.first
                            print(f"로그인 요소 발견 (get_by_text): {text}")
                            break
                    except Exception:
                        pass

            # 방법 4: CSS 셀렉터로 찾기
            if not login_btn:
                for sel in [
                    'a[href*="login"]',
                    'a[href*="signin"]',
                    'button:has-text("로그인")',
                    '[class*="login"]',
                    '[class*="signin"]',
                ]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible(timeout=2000):
                            login_btn = el
                            print(f"로그인 버튼 발견 (CSS): {sel}")
                            break
                    except Exception:
                        pass

            assert login_btn is not None, "회원가입/로그인 버튼을 찾을 수 없습니다"

            # 로그인 버튼 클릭
            await login_btn.click()
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            print(f"로그인 페이지 진입: {page.url}")

            # 확인사항 1: 이메일로 시작하기 버튼 선택
            email_start_btn = None

            for btn_text in ['이메일로 시작하기', '이메일로 계속하기', '이메일로 로그인', '이메일 로그인']:
                try:
                    el = page.get_by_role('button', name=btn_text)
                    if await el.first.is_visible(timeout=3000):
                        email_start_btn = el.first
                        print(f"이메일로 시작하기 버튼 발견: {btn_text}")
                        break
                except Exception:
                    pass

            if not email_start_btn:
                for text in ['이메일로 시작하기', '이메일로 계속하기', '이메일로 로그인']:
                    try:
                        el = page.get_by_text(text, exact=True)
                        if await el.first.is_visible(timeout=3000):
                            email_start_btn = el.first
                            print(f"이메일로 시작하기 텍스트 발견: {text}")
                            break
                    except Exception:
                        pass

            assert email_start_btn is not None, "이메일로 시작하기 버튼을 찾을 수 없습니다"

            await email_start_btn.click()
            await page.wait_for_timeout(1500)
            print("이메일로 시작하기 버튼 클릭 완료")

            # 확인사항 2: 이메일 및 비밀번호 입력
            # 이메일 입력
            email_input = None
            for sel in [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="이메일"]',
                'input[id*="email"]',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=3000):
                        email_input = el
                        print(f"이메일 입력 필드 발견: {sel}")
                        break
                except Exception:
                    pass

            assert email_input is not None, "이메일 입력 필드를 찾을 수 없습니다"
            await email_input.fill(TEST_EMAIL)
            print(f"이메일 입력: {TEST_EMAIL}")

            # 비밀번호 입력
            password_input = None
            for sel in [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="비밀번호"]',
                'input[id*="password"]',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=3000):
                        password_input = el
                        print(f"비밀번호 입력 필드 발견: {sel}")
                        break
                except Exception:
                    pass

            assert password_input is not None, "비밀번호 입력 필드를 찾을 수 없습니다"
            await password_input.fill(TEST_PASSWORD)
            print("비밀번호 입력 완료")

            # 확인사항 3: 로그인 버튼 선택
            submit_btn = None

            for btn_text in ['로그인', '로그인하기', '로그인 하기', '이메일로 로그인']:
                try:
                    el = page.get_by_role('button', name=btn_text)
                    if await el.first.is_visible(timeout=3000):
                        submit_btn = el.first
                        print(f"로그인 제출 버튼 발견: {btn_text}")
                        break
                except Exception:
                    pass

            if not submit_btn:
                for sel in [
                    'button[type="submit"]',
                    'button:has-text("로그인")',
                ]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible(timeout=2000):
                            submit_btn = el
                            print(f"로그인 제출 버튼 발견 (CSS): {sel}")
                            break
                    except Exception:
                        pass

            assert submit_btn is not None, "로그인 버튼을 찾을 수 없습니다"

            await submit_btn.click()
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=20000)
            except Exception:
                pass
            await page.wait_for_timeout(3000)

            final_url = page.url
            print(f"로그인 후 URL: {final_url}")

            # 기대결과: 정상 로그인 및 교육•이벤트 페이지로 리다이렉트
            is_event_page = 'event.wanted.co.kr' in final_url
            assert is_event_page, f"교육이벤트 페이지 리다이렉트 실패. 현재 URL: {final_url}"
            print(f"로그인 성공 - 교육이벤트 페이지로 리다이렉트 확인: {final_url}")

            # 세션 저장
            await context.storage_state(path='work/auth_state.json')
            print("세션 저장 완료: work/auth_state.json")

            await page.screenshot(path='screenshots/test_36_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_36_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
