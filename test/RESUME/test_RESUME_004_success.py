import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"
TEST_PASSWORD = ""

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

            print(f"이력서 편집 페이지 진입: {page.url}")

            # Step 1: LNB 메뉴 영역에서 "이력서 리뷰" 버튼 찾기
            review_btn = None

            # 다양한 텍스트 패턴으로 탐색
            for selector_text in ['이력서 리뷰', 'AI 이력서 리뷰', '리뷰']:
                btn = page.get_by_text(selector_text, exact=False)
                count = await btn.count()
                if count > 0:
                    review_btn = btn.first
                    print(f"이력서 리뷰 버튼 발견: '{selector_text}'")
                    break

            if review_btn is None:
                # LNB 영역 내에서 탐색
                lnb_area = page.locator('[class*="LNB"], [class*="lnb"], [class*="Sidebar"], [class*="sidebar"], nav')
                if await lnb_area.count() > 0:
                    for selector_text in ['이력서 리뷰', '리뷰']:
                        btn = lnb_area.first.get_by_text(selector_text, exact=False)
                        if await btn.count() > 0:
                            review_btn = btn.first
                            print(f"LNB 내 이력서 리뷰 버튼 발견: '{selector_text}'")
                            break

            assert review_btn is not None, "이력서 리뷰 버튼을 찾을 수 없습니다"

            # Step 2: 이력서 리뷰 버튼 클릭
            await review_btn.click()
            await page.wait_for_timeout(2000)

            # Step 3: 패널 영역 확인
            # "이력서 분석을 받아보세요" 텍스트 확인
            analysis_title = page.get_by_text('이력서 분석을 받아보세요', exact=False)
            assert await analysis_title.count() > 0, "'이력서 분석을 받아보세요' 타이틀이 노출되지 않습니다"
            print("'이력서 분석을 받아보세요' 타이틀 확인")

            # "이력서 리뷰 받기" 버튼 확인
            review_receive_btn = page.get_by_role('button', name='이력서 리뷰 받기')
            if await review_receive_btn.count() == 0:
                # 다른 패턴으로 탐색
                review_receive_btn = page.get_by_text('이력서 리뷰 받기', exact=False)

            assert await review_receive_btn.count() > 0, "'이력서 리뷰 받기' 버튼이 노출되지 않습니다"
            print("'이력서 리뷰 받기' 버튼 확인")

            await page.screenshot(path='screenshots/test_RESUME_004_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_RESUME_004_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
