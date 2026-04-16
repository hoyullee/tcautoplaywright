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

            # 페이지 접속
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print("✅ 페이지 로드 완료")

            # 로그인 시작 - "회원가입/로그인" 버튼 클릭
            print("🔐 로그인 시작...")
            await page.get_by_role('button', name='회원가입/로그인').click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # id.wanted.co.kr 로그인 페이지 - "이메일로 계속하기" 클릭
            email_continue = page.get_by_role('button', name='이메일로 계속하기')
            if await email_continue.count() > 0:
                await email_continue.click()
                await page.wait_for_timeout(2000)

            # 이메일/비밀번호 입력
            await page.locator('input[type="email"]').wait_for(state='visible', timeout=10000)
            await page.locator('input[type="email"]').fill(TEST_EMAIL)
            await page.locator('input[type="password"]').fill(TEST_PASSWORD)
            await page.get_by_role('button', name='로그인').click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"✅ 로그인 완료, 현재 URL: {page.url}")

            # GNB 영역 확인
            print("🔍 GNB 영역 확인...")
            gnb = page.locator('header').first
            await gnb.wait_for(state='visible', timeout=10000)
            assert await gnb.is_visible(), "GNB 영역이 보이지 않습니다"
            print("✅ GNB 영역 확인 완료")

            # 로그인 후 상태 스크린샷
            await page.screenshot(path='screenshots/test_4_after_login.png')

            # header 내 모든 링크 디버깅
            all_links = await page.locator('header a').all()
            print(f"🔍 Header 링크 수: {len(all_links)}")
            for lnk in all_links[:20]:
                href = await lnk.get_attribute('href')
                txt = await lnk.text_content()
                print(f"  link: href={href}, text={txt.strip()[:40] if txt else ''}")

            # header 내 모든 버튼 디버깅
            all_btns = await page.locator('header button').all()
            print(f"🔍 Header 버튼 수: {len(all_btns)}")
            for btn in all_btns[:10]:
                txt = await btn.text_content()
                cls = await btn.get_attribute('class')
                print(f"  button: class={cls}, text={txt.strip()[:40] if txt else ''}")

            # 프로필 아이콘 클릭
            print("🔍 프로필 아이콘 선택...")
            profile_clicked = False

            # 1. header 내 프로필/유저 관련 링크
            for selector in [
                'header a[href*="/my"]',
                'header a[href*="/profile"]',
                'header a[href*="/users"]',
                '[class*="gnb"] a[href*="/my"]',
                'nav a[href*="/my"]',
            ]:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    try:
                        await elem.click(timeout=5000)
                        profile_clicked = True
                        print(f"✅ 클릭: {selector}")
                        break
                    except Exception as ce:
                        print(f"  클릭 실패 ({selector}): {ce}")

            if not profile_clicked:
                # 2. 프로필 이미지(원형 아바타) 버튼
                for selector in [
                    'button[class*="avatar"]',
                    'button[class*="profile"]',
                    'button[class*="user"]',
                    '[class*="UserProfile"]',
                    '[class*="userProfile"]',
                    'header button:has(img)',
                ]:
                    elem = page.locator(selector).first
                    if await elem.count() > 0:
                        try:
                            await elem.click(timeout=5000)
                            profile_clicked = True
                            print(f"✅ 클릭: {selector}")
                            break
                        except Exception as ce:
                            print(f"  클릭 실패 ({selector}): {ce}")

            if not profile_clicked:
                raise Exception("프로필 아이콘을 찾을 수 없습니다")

            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshots/test_4_after_profile_click.png')

            # 프로필 페이지 진입 확인
            current_url = page.url
            print(f"📍 프로필 클릭 후 URL: {current_url}")

            # 드롭다운 메뉴가 열린 경우 프로필 링크 클릭
            for link_name in ['프로필', 'My Profile', '내 프로필']:
                profile_menu_link = page.get_by_role('link', name=link_name)
                if await profile_menu_link.count() > 0:
                    try:
                        await profile_menu_link.first.click(timeout=5000)
                        await page.wait_for_timeout(2000)
                        current_url = page.url
                        print(f"📍 드롭다운 '{link_name}' 클릭 후 URL: {current_url}")
                        break
                    except Exception as ce:
                        print(f"  드롭다운 클릭 실패: {ce}")

            # 최종 URL에서 프로필 페이지 확인
            assert '/profile' in current_url or '/users' in current_url or '/my' in current_url, \
                f"프로필 페이지로 이동하지 않음. 현재 URL: {current_url}"
            print("✅ 프로필 페이지 진입 확인 완료")

            await page.screenshot(path='screenshots/test_4_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_4_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
