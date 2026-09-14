import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

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

            # 2. GNB 검색 버튼 클릭 (aria-label='검색')
            search_btn = page.get_by_role('button', name='검색')
            await search_btn.wait_for(state='visible', timeout=10000)
            await search_btn.click()
            await page.wait_for_timeout(1500)

            # 3. 검색어 입력 텍스트박스 노출 확인
            # 실제 DOM에서는 input[type="search"] 로 구현됨
            search_input = page.locator('input[type="search"]')
            await search_input.wait_for(state='visible', timeout=10000)
            assert await search_input.is_visible(), "검색어 입력 텍스트박스가 노출되지 않음"
            print("✅ 검색어 입력 텍스트박스 노출 확인")

            # 4. 인기 검색어 섹션 노출 확인
            popular_section = page.locator('text=인기 검색어').first
            await popular_section.wait_for(state='visible', timeout=5000)
            assert await popular_section.is_visible(), "인기 검색어 섹션이 노출되지 않음"
            print("✅ 인기 검색어 섹션 노출 확인")

            # 5. 인기 검색어 1위~8위 버튼 노출 확인
            # 실제 DOM: 검색입력창 근처 컨테이너에 <li> + <a role="link"> 구조
            popular_items = await page.evaluate("""() => {
                const input = document.querySelector('input[type="search"]');
                if (!input) return [];

                // 입력창에서 4~6단계 상위 컨테이너에서 링크 탐색
                let container = input.parentElement;
                for (let i = 0; i < 8; i++) {
                    if (!container) break;
                    const links = [...container.querySelectorAll('a[role="link"]')];
                    if (links.length >= 8) {
                        return links.slice(0, 10).map(a => ({
                            text: a.innerText.trim(),
                            visible: a.offsetParent !== null
                        }));
                    }
                    container = container.parentElement;
                }
                return [];
            }""")

            print(f"인기 검색어 항목들: {popular_items}")
            visible_items = [item for item in popular_items if item['visible']]
            print(f"노출된 인기 검색어 개수: {len(visible_items)}")
            assert len(visible_items) >= 8, f"인기 검색어 항목이 8개 미만 노출됨: {len(visible_items)}개"

            # 1위~8위 순위 번호 포함 여부 확인
            ranks_found = []
            for item in visible_items[:8]:
                for rank in range(1, 9):
                    if str(rank) in item['text'].split('\n')[0]:
                        ranks_found.append(rank)
                        break

            print(f"확인된 순위: {sorted(set(ranks_found))}")
            assert len(set(ranks_found)) >= 8, f"1~8위 순위 항목이 모두 노출되지 않음. 확인된 순위: {sorted(set(ranks_found))}"
            print("✅ 인기 검색어 1위~8위 버튼(링크) 노출 확인")

            await page.screenshot(path='screenshots/test_SEARCH_001_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_SEARCH_001_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
