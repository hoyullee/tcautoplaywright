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

            # 회원가입/로그인 버튼 클릭
            print("🔍 회원가입/로그인 버튼 클릭 중...")
            await page.get_by_text('회원가입/로그인', exact=True).click()
            await page.wait_for_timeout(2000)

            # 이메일로 계속하기 클릭
            email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_btn.wait_for(state='visible', timeout=10000)
            await email_continue_btn.click()
            await page.wait_for_timeout(1000)

            # 이메일/비밀번호 입력
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)
            password_input = page.locator('input[type="password"]')
            await password_input.wait_for(state='visible', timeout=10000)
            await password_input.fill(TEST_PASSWORD)

            # 로그인 버튼 클릭
            await page.get_by_role('button', name='로그인').click()
            await page.wait_for_url(
                lambda url: url.startswith('https://www.wanted.co.kr'),
                timeout=15000
            )
            await page.wait_for_timeout(2000)
            print("✅ 로그인 완료")

            # GNB 영역 확인 (nav 태그)
            print("🔍 GNB 영역 확인 중...")
            gnb = page.locator('nav').first
            await gnb.wait_for(state='visible', timeout=10000)
            gnb_text = await gnb.inner_text()
            print(f"  GNB 내용: {gnb_text[:80]}")
            print("✅ GNB 영역 확인 완료")

            await page.screenshot(path='screenshots/test_10_after_login.png')

            # 프로필 아이콘 선택 (여러 셀렉터 시도)
            print("🔍 프로필 아이콘 클릭 중...")
            profile_clicked = False
            profile_selectors = [
                '[class*="isAvatar"]',
                '[class*="profileBox"]',
                'img[src*="profile"]',
                '[class*="avatar"]',
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

            if not profile_clicked:
                raise Exception("프로필 아이콘을 찾을 수 없습니다")

            await page.wait_for_timeout(2000)
            print("✅ 프로필 아이콘 클릭 완료")

            await page.screenshot(path='screenshots/test_10_after_profile_click.png')

            # 현재 URL 확인 - 직접 프로필 페이지로 이동했는지 확인
            current_url = page.url
            print(f"현재 URL: {current_url}")

            if 'profile' in current_url or '/my' in current_url or 'social.wanted' in current_url:
                print("✅ 프로필 페이지 직접 진입 확인")
                await page.screenshot(path='screenshots/test_10_success.png')
                print("✅ 테스트 성공")
                print("AUTOMATION_SUCCESS")
                return True

            # 드롭다운에서 프로필 링크 찾아 클릭
            print("🔍 드롭다운에서 프로필 링크 찾는 중...")
            profile_link = page.locator('a[href*="social.wanted.co.kr/my/profile"]').first
            link_count = await profile_link.count()
            if link_count > 0:
                href = await profile_link.get_attribute('href')
                print(f"  프로필 링크: {href}")
                # 새 탭으로 열리는 경우 처리
                async with page.context.expect_page(timeout=15000) as new_page_info:
                    await profile_link.click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded', timeout=20000)
                await new_page.wait_for_timeout(2000)
                current_url = new_page.url
                print(f"이동 후 URL: {current_url}")
                assert 'profile' in current_url or '/my' in current_url or 'social.wanted' in current_url, \
                    f"프로필 페이지 진입 실패. 현재 URL: {current_url}"
                print("✅ 프로필 페이지 진입 확인")
                await new_page.screenshot(path='screenshots/test_10_success.png')
            else:
                raise Exception("드롭다운에서 프로필 링크를 찾을 수 없습니다")

            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_10_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
