import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups
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
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 탐색 페이지 진입 (로그인 상태) - '적극 채용 중인 회사' 배너가 노출되는 개발 카테고리로 진입
            await page.goto('https://www.wanted.co.kr/wdlist/518', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await dismiss_optional_popups(page)  # 검증 대상이 아닌 팝업 정리
            await page.wait_for_timeout(2000)

            # '적극 채용 중인 회사' 섹션 확인 및 스크롤
            actively_hiring_section = page.get_by_text('적극 채용 중인 회사', exact=False).first
            await actively_hiring_section.wait_for(state='visible', timeout=15000)
            await actively_hiring_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # 포지션 상세 페이지로 이동하는 링크(/wd/{id})를 포지션 카드로 간주
            position_links = page.locator('a[href*="/wd/"]')
            initial_count = await position_links.count()
            assert initial_count > 0, f"'적극 채용 중인 회사' 하단 포지션 카드가 노출되지 않음 (count: {initial_count})"
            print(f"초기 포지션 카드 수: {initial_count}")

            # 하단으로 스크롤하여 추가 포지션 카드 로드 유도
            for _ in range(4):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

            after_scroll_count = await position_links.count()
            print(f"스크롤 후 포지션 카드 수: {after_scroll_count}")

            assert after_scroll_count > initial_count, \
                f"스크롤 후 추가 포지션 카드가 로드되지 않음 (초기: {initial_count}, 스크롤 후: {after_scroll_count})"

            await page.screenshot(path='screenshots/test_CAREERS_003_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERS_003_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
