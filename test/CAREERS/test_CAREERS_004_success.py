import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"

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

            # 포지션 리스트 영역 확인 - 포지션 카드들이 로드될 때까지 대기
            # 포지션 카드는 보통 a 태그로 /wd/{id} 링크를 가짐
            await page.wait_for_selector('a[href^="/wd/"]', timeout=15000)

            # 포지션 카드 목록 가져오기
            position_cards = page.locator('a[href^="/wd/"]')
            card_count = await position_cards.count()
            assert card_count > 0, "포지션 카드가 존재하지 않습니다."

            # 첫 번째 포지션 카드 클릭
            first_card = position_cards.first
            href = await first_card.get_attribute('href')
            print(f"선택된 포지션 링크: {href}")

            await first_card.click()
            await page.wait_for_load_state('domcontentloaded')

            # 포지션 상세 페이지 진입 확인
            current_url = page.url
            print(f"현재 URL: {current_url}")

            assert '/wd/' in current_url, f"포지션 상세 페이지로 이동하지 않았습니다. 현재 URL: {current_url}"

            await page.screenshot(path='screenshots/test_42_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_42_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
