from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')

        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            print("✅ 페이지 로드 완료")

            # GNB에서 교육•이벤트 링크 클릭 (같은 탭에서 이동)
            print("🔍 GNB 교육•이벤트 항목 탐색 중...")
            selector = 'a[href*="event.wanted.co.kr"]'
            edu_link = page.locator(selector).first
            await edu_link.wait_for(timeout=15000)

            await edu_link.click()
            print("✅ 교육•이벤트 클릭")
            await page.wait_for_url('*event.wanted.co.kr*', timeout=20000)

            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            assert 'event.wanted.co.kr' in current_url, f"교육•이벤트 페이지 진입 실패. 현재 URL: {current_url}"
            print("✅ 교육•이벤트 페이지 진입 확인")

            await page.screenshot(path='screenshots/test_20_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_20_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
