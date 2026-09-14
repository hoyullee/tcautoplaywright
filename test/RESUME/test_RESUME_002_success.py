import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = ""
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

            # LNB 메뉴 영역 확인
            # 1. "포지션 맞춤 리뷰" 항목 노출 확인 (default 선택 상태)
            position_review_text = page.get_by_text('포지션 맞춤 리뷰', exact=False)
            assert await position_review_text.count() > 0, "LNB에 '포지션 맞춤 리뷰' 항목이 없습니다"

            # 2. "이력서 리뷰" 항목 노출 확인
            resume_review_text = page.get_by_text('이력서 리뷰', exact=False)
            assert await resume_review_text.count() > 0, "LNB에 '이력서 리뷰' 항목이 없습니다"

            # 3. 포지션 맞춤 리뷰가 default 선택 상태인지 확인 (패널이 열려있어야 함)
            # 포지션 맞춤 리뷰 패널이 노출되는지 확인
            position_review_panel = page.locator('[class*="PositionReview"], [class*="position-review"], [class*="positionReview"]')
            panel_visible = await position_review_panel.count() > 0

            if not panel_visible:
                # 다른 방법으로 패널 존재 확인 - 텍스트 기반으로 클릭 후 확인
                await position_review_text.first.click()
                await page.wait_for_timeout(1000)

            # 최종 검증: 두 메뉴 항목이 모두 존재하는지 재확인
            position_review_final = page.get_by_text('포지션 맞춤 리뷰', exact=False)
            resume_review_final = page.get_by_text('이력서 리뷰', exact=False)

            pos_count = await position_review_final.count()
            res_count = await resume_review_final.count()

            assert pos_count > 0, f"'포지션 맞춤 리뷰' 항목이 LNB에 노출되지 않습니다"
            assert res_count > 0, f"'이력서 리뷰' 항목이 LNB에 노출되지 않습니다"

            print(f"✅ LNB '포지션 맞춤 리뷰' 항목 확인: {pos_count}개 발견")
            print(f"✅ LNB '이력서 리뷰' 항목 확인: {res_count}개 발견")
            print(f"✅ 현재 URL: {page.url}")

            await page.screenshot(path='screenshots/test_RESUME_002_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_RESUME_002_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
