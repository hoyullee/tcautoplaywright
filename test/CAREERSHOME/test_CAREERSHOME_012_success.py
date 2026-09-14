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

            # '합격 가능성 높은 포지션' 섹션 찾기
            section_header = page.get_by_text('합격 가능성 높은 포지션', exact=False)
            await section_header.first.wait_for(state='visible', timeout=15000)

            # 섹션 헤더로 스크롤
            await section_header.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # '합격 가능성 높은 포지션' 섹션 내의 '전체보기' 버튼 찾기
            # 먼저 matched URL로 연결되는 링크 탐색
            view_all_link = page.locator('a[href*="matched"]').filter(has_text='전체보기')

            if await view_all_link.count() == 0:
                # matched URL로 연결되는 링크 (텍스트 무관)
                view_all_link = page.locator('a[href*="matched"]')

            if await view_all_link.count() == 0:
                # 섹션 컨테이너에서 전체보기 버튼 찾기
                section = page.locator('section').filter(has_text='합격 가능성 높은 포지션')
                if await section.count() > 0:
                    view_all_link = section.get_by_text('전체보기', exact=True)
                else:
                    view_all_link = page.get_by_text('전체보기', exact=True).first

            # 전체보기 버튼 스크롤 후 클릭
            await view_all_link.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 클릭 및 페이지 이동 대기
            await view_all_link.first.click(timeout=10000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1000)

            # 결과 URL 확인 - https://www.wanted.co.kr/matched 로 이동했는지 확인
            current_url = page.url
            assert 'matched' in current_url, f"Expected URL to contain 'matched', but got: {current_url}"

            await page.screenshot(path='screenshots/test_CAREERSHOME_012_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_012_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
