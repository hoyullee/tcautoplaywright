import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.async_api import async_playwright
import asyncio
import os
import pytest
from ui_helpers import dismiss_optional_popups

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

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

            # 사전조건: 로그인 상태로 채용 홈 진입
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await dismiss_optional_popups(page)  # 검증 대상이 아닌 팝업 정리

            # 확인사항 1: GNB 영역 - 프로필 아이콘 노출 확인
            profile_icon = page.get_by_role('link', name='MY 원티드')
            await profile_icon.wait_for(state='visible', timeout=10000)

            # 확인사항 2: 프로필 아이콘 선택
            await profile_icon.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1000)

            # 기대결과: 프로필 페이지 진입 확인
            assert 'social.wanted.co.kr/my/profile' in page.url, \
                f"프로필 페이지로 진입하지 못함, 현재 URL: {page.url}"

            profile_menu = page.get_by_role('listitem', name='프로필')
            await profile_menu.wait_for(state='visible', timeout=10000)

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
