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

            # 탐색 페이지 진입
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # '적극 채용 중인 회사' 섹션 확인
            actively_hiring_section = page.get_by_text('적극 채용 중인 회사')
            await actively_hiring_section.wait_for(state='visible', timeout=10000)

            # '적극 채용 중인 회사' 섹션으로 스크롤
            await actively_hiring_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # 포지션 카드 노출 확인 (초기 로드)
            # 포지션 카드는 일반적으로 a 태그나 특정 역할을 가진 요소로 구성됨
            position_cards = page.locator('[class*="JobCard"]')
            initial_count = await position_cards.count()

            # 포지션 카드가 없을 경우 다른 셀렉터 시도
            if initial_count == 0:
                position_cards = page.locator('[class*="job-card"], [class*="Card_container"], article')
                initial_count = await position_cards.count()

            assert initial_count > 0, f"초기 포지션 카드가 노출되지 않음 (count: {initial_count})"
            print(f"초기 포지션 카드 수: {initial_count}")

            # 페이지 하단으로 스크롤하여 추가 포지션 카드 로드 확인
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # 추가 스크롤로 무한 스크롤 트리거
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # 스크롤 후 포지션 카드 수 확인
            after_scroll_count = await position_cards.count()
            print(f"스크롤 후 포지션 카드 수: {after_scroll_count}")

            # 스크롤 후 카드 수가 초기보다 많거나 같아야 함 (추가 로드 확인)
            assert after_scroll_count >= initial_count, \
                f"스크롤 후 포지션 카드 수({after_scroll_count})가 초기({initial_count})보다 적음"

            # 추가 포지션 카드 로드 확인 (스크롤로 인해 더 많은 카드가 노출되어야 함)
            assert after_scroll_count > initial_count, \
                f"스크롤 후 추가 포지션 카드가 로드되지 않음 (초기: {initial_count}, 스크롤 후: {after_scroll_count})"

            print(f"추가 포지션 카드 확인: {initial_count} → {after_scroll_count}")

            await page.screenshot(path='screenshots/test_41_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_41_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
