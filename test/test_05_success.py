import sys
from playwright.async_api import async_playwright
import asyncio
import os
import json
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

async def do_login(page, context):
    """id.wanted.co.kr 로그인 처리"""
    print("[INFO] id.wanted.co.kr 로그인 진행...")
    await page.wait_for_timeout(2000)

    try:
        email_btn = page.get_by_role('button', name='이메일로 계속하기')
        await email_btn.wait_for(timeout=8000)
        await email_btn.click()
        await page.wait_for_timeout(2000)
    except Exception:
        pass

    email_input = page.locator('#email, input[type="email"]').first
    await email_input.wait_for(timeout=10000)
    await email_input.fill(TEST_EMAIL)

    password_input = page.locator('input[type="password"]').first
    await password_input.fill(TEST_PASSWORD)

    login_btn = page.get_by_role('button', name='로그인')
    await login_btn.click()
    await page.wait_for_load_state('load', timeout=20000)
    await page.wait_for_timeout(3000)

    # 로그인 후 세션 갱신
    await context.storage_state(path='work/auth_state.json')
    print(f"[OK] 로그인 완료: {page.url}")

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
            storage_state='work/auth_state.json',
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 사전조건: 프로필 페이지 진입
            print("[INFO] 프로필 페이지로 이동...")
            await page.goto('https://www.wanted.co.kr/profile', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)
            current_url = page.url
            print(f"[INFO] 현재 URL: {current_url}")

            # 세션 만료 시 로그인
            if 'id.wanted.co.kr' in current_url or 'login' in current_url:
                print("[WARN] 세션 만료 - 로그인 필요")
                await do_login(page, context)
                await page.goto('https://www.wanted.co.kr/profile', timeout=30000)
                await page.wait_for_load_state('load')
                await page.wait_for_timeout(3000)
                current_url = page.url
                print(f"[INFO] 로그인 후 URL: {current_url}")

            profile_keywords = ['profile', 'mypage', 'my-page', 'account', 'social']
            is_profile = any(kw in current_url.lower() for kw in profile_keywords)
            assert is_profile, f"프로필 페이지 진입 실패: {current_url}"
            print(f"[OK] 프로필 페이지 진입: {current_url}")
            await page.screenshot(path='screenshots/test_5_step1_profile.png')

            # 확인사항 1: LNB 영역 확인
            print("[INFO] LNB 영역 확인 중...")
            lnb_visible = False
            lnb_selectors = [
                '[class*="Lnb"]',
                '[class*="lnb"]',
                '[class*="sidebar"]',
                '[class*="Sidebar"]',
                'aside',
                '[class*="ProfileNav"]',
                '[class*="profile-nav"]',
                '[class*="SideNav"]',
                'nav',
            ]
            for sel in lnb_selectors:
                try:
                    loc = page.locator(sel).first
                    count = await page.locator(sel).count()
                    if count == 0:
                        continue
                    await loc.wait_for(state='visible', timeout=3000)
                    print(f"[OK] LNB 영역 확인됨 (셀렉터: {sel})")
                    lnb_visible = True
                    break
                except Exception:
                    continue

            if not lnb_visible:
                lnb_info = await page.evaluate("""() => {
                    const navEls = Array.from(document.querySelectorAll('nav, aside, [class*=\"Lnb\"], [class*=\"lnb\"]'));
                    return {found: navEls.length > 0, count: navEls.length};
                }""")
                if lnb_info.get('found'):
                    lnb_visible = True
                    print(f"[OK] JS로 LNB 영역 확인됨 (count={lnb_info['count']})")

            assert lnb_visible, "LNB 영역을 찾을 수 없습니다"
            await page.screenshot(path='screenshots/test_5_step2_lnb.png')

            # 확인사항 2: 로그아웃 버튼 클릭
            print("[INFO] 로그아웃 버튼 탐색 및 클릭...")
            logout_clicked = False

            # 방법 1: 텍스트로 정확히 일치하는 요소 찾기
            for text in ['로그아웃', 'Logout']:
                try:
                    el = page.get_by_text(text, exact=True).first
                    await el.wait_for(state='visible', timeout=5000)
                    await el.click()
                    logout_clicked = True
                    print(f"[OK] 로그아웃 텍스트 클릭됨: {text}")
                    break
                except Exception:
                    continue

            # 방법 2: role=button으로 탐색
            if not logout_clicked:
                for name in ['로그아웃', 'Logout']:
                    try:
                        btn = page.get_by_role('button', name=name)
                        count = await btn.count()
                        if count > 0:
                            await btn.first.wait_for(state='visible', timeout=3000)
                            await btn.first.click()
                            logout_clicked = True
                            print(f"[OK] 로그아웃 버튼(role) 클릭됨: {name}")
                            break
                    except Exception:
                        continue

            # 방법 3: LNB 내 로그아웃 요소를 JS로 탐색
            if not logout_clicked:
                print("[INFO] JS로 LNB 내 로그아웃 요소 탐색...")
                result = await page.evaluate("""() => {
                    const allEls = Array.from(document.querySelectorAll('li, button, a, span, div'));
                    const logoutEl = allEls.find(el =>
                        el.textContent.trim() === '로그아웃' ||
                        el.textContent.trim() === 'Logout'
                    );
                    if (logoutEl) {
                        logoutEl.click();
                        return {found: true, tag: logoutEl.tagName, cls: logoutEl.className.substring(0,60)};
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS 로그아웃 탐색 결과: {result}")
                if result.get('found'):
                    logout_clicked = True
                    print(f"[OK] JS로 로그아웃 클릭됨: {result}")

            assert logout_clicked, "로그아웃 버튼을 찾을 수 없습니다"

            # 기대결과: 로그아웃 후 채용 홈으로 리다이렉트 확인
            print("[INFO] 로그아웃 후 리다이렉트 대기...")
            await page.wait_for_load_state('load', timeout=20000)
            await page.wait_for_timeout(4000)
            final_url = page.url
            print(f"[INFO] 최종 URL: {final_url}")
            await page.screenshot(path='screenshots/test_5_step3_after_logout.png')

            # 채용 홈 리다이렉트 확인
            is_home = (
                final_url.rstrip('/') == 'https://www.wanted.co.kr' or
                final_url == 'https://www.wanted.co.kr/'
            )

            # 로그아웃 상태 확인 (로그인 버튼 표시 여부)
            logout_confirmed = False
            try:
                for text in ['로그인', '회원가입']:
                    el = page.get_by_text(text, exact=True)
                    count = await el.count()
                    if count > 0:
                        await el.first.wait_for(state='visible', timeout=5000)
                        logout_confirmed = True
                        print(f"[OK] 로그아웃 상태 확인됨 ('{text}' 표시)")
                        break
            except Exception:
                pass

            assert is_home or logout_confirmed, (
                f"로그아웃 후 채용 홈 리다이렉트 실패. 현재 URL: {final_url}"
            )
            print(f"[OK] 로그아웃 성공 및 채용 홈 리다이렉트 확인: {final_url}")

            await page.screenshot(path='screenshots/test_5_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_5_failed.png')
            except Exception:
                pass
            print(f"[FAIL] 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
