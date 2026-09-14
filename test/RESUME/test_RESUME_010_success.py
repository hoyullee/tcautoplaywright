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

            print(f"이력서 편집 페이지 URL: {page.url}")

            # 이전 페이지 버튼 클릭
            # 이전 페이지 버튼은 상단 영역에 존재 (뒤로가기 버튼)
            back_btn = None

            # 1. aria-label로 찾기
            candidate = page.locator('[aria-label="이전 페이지"]')
            if await candidate.count() > 0:
                back_btn = candidate.first

            # 2. 텍스트로 찾기
            if back_btn is None:
                candidate = page.get_by_text('이전 페이지', exact=True)
                if await candidate.count() > 0:
                    back_btn = candidate.first

            # 3. 뒤로가기 버튼 패턴
            if back_btn is None:
                candidate = page.locator('[class*="back"], [class*="Back"]')
                if await candidate.count() > 0:
                    back_btn = candidate.first

            # 4. 이전 버튼 (이전/prev 패턴)
            if back_btn is None:
                candidate = page.locator('[class*="prev"], [class*="Prev"]')
                if await candidate.count() > 0:
                    back_btn = candidate.first

            # 5. 헤더 내 첫 번째 버튼 (이력서 편집 페이지 상단의 뒤로가기)
            if back_btn is None:
                candidate = page.locator('header button, [class*="header"] button, [class*="Header"] button')
                if await candidate.count() > 0:
                    back_btn = candidate.first

            # 6. role=button으로 찾기
            if back_btn is None:
                candidate = page.get_by_role('button', name='이전')
                if await candidate.count() > 0:
                    back_btn = candidate.first

            assert back_btn is not None, "이전 페이지 버튼을 찾을 수 없습니다"

            # 이전 페이지 버튼 클릭
            await back_btn.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            print(f"이전 페이지 버튼 클릭 후 URL: {page.url}")

            # 이력서 탭 페이지로 랜딩 확인
            # 이력서 탭 페이지 URL: https://www.wanted.co.kr/cv/list
            assert 'cv/list' in page.url or 'cv/intro' in page.url, \
                f"이력서 탭 페이지로 이동하지 않음: {page.url}"

            await page.screenshot(path='screenshots/test_RESUME_010_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_RESUME_010_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
