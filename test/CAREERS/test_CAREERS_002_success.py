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

            # 탐색 페이지 진입 (로그인 상태)
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # '적극 채용 중인 회사' 섹션 확인
            actively_hiring_section = page.get_by_text('적극 채용 중인 회사', exact=False)
            await actively_hiring_section.first.wait_for(state='visible', timeout=10000)

            # 섹션이 존재하는지 확인
            section_count = await actively_hiring_section.count()
            assert section_count > 0, "'적극 채용 중인 회사' 항목이 노출되지 않음"

            # '적극 채용 중인 회사' 섹션 내 회사 카드 5개 확인
            # 섹션 컨테이너를 찾아서 그 안의 카드 개수 확인
            # 다양한 방법으로 카드 수를 확인
            card_count = await page.evaluate("""() => {
                // 텍스트로 섹션 헤더를 찾고 부모 섹션을 탐색
                const allElements = document.querySelectorAll('*');
                let sectionContainer = null;

                for (const el of allElements) {
                    if (el.textContent && el.textContent.trim() === '적극 채용 중인 회사') {
                        // 부모 컨테이너 탐색
                        let parent = el.parentElement;
                        for (let i = 0; i < 5; i++) {
                            if (parent) {
                                parent = parent.parentElement;
                            }
                        }
                        if (parent) {
                            sectionContainer = parent;
                        }
                        break;
                    }
                }

                if (!sectionContainer) return -1;

                // 섹션 내 링크(회사 카드) 수 확인
                const cards = sectionContainer.querySelectorAll('a');
                return cards.length;
            }""")

            # 카드가 없으면 다른 방법으로 확인
            if card_count <= 0:
                # 리스트 최상단 영역에서 회사 관련 링크 확인
                card_count = await page.evaluate("""() => {
                    const headings = [...document.querySelectorAll('h2, h3, h4, strong, b, span')];
                    let targetHeading = null;
                    for (const h of headings) {
                        if (h.textContent && h.textContent.trim().includes('적극 채용 중인 회사')) {
                            targetHeading = h;
                            break;
                        }
                    }
                    if (!targetHeading) return -2;

                    // 섹션 전체 컨테이너 탐색 (최대 10단계 상위)
                    let container = targetHeading;
                    for (let i = 0; i < 10; i++) {
                        const parent = container.parentElement;
                        if (!parent) break;
                        // 카드가 5개 이상인 컨테이너를 찾음
                        const links = parent.querySelectorAll('a');
                        if (links.length >= 5) {
                            container = parent;
                            break;
                        }
                        container = parent;
                    }

                    const links = container.querySelectorAll('a');
                    return links.length;
                }""")

            print(f"'적극 채용 중인 회사' 섹션 내 회사 카드 수: {card_count}")
            assert card_count == 5, f"회사 카드가 5개 노출되어야 하지만 {card_count}개 노출됨"

            await page.screenshot(path='screenshots/test_40_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_40_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
