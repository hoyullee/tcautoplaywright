import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = ""
TEST_PASSWORD = ""

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

            # 채용 홈 접속 (비로그인 상태)
            print("🌐 채용 홈 접속 중...")
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            print("✅ 채용 홈 로드 완료")

            # GNB에서 콘텐츠 링크 찾기
            print("🔍 GNB 콘텐츠 항목 탐색 중...")
            contents_link = page.locator('a[href*="wanted.co.kr/events"]').first
            await contents_link.wait_for(timeout=15000)

            await contents_link.click()
            print("✅ 콘텐츠 클릭")
            await page.wait_for_url('*wanted.co.kr/events*', timeout=20000)

            # 콘텐츠 페이지 URL 확인
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            assert 'wanted.co.kr/events' in current_url, \
                f"콘텐츠 페이지로 이동하지 않았습니다. 현재 URL: {current_url}"
            print("✅ 콘텐츠 페이지 진입 확인")

            await page.screenshot(path='screenshots/test_21_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_21_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
