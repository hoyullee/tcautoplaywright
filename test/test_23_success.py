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

            # GNB에서 프리랜서 링크 찾기 (gigs/experts 링크)
            print("🔍 GNB 프리랜서 항목 탐색 중...")
            freelancer_link = page.locator('a[href*="gigs/experts"]').first
            await freelancer_link.wait_for(timeout=15000)
            print("✅ 프리랜서 링크 발견")

            href = await freelancer_link.get_attribute('href')
            target_attr = await freelancer_link.get_attribute('target')
            print(f"📌 href: {href}, target: {target_attr}")

            # 새 탭 이벤트를 먼저 대기하면서 클릭 (프리랜서는 새 탭으로 열림)
            try:
                print("🆕 새 탭 감지 시도...")
                async with context.expect_page(timeout=8000) as new_page_info:
                    await freelancer_link.click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded', timeout=30000)
                current_url = new_page.url
                screenshot_page = new_page
                print(f"✅ 새 탭으로 열림")
            except Exception:
                # 새 탭이 안 열린 경우 현재 탭에서 URL 변경 확인
                print("➡️ 새 탭 없음 - 현재 탭에서 URL 확인")
                await page.wait_for_url('*gigs/experts*', timeout=20000)
                current_url = page.url
                screenshot_page = page

            print(f"📍 현재 URL: {current_url}")

            assert 'gigs/experts' in current_url, \
                f"프리랜서 페이지로 이동하지 않았습니다. 현재 URL: {current_url}"
            print("✅ 프리랜서 페이지 진입 확인")

            await screenshot_page.screenshot(path='screenshots/test_23_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_23_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
