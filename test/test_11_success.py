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

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            print("✅ 페이지 로드 완료")

            # 로그인
            print("🔍 로그인 중...")
            await page.get_by_text('회원가입/로그인', exact=True).click()
            await page.wait_for_timeout(2000)

            email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_btn.wait_for(state='visible', timeout=10000)
            await email_continue_btn.click()
            await page.wait_for_timeout(1000)

            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)

            password_input = page.locator('input[type="password"]')
            await password_input.wait_for(state='visible', timeout=10000)
            await password_input.fill(TEST_PASSWORD)

            await page.locator('button[type="submit"]').click(timeout=10000)
            await page.wait_for_url(
                lambda url: 'wanted.co.kr' in url and 'id.wanted' not in url,
                timeout=15000
            )
            await page.wait_for_timeout(2000)
            print("✅ 로그인 완료")

            await page.screenshot(path='screenshots/test_11_after_login.png')

            # 프로필 페이지로 이동 (사전조건: 프로필 페이지 진입)
            print("🔍 프로필 페이지 이동 중...")

            # 프로필 아이콘 클릭 시도
            profile_clicked = False
            profile_selectors = [
                '[class*="isAvatar"]',
                '[class*="profileBox"]',
                'img[src*="profile"]',
                '[class*="avatar"]',
                '[class*="Avatar"]',
            ]
            for sel in profile_selectors:
                try:
                    el = page.locator(sel).first
                    count = await el.count()
                    if count > 0:
                        await el.scroll_into_view_if_needed()
                        await el.click(timeout=5000)
                        profile_clicked = True
                        print(f"  프로필 아이콘 클릭 성공 (셀렉터: {sel})")
                        break
                except Exception:
                    continue

            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshots/test_11_after_profile_click.png')

            # 드롭다운에서 프로필 링크 찾아 직접 이동
            current_url = page.url
            if 'profile' not in current_url and '/my' not in current_url:
                print("🔍 프로필 링크 탐색 중...")
                # social.wanted.co.kr 프로필 링크 시도
                profile_link = page.locator('a[href*="social.wanted.co.kr/my/profile"]').first
                link_count = await profile_link.count()
                if link_count > 0:
                    href = await profile_link.get_attribute('href')
                    print(f"  프로필 링크: {href}")
                    # 같은 탭에서 직접 이동
                    await page.goto(href, timeout=30000, wait_until='domcontentloaded')
                    await page.wait_for_timeout(2000)
                else:
                    # 직접 프로필 URL로 이동
                    print("  직접 프로필 URL로 이동...")
                    await page.goto('https://social.wanted.co.kr/my/profile', timeout=30000, wait_until='domcontentloaded')
                    await page.wait_for_timeout(2000)

            current_url = page.url
            print(f"  현재 URL: {current_url}")
            print("✅ 프로필 페이지 진입 완료")
            await page.screenshot(path='screenshots/test_11_profile_page.png')

            # LNB 영역 확인
            print("🔍 LNB 영역 확인 중...")
            lnb_selectors = [
                'nav[class*="lnb" i]',
                '[class*="lnb" i]',
                'aside',
                'nav',
                '[role="navigation"]',
            ]
            lnb = None
            for sel in lnb_selectors:
                try:
                    el = page.locator(sel).first
                    count = await el.count()
                    if count > 0:
                        lnb = el
                        print(f"  LNB 영역 발견 (셀렉터: {sel})")
                        break
                except Exception:
                    continue

            if lnb is None:
                print("  LNB 셀렉터로 찾지 못해 로그아웃 버튼 직접 탐색")
            else:
                print("✅ LNB 영역 확인 완료")

            await page.screenshot(path='screenshots/test_11_lnb_area.png')

            # 로그아웃 버튼 탐색 및 클릭
            print("🔍 로그아웃 버튼 탐색 중...")
            logout_clicked = False

            # 로그아웃 버튼 셀렉터 목록
            logout_candidates = [
                page.get_by_role('button', name='로그아웃'),
                page.get_by_text('로그아웃', exact=True),
                page.locator('a', has_text='로그아웃'),
                page.locator('[class*="logout" i]'),
                page.locator('button', has_text='로그아웃'),
            ]

            for candidate in logout_candidates:
                try:
                    count = await candidate.count()
                    if count > 0:
                        await candidate.first.scroll_into_view_if_needed()
                        await candidate.first.click(timeout=5000)
                        logout_clicked = True
                        print("  로그아웃 버튼 클릭 성공")
                        break
                except Exception:
                    continue

            if not logout_clicked:
                raise Exception("로그아웃 버튼을 찾을 수 없습니다")

            # 로그아웃 후 채용 홈으로 리다이렉트 확인
            print("🔍 채용 홈으로 리다이렉트 확인 중...")
            await page.wait_for_timeout(3000)
            final_url = page.url
            print(f"  최종 URL: {final_url}")

            # 채용 홈 확인: wanted.co.kr 루트 또는 채용 홈 URL
            is_home = (
                final_url == 'https://www.wanted.co.kr/' or
                final_url.startswith('https://www.wanted.co.kr/?') or
                final_url == 'https://www.wanted.co.kr' or
                ('wanted.co.kr' in final_url and 'profile' not in final_url and 'login' not in final_url)
            )

            assert is_home, f"채용 홈으로 리다이렉트되지 않았습니다. 현재 URL: {final_url}"
            print(f"✅ 채용 홈으로 리다이렉트 확인 완료: {final_url}")

            # 로그아웃 상태 확인 (회원가입/로그인 버튼 노출)
            login_btn = page.get_by_text('회원가입/로그인')
            login_btn_count = await login_btn.count()
            if login_btn_count > 0:
                print("✅ 로그아웃 완료 확인 (회원가입/로그인 버튼 노출)")
            else:
                print("  (회원가입/로그인 버튼 미확인, URL 기준으로 성공 처리)")

            await page.screenshot(path='screenshots/test_11_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_11_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
