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

            # GNB에서 채용 항목 클릭 (href 절대 URL 매칭)
            print("🔍 GNB 채용 항목 탐색 중...")
            gnb_link = page.locator('a[href="https://www.wanted.co.kr/wdlist"]').first
            await gnb_link.wait_for(timeout=15000)
            await gnb_link.click()
            await page.wait_for_url('**/wdlist**', timeout=20000)
            print(f"✅ 클릭 후 URL: {page.url}")

            # 탐색 페이지 진입 확인
            assert 'wdlist' in page.url, f"탐색 페이지(wdlist)로 이동되지 않음. 현재 URL: {page.url}"
            print(f"✅ 탐색 페이지 진입 확인: {page.url}")

            await page.screenshot(path='screenshots/test_17_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_17_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
