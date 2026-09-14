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

            # 채용 홈 진입
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # GNB 영역에서 프로필 아이콘 찾기
            profile_icon = None

            # 방법 1: aria-label로 프로필 버튼 찾기
            for selector in [
                '[aria-label="내 프로필"]',
                '[aria-label="프로필"]',
                '[aria-label="마이페이지"]',
                'button[class*="profile"]',
                '[class*="UserAvatar"]',
                '[class*="userAvatar"]',
            ]:
                try:
                    el = page.locator(selector).first
                    if await el.is_visible():
                        profile_icon = el
                        break
                except:
                    pass

            # 방법 2: GNB 내 버튼들 중 프로필 관련 요소 탐색
            if not profile_icon:
                gnb_btns = await page.locator('header button, nav button').all()
                for btn in gnb_btns:
                    try:
                        label = await btn.get_attribute('aria-label') or ''
                        class_name = await btn.get_attribute('class') or ''
                        if any(k in label.lower() for k in ['프로필', 'profile', 'mypage', '마이']) or \
                           any(k in class_name.lower() for k in ['profile', 'avatar', 'user']):
                            if await btn.is_visible():
                                profile_icon = btn
                                break
                    except:
                        pass

            # 방법 3: 헤더 내 이미지 아바타 요소
            if not profile_icon:
                for sel in [
                    'header img[alt*="profile"]',
                    'header img[alt*="프로필"]',
                    'header [class*="Avatar"]',
                    'header [class*="avatar"]',
                    'nav [class*="avatar"]',
                ]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            profile_icon = el
                            break
                    except:
                        pass

            # 방법 4: JS로 헤더 내 프로필 링크 탐색
            if not profile_icon:
                profile_href = await page.evaluate("""() => {
                    const links = [...document.querySelectorAll('header a, nav a')];
                    const profileLink = links.find(a =>
                        a.href && (a.href.includes('/profile') || a.href.includes('/users/'))
                    );
                    return profileLink ? profileLink.getAttribute('href') : null;
                }""")
                if profile_href:
                    profile_icon = page.locator(f'a[href="{profile_href}"]').first

            assert profile_icon is not None, "프로필 아이콘을 GNB에서 찾을 수 없습니다"

            # 프로필 아이콘 클릭 (오버레이 등으로 가려진 경우 force=True로 우회)
            await profile_icon.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            try:
                await profile_icon.click(timeout=10000)
            except Exception:
                await profile_icon.click(force=True)
            await page.wait_for_timeout(2000)

            current_url = page.url
            print(f"클릭 후 URL: {current_url}")

            profile_page_entered = False

            # 직접 프로필 페이지로 이동했는지 확인
            if '/profile' in current_url or '/users/' in current_url or '/mypage' in current_url:
                profile_page_entered = True
                print(f"프로필 페이지로 직접 이동: {current_url}")
            else:
                # 드롭다운이 열렸다면 프로필 링크 찾아서 클릭
                for sel in [
                    'a[href*="/profile"]',
                    'a[href*="/users/"]',
                    '[role="menu"] a',
                    '[class*="dropdown"] a',
                ]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            href = await el.get_attribute('href') or ''
                            print(f"드롭다운에서 링크 발견: {href}")
                            if '/profile' in href or '/users/' in href or '/mypage' in href:
                                await el.click()
                                await page.wait_for_load_state('domcontentloaded')
                                current_url = page.url
                                if '/profile' in current_url or '/users/' in current_url or '/mypage' in current_url:
                                    profile_page_entered = True
                                    print(f"프로필 페이지로 이동: {current_url}")
                                break
                    except:
                        pass

            assert profile_page_entered, f"프로필 페이지 진입 실패. 현재 URL: {current_url}"

            await page.screenshot(path='screenshots/test_LOGIN_004_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_LOGIN_004_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
