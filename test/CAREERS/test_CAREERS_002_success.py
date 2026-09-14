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
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 탐색 페이지 진입 (로그인 상태) - '적극 채용 중인 회사' 배너가 노출되는 개발 카테고리로 진입
            await page.goto('https://www.wanted.co.kr/wdlist/518', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # 희망 근무지 설정 모달이 뜨는 경우 닫기
            close_btn = page.get_by_text('나중에 하기')
            if await close_btn.count() > 0:
                await close_btn.first.click()
                await page.wait_for_timeout(1000)

            # '적극 채용 중인 회사' 섹션(리스트 영역 상단) 노출 확인
            actively_hiring_section = page.get_by_text('적극 채용 중인 회사', exact=False)
            await actively_hiring_section.first.wait_for(state='visible', timeout=10000)
            section_count = await actively_hiring_section.count()
            assert section_count > 0, "'적극 채용 중인 회사' 항목이 노출되지 않음"

            # 섹션 내 회사 카드 개수 확인 (가장 가까운 section 조상 요소 기준)
            card_count = await page.evaluate("""() => {
                const all = [...document.querySelectorAll('*')];
                let headingEl = null;
                for (const el of all) {
                    if (el.children.length === 0 && el.textContent && el.textContent.includes('적극 채용 중인 회사')) {
                        headingEl = el;
                        break;
                    }
                }
                if (!headingEl) return -1;

                let container = headingEl.closest('section');
                if (!container) {
                    container = headingEl;
                    for (let i = 0; i < 8; i++) {
                        if (!container.parentElement) break;
                        container = container.parentElement;
                    }
                }
                return container.querySelectorAll('a').length;
            }""")

            print(f"'적극 채용 중인 회사' 섹션 내 회사 카드 수: {card_count}")
            assert card_count == 5, f"회사 카드가 5개 노출되어야 하지만 {card_count}개 노출됨"

            await page.screenshot(path='screenshots/test_CAREERS_002_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERS_002_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
