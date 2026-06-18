import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 사전조건: 로그인 상태 + 프로필 페이지 진입
            # 프로필 페이지 = social.wanted.co.kr/my/profile (LNB가 있는 페이지)
            try:
                await page.goto('https://social.wanted.co.kr/my/profile', timeout=30000)
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
            except Exception:
                # networkidle 타임아웃이더라도 페이지 내용이 있으면 계속 진행
                pass

            await page.wait_for_timeout(3000)

            current_url = page.url
            print(f"현재 URL: {current_url}")
            assert 'social.wanted.co.kr' in current_url or 'profile' in current_url, \
                f"프로필 페이지 진입 실패. 현재 URL: {current_url}"

            # LNB 영역에서 로그아웃 버튼 찾기
            # 구조: <button role="listitem" class="wds-1h9bpsd">로그아웃</button>
            logout_btn = None

            # 방법 1: role=button + 텍스트로 찾기
            try:
                el = page.get_by_role('button', name='로그아웃')
                if await el.is_visible():
                    logout_btn = el
                    print("로그아웃 버튼 발견 (get_by_role)")
            except:
                pass

            # 방법 2: get_by_text
            if not logout_btn:
                try:
                    el = page.get_by_text('로그아웃', exact=True)
                    if await el.first.is_visible():
                        logout_btn = el.first
                        print("로그아웃 버튼 발견 (get_by_text)")
                except:
                    pass

            # 방법 3: LNB 클래스 내 button 찾기
            if not logout_btn:
                for sel in [
                    '[class*="LnbDesktop"] button:has-text("로그아웃")',
                    '[class*="pcLnb"] button:has-text("로그아웃")',
                    'button[role="listitem"]:has-text("로그아웃")',
                    'button:has-text("로그아웃")',
                ]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            logout_btn = el
                            print(f"로그아웃 버튼 발견: {sel}")
                            break
                    except:
                        pass

            assert logout_btn is not None, "LNB에서 로그아웃 버튼을 찾을 수 없습니다"

            # 로그아웃 버튼 클릭
            await logout_btn.click()
            await page.wait_for_timeout(2000)

            # 로그아웃 확인 다이얼로그 처리 (있을 경우)
            try:
                dialog = page.locator('[role="dialog"]')
                if await dialog.is_visible(timeout=3000):
                    # 확인/로그아웃 버튼 클릭
                    for confirm_text in ['로그아웃', '확인', 'Logout', 'OK']:
                        try:
                            confirm_btn = dialog.get_by_role('button', name=confirm_text)
                            if await confirm_btn.is_visible(timeout=1000):
                                await confirm_btn.click()
                                print(f"다이얼로그에서 '{confirm_text}' 버튼 클릭")
                                break
                        except:
                            pass
            except:
                pass

            # 페이지 이동 대기
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
            except:
                pass
            await page.wait_for_timeout(2000)

            final_url = page.url
            print(f"로그아웃 후 URL: {final_url}")

            # 채용 홈으로 리다이렉트 확인
            is_home = (
                final_url.rstrip('/') == 'https://www.wanted.co.kr' or
                final_url == 'https://www.wanted.co.kr/'
            )
            is_not_profile = 'profile' not in final_url and 'social.wanted.co.kr' not in final_url

            assert is_home or (is_not_profile and 'wanted.co.kr' in final_url), \
                f"채용 홈 리다이렉트 실패. 현재 URL: {final_url}"
            print(f"로그아웃 성공 - 채용 홈으로 리다이렉트 확인: {final_url}")

            await page.screenshot(path='screenshots/test_05_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_05_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
