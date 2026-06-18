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
            storage_state='work/auth_state.json',
            viewport={'width': 1280, 'height': 900}
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈으로 이동
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # '출퇴근 걱정없는 역세권 포지션' 섹션 찾기 및 스크롤
            section = page.get_by_text('출퇴근 걱정없는 역세권 포지션').first
            await section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # '지도로 공고 찾기' 버튼/링크 정보 확인
            btn_info = await page.evaluate("""() => {
                const elems = [...document.querySelectorAll('a, button')];
                const result = [];
                for (const el of elems) {
                    const text = el.textContent.trim();
                    if (text.includes('지도로 공고 찾기')) {
                        result.push({
                            tag: el.tagName,
                            text: text.slice(0, 50),
                            href: el.getAttribute('href') || '',
                            target: el.getAttribute('target') || '',
                            ariaLabel: el.getAttribute('aria-label') || ''
                        });
                    }
                }
                return result;
            }""")
            print(f"지도로 공고 찾기 버튼 정보: {btn_info}")

            # '지도로 공고 찾기' 링크 찾기
            map_btn = page.get_by_role('link', name='지도로 공고 찾기').first
            if await map_btn.count() == 0:
                map_btn = page.get_by_text('지도로 공고 찾기').first
            if await map_btn.count() == 0:
                map_btn = page.locator('a, button').filter(has_text='지도로 공고 찾기').first

            await map_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 링크의 href 확인
            href = await map_btn.get_attribute('href')
            target = await map_btn.get_attribute('target')
            print(f"버튼 href: {href}, target: {target}")

            # 새 탭 여부 확인 후 클릭 처리
            if target == '_blank':
                # 새 탭으로 열리는 경우
                async with context.expect_page() as new_page_info:
                    await map_btn.click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded')
                current_url = new_page.url
                print(f"새 탭 URL: {current_url}")
                assert 'position-map' in current_url, f"포지션맵 페이지로 이동되지 않음. 현재 URL: {current_url}"
                await new_page.screenshot(path='screenshots/test_23_success.png')
            else:
                # 같은 탭에서 열리는 경우
                await map_btn.click()
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)
                current_url = page.url
                print(f"현재 URL: {current_url}")
                assert 'position-map' in current_url, f"포지션맵 페이지로 이동되지 않음. 현재 URL: {current_url}"
                await page.screenshot(path='screenshots/test_23_success.png')

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_23_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
