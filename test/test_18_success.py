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

            # GNB에서 이력서 항목 클릭 (비로그인 시 cv/list → cv/intro 리다이렉트)
            print("🔍 GNB 이력서 항목 탐색 중...")
            resume_link = page.locator('a[href="https://www.wanted.co.kr/cv/list"]').first
            await resume_link.wait_for(timeout=15000)
            async with page.expect_navigation(timeout=20000):
                await resume_link.click()
            print(f"✅ 클릭 후 URL: {page.url}")

            # 비로그인 상태이므로 cv/intro로 리다이렉트 확인
            assert 'cv/intro' in page.url, f"이력서 페이지(cv/intro)로 이동되지 않음. 현재 URL: {page.url}"
            print(f"✅ 이력서 페이지 진입 확인: {page.url}")

            await page.screenshot(path='screenshots/test_18_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_18_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
