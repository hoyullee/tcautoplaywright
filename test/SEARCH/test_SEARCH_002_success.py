import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups

from playwright.async_api import async_playwright
import asyncio
import os
import pytest

SEARCH_KEYWORD = "개발자"


@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1. 채용 홈 진입 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await dismiss_optional_popups(page)

            # 2. GNB 검색 버튼 클릭 -> 검색 화면 전환 상태 (사전조건)
            search_btn = page.get_by_role('button', name='검색')
            await search_btn.wait_for(state='visible', timeout=10000)
            await search_btn.click()
            await page.wait_for_timeout(1000)

            # 3. 검색어 입력 항목(텍스트 박스) 확인 후 임의의 텍스트 입력
            search_input = page.locator('input[type="search"]')
            await search_input.wait_for(state='visible', timeout=10000)
            await search_input.fill(SEARCH_KEYWORD)
            await page.wait_for_timeout(300)
            input_value = await search_input.input_value()
            assert input_value == SEARCH_KEYWORD, f"검색어 입력값이 일치하지 않음: {input_value}"

            # 4. 검색 실행 (Enter)
            await search_input.press('Enter')
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 5. 검색 결과 페이지 랜딩 확인
            assert '/search' in page.url, f"검색 결과 페이지로 랜딩되지 않음: {page.url}"

            # 6. 검색어 입력 항목에 입력한 검색어가 노출되는지 확인
            keyword_display = page.get_by_text(SEARCH_KEYWORD, exact=True).first
            await keyword_display.wait_for(state='visible', timeout=10000)
            assert await keyword_display.is_visible(), "검색 결과 페이지에 입력 검색어가 노출되지 않음"

            # 7. 탭 메뉴(전체/포지션/회사/콘텐츠/소셜/프로필) 노출 확인
            tab_names = ['전체', '포지션', '회사', '콘텐츠', '소셜', '프로필']
            for tab_name in tab_names:
                tab = page.locator('[role="tab"]', has_text=tab_name).first
                await tab.wait_for(state='visible', timeout=5000)
                assert await tab.is_visible(), f"탭 메뉴 '{tab_name}' 이 노출되지 않음"

            # 8. 각 항목(포지션/회사/콘텐츠/소셜/프로필) 리스트 노출 확인
            # 각 섹션은 <h2> 제목 뒤에 카드(anchor) 목록이 뒤따르는 구조
            section_names = ['포지션', '회사', '콘텐츠', '소셜', '프로필']
            list_counts = await page.evaluate("""(names) => {
                const results = {};
                for (const name of names) {
                    const heading = [...document.querySelectorAll('h2')]
                        .find(h => h.innerText.startsWith(name));
                    if (!heading) { results[name] = -1; continue; }
                    let container = heading.parentElement;
                    let count = 0;
                    for (let i = 0; i < 5 && container; i++) {
                        const links = container.querySelectorAll('a');
                        if (links.length > 1) { count = links.length; break; }
                        container = container.parentElement;
                    }
                    results[name] = count;
                }
                return results;
            }""", section_names)

            print(f"섹션별 리스트 항목 수: {list_counts}")
            for name in section_names:
                assert list_counts.get(name, -1) > 0, f"'{name}' 항목 리스트가 노출되지 않음"

            await page.screenshot(path='screenshots/test_SEARCH_002_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_SEARCH_002_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
