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

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1500)

            # 인앱 메시지(브레이즈) 팝업이 뜨는 경우 화면을 가려 클릭이 막히므로 닫기 처리
            if await page.locator('iframe.ab-in-app-message').count() > 0:
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(500)

            # '한 번쯤 가보고 싶은 회사' 섹션 찾기
            section_title = page.get_by_text('한 번쯤 가보고 싶은 회사')
            await section_title.wait_for(state='visible', timeout=15000)

            # 섹션으로 스크롤
            await section_title.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 섹션 내의 '전체보기' 링크 href 탐색 (evaluate 사용)
            view_all_href = await page.evaluate("""() => {
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    if (el.childNodes && [...el.childNodes].some(n =>
                        n.nodeType === Node.TEXT_NODE &&
                        n.textContent.includes('한 번쯤 가보고 싶은 회사')
                    )) {
                        let parent = el;
                        for (let i = 0; i < 10; i++) {
                            parent = parent.parentElement;
                            if (!parent) break;
                            const allLinks = parent.querySelectorAll('a');
                            for (const link of allLinks) {
                                if (link.textContent.trim().includes('전체보기')) {
                                    return link.href;
                                }
                            }
                        }
                        break;
                    }
                }
                return null;
            }""")

            print(f"Found view_all_href: {view_all_href}")

            view_all_btn = None

            if view_all_href:
                path_part = view_all_href.split("wanted.co.kr")[-1]
                view_all_btn = page.locator(f'a[href*="{path_part}"]').first
            else:
                # 전체보기 버튼을 텍스트로 찾되 섹션 근처에서
                view_all_buttons = page.get_by_role('link', name='전체보기')
                count = await view_all_buttons.count()
                print(f"Found {count} '전체보기' link buttons")

                if count == 0:
                    view_all_buttons = page.get_by_role('button', name='전체보기')
                    count = await view_all_buttons.count()
                    print(f"Found {count} '전체보기' role=button buttons")

                section_box = await section_title.bounding_box()
                print(f"Section title box: {section_box}")

                best_btn = None
                min_distance = float('inf')

                for i in range(count):
                    btn = view_all_buttons.nth(i)
                    box = await btn.bounding_box()
                    if box and section_box:
                        distance = abs(box['y'] - section_box['y'])
                        print(f"Button {i} box: {box}, distance: {distance}")
                        if distance < min_distance:
                            min_distance = distance
                            best_btn = btn

                view_all_btn = best_btn

            if view_all_btn is None:
                raise Exception("'전체보기' 버튼을 찾을 수 없습니다")

            # 전체보기 버튼이 보이도록 스크롤
            await view_all_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 전체보기 버튼 클릭
            await view_all_btn.click()
            await page.wait_for_load_state('domcontentloaded', timeout=15000)

            # 이동된 URL 확인
            new_url = page.url
            print(f"Navigated to: {new_url}")

            # 기대 URL 패턴 확인: https://www.wanted.co.kr/tags/14?view=company&tag_id=10675
            expected_url_pattern = 'wanted.co.kr/tags'
            if expected_url_pattern not in new_url:
                raise Exception(f"Expected URL containing '{expected_url_pattern}', but got: {new_url}")

            print(f"Successfully navigated to '한 번쯤 가보고 싶은 회사' page: {new_url}")

            await page.screenshot(path='screenshots/test_17_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_17_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
