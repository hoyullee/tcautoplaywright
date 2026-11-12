import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups, poll_until

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

            # 이력서 목록 페이지 진입
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            assert 'cv/list' in page.url, f"이력서 목록 페이지 진입 실패: {page.url}"

            # 최상위 이력서 카드만 선택 (:has로 하위 요소 제외)
            # 기본 이력서는 항상 index 0이므로 index 1(두 번째 카드)이 첫 번째 비기본 이력서
            all_cards = page.locator('[class*="ResumeItem_ResumeItem"]:has([class*="__title__"])')
            total = await all_cards.count()

            # 비기본 이력서(index 1 이상)가 없으면 새 이력서 생성
            if total < 2:
                for kw in ['새 이력서 작성', '새 이력서']:
                    btn = page.get_by_text(kw, exact=False)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        await page.goto('https://www.wanted.co.kr/cv/list', timeout=30000)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        break
                total = await all_cards.count()

            assert total >= 2, "기본 이력서 외 이력서 카드가 없습니다"

            # index 0 = 기본 이력서, index 1 = 첫 번째 비기본 이력서
            await all_cards.nth(1).click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            assert '/cv/' in page.url and 'cv/list' not in page.url, f"이력서 편집 페이지 진입 실패: {page.url}"

            await dismiss_optional_popups(page)

            # 스킬 섹션 (이력서 언어에 따라 '스킬' 또는 'Skills')
            skill_header = page.locator('[data-header-label="스킬"], [data-header-label="Skills"]').first
            await skill_header.wait_for(state='attached', timeout=15000)
            await skill_header.scroll_into_view_if_needed()

            skill_input = page.get_by_placeholder('보유 스킬을 검색해 보세요.')

            async def activate_input():
                await page.evaluate("""() => {
                    const h = document.querySelector('[data-header-label="스킬"], [data-header-label="Skills"]');
                    if (h && h.nextElementSibling) h.nextElementSibling.click();
                }""")
                return await skill_input.count() > 0

            assert await poll_until(activate_input, timeout=10000, interval=500), "스킬 검색 input을 찾을 수 없습니다"

            await skill_input.first.scroll_into_view_if_needed()
            await skill_input.first.click()
            await skill_input.first.fill('playwright')

            option = page.get_by_text('Playwright', exact=True)
            await option.first.wait_for(state='visible', timeout=10000)
            await option.first.click()

            # 등록 확인: 스킬 영역에 'Playwright' 칩이 노출되고 입력창 값은 비워짐
            async def check_registered():
                text = await page.evaluate("""() => {
                    const h = document.querySelector('[data-header-label="스킬"], [data-header-label="Skills"]');
                    const box = h && h.nextElementSibling;
                    return box ? box.textContent : '';
                }""")
                return 'playwright' in text.lower()

            assert await poll_until(check_registered, timeout=8000, interval=300), "스킬에 'Playwright'가 등록되지 않았습니다"

            await page.screenshot(path='screenshots/test_RESUME_008_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_RESUME_008_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
