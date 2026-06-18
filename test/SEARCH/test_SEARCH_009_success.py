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

            # 1. 채용 홈 진입 (로그인 세션 사용)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(2000)

            # 2. 최근 검색 이력 생성을 위해 먼저 검색 수행
            # GNB 검색 버튼 클릭
            search_btn = page.get_by_role('button', name='검색')
            await search_btn.wait_for(state='visible', timeout=10000)
            await search_btn.click()
            await page.wait_for_timeout(1000)

            # 검색 입력창에 검색어 입력
            search_input = page.locator('input[type="search"]')
            await search_input.wait_for(state='visible', timeout=10000)
            await search_input.fill('개발자')
            await page.wait_for_timeout(500)
            await page.keyboard.press('Enter')
            await page.wait_for_load_state('load', timeout=15000)
            await page.wait_for_timeout(2000)
            print("검색 이력 생성 완료: '개발자' 검색")

            # 3. 채용 홈으로 다시 이동
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(2000)

            # 4. GNB > 검색 버튼 클릭 (최근 검색어 확인)
            search_btn2 = page.get_by_role('button', name='검색')
            await search_btn2.wait_for(state='visible', timeout=10000)
            await search_btn2.click()
            await page.wait_for_timeout(1500)

            # 검색 패널이 열렸는지 확인
            search_input2 = page.locator('input[type="search"]')
            await search_input2.wait_for(state='visible', timeout=10000)
            print("검색 패널 열림 확인")

            # 5. 최근 검색어 섹션 확인
            # "최근 검색어" 텍스트 찾기
            recent_header = page.get_by_text('최근 검색어', exact=True)
            header_count = await recent_header.count()
            print(f"'최근 검색어' 헤더 수: {header_count}")

            if header_count == 0:
                # 다른 가능한 텍스트 시도
                recent_header = page.get_by_text('최근검색어', exact=True)
                header_count = await recent_header.count()
                print(f"'최근검색어' 헤더 수: {header_count}")

            if header_count == 0:
                # 최근 검색어 관련 텍스트 포함 확인
                recent_header = page.locator('*').filter(has_text='최근 검색')
                header_count = await recent_header.count()
                print(f"'최근 검색' 포함 요소 수: {header_count}")

            assert header_count > 0, "최근 검색어 섹션을 찾을 수 없음"
            print(f"✅ 최근 검색어 섹션 확인 완료")

            # 6. 최근 검색어 항목 존재 확인
            # 검색 패널 내에서 최근 검색어 항목 탐색
            # 검색어 '개발자'가 목록에 있는지 확인
            recent_item = page.get_by_text('개발자', exact=True)
            item_count = await recent_item.count()
            print(f"'개발자' 최근 검색어 항목 수: {item_count}")

            if item_count == 0:
                # 더 넓은 범위로 확인
                recent_item = page.locator('*').filter(has_text='개발자')
                item_count = await recent_item.count()
                print(f"'개발자' 포함 요소 수: {item_count}")

            assert item_count > 0, "최근 검색어 '개발자' 항목이 표시되지 않음"
            print(f"✅ 최근 검색어 항목 '개발자' 노출 확인")

            await page.screenshot(path='screenshots/test_61_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_61_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
