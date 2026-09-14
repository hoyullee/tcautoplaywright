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

            # 채용 홈 접속 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 1. '출퇴근 편한 포지션' 섹션 찾기 (스크롤하며 탐색)
            # 테스트케이스의 '출퇴근 걱정없는 역세권 포지션'에 해당하는 실제 섹션명
            section_found = False
            for _ in range(30):
                # 실제 페이지의 섹션명으로 확인
                section = page.get_by_text('출퇴근 편한 포지션', exact=True)
                if await section.count() > 0:
                    section_found = True
                    await section.first.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    break
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(200)

            if not section_found:
                # fallback: 역세권 관련 텍스트 탐색
                for _ in range(10):
                    section = page.get_by_text('역세권', exact=False)
                    if await section.count() > 0:
                        section_found = True
                        await section.first.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        break
                    await page.evaluate("window.scrollBy(0, 400)")
                    await page.wait_for_timeout(200)

            if not section_found:
                raise Exception("'출퇴근 편한 포지션'(역세권 포지션) 섹션을 찾을 수 없습니다.")
            print("[OK] '출퇴근 편한 포지션' 섹션 확인")

            # 2. '지도로 공고 찾기' 버튼/링크 찾기
            map_btn = page.get_by_role('link', name='지도로 공고 찾기')
            if await map_btn.count() == 0:
                map_btn = page.get_by_role('button', name='지도로 공고 찾기')
            if await map_btn.count() == 0:
                map_btn = page.get_by_text('지도로 공고 찾기', exact=True)

            if await map_btn.count() == 0:
                raise Exception("'지도로 공고 찾기' 버튼을 찾을 수 없습니다.")

            await map_btn.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            print("[OK] '지도로 공고 찾기' 버튼 확인")

            # 3. 클릭 - 새 탭 또는 같은 탭 이동 처리
            pages_before = len(context.pages)
            await map_btn.first.click()
            await page.wait_for_timeout(2000)

            pages_after = context.pages
            if len(pages_after) > pages_before:
                # 새 탭에서 열림
                target_page = pages_after[-1]
                await target_page.wait_for_load_state('domcontentloaded', timeout=30000)
                for _ in range(10):
                    current_url = target_page.url
                    if current_url and current_url != 'about:blank':
                        break
                    await target_page.wait_for_timeout(500)
                print(f"[NEW TAB] Navigated to: {current_url}")
            else:
                # 같은 탭에서 이동
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                current_url = page.url
                target_page = page
                print(f"[SAME TAB] Navigated to: {current_url}")

            # 4. 포지션맵 페이지 이동 확인
            print(f"Final URL: {current_url}")
            if 'position-map' not in current_url:
                raise Exception(f"'포지션맵' 페이지로 이동되지 않았습니다. URL: {current_url}")
            print("[OK] '포지션맵' 페이지로 이동 확인")

            await target_page.screenshot(path='screenshots/test_CAREERSHOME_011_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_011_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
